import pytest
from app.terminal import termination as t

def plan(args=None, kind='exec'):
    return {'instruction':'终止端口8091和8092的服务', 'goal':'终止服务', 'steps':[{'kind':kind,'executable':'/bin/kill','args':args or ['-15','123','456'],'script':'kill 123'}]}

def test_targets_and_reject_dynamic():
    assert t.termination_targets(plan()) == ([8091,8092], {123,456})
    with pytest.raises(ValueError): t.termination_targets(plan(kind='shell'))
    with pytest.raises(ValueError): t.termination_targets(plan(['-15','-1']))

@pytest.mark.asyncio
async def test_stale_pids_stop_before_execution(monkeypatch):
    async def listeners(ports): return {8091:{999},8092:{456}}
    monkeypatch.setattr(t,'listeners',listeners)
    with pytest.raises(ValueError,match='不一致'): await t.preflight(([8091,8092],{123,456}))

@pytest.mark.asyncio
async def test_identity_change_rejected(monkeypatch):
    async def listeners(ports): return {8091:{123}}
    async def identity(pid): return 'new process'
    monkeypatch.setattr(t,'listeners',listeners)
    monkeypatch.setattr(t,'process_identity',identity)
    with pytest.raises(ValueError,match='身份'): await t.revalidate(([8091],{123}),{123:'old process'})

@pytest.mark.asyncio
async def test_postflight_empty_and_restart(monkeypatch):
    async def empty(ports): return {8091:set()}
    monkeypatch.setattr(t,'listeners',empty)
    ok, text = await t.postflight(([8091],{123}))
    assert ok and '未发现TCP监听' in text
    async def occupied(ports): return {8091:{999}}
    async def no_sleep(n): pass
    monkeypatch.setattr(t,'listeners',occupied)
    monkeypatch.setattr(t.asyncio,'sleep',no_sleep)
    ok, text = await t.postflight(([8091],{123}))
    assert not ok and '未自动再次终止' in text
