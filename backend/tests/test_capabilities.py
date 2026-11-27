import pytest
from app.terminal import capabilities as c
from app.terminal.plans import verify_generated

@pytest.mark.parametrize('text',['不要kill8093端口','如果关闭8093端口','如何终止8093端口'])
def test_ambiguous_not_compiled(text):
    assert c.stop_ports(text) is None

def test_explicit():
    assert c.stop_ports('去把8093 端口kill掉') == [8093]
    with pytest.raises(ValueError): c.stop_ports('kill -1端口')

@pytest.mark.asyncio
async def test_stop_plan_bound_identity(tmp_path,monkeypatch):
    async def listeners(ports): return {8093:{123}}
    async def identity(pid): return 'start command'
    monkeypatch.setattr(c,'listeners',listeners)
    monkeypatch.setattr(c,'process_identity',identity)
    plan=await c.compile_request(tmp_path,'.','去把8093端口kill掉')
    assert not plan['auto_run']
    assert plan['steps'][0]['args']==['-TERM','123']
    assert plan['target_identities']=={'123':'start command'}
    from app.terminal.plans import digest
    assert verify_generated(tmp_path,plan,digest(plan))['target_identities']==plan['target_identities']

@pytest.mark.asyncio
async def test_no_target_only_queries(tmp_path,monkeypatch):
    async def listeners(ports): return {8093:set()}
    monkeypatch.setattr(c,'listeners',listeners)
    plan=await c.compile_request(tmp_path,'.','关闭8093端口服务')
    assert all(s['program']=='/usr/sbin/lsof' for s in plan['steps'])
