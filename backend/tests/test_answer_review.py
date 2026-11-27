import pytest
from app.answer_review import reviewed_answer
from app.config import Settings
from app.schemas import ChatMessage

class Fake:
    def __init__(self):
        self.calls = []
    async def achat(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        yield "错误草稿" if len(self.calls) == 1 else "校验后的答案"

@pytest.mark.asyncio
async def test_review_only_streams_final():
    fake = Fake()
    result = ''.join([x async for x in reviewed_answer(fake, [ChatMessage(role='system', content='s'), ChatMessage(role='user', content='q')], model='local', settings=Settings())])
    assert result == '校验后的答案'
    assert len(fake.calls) == 2
    assert '错误草稿' in fake.calls[1][0][-1].content
    assert all(call[1]['reasoning'] is False for call in fake.calls)

@pytest.mark.asyncio
async def test_review_cancellation_stops_before_second_call():
    fake = Fake()
    async def disconnected():
        return True
    assert [x async for x in reviewed_answer(fake, [ChatMessage(role='user', content='q')], model='local', settings=Settings(), disconnected=disconnected)] == []
    assert len(fake.calls) == 1
