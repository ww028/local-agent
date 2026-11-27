import asyncio
import socket
import pytest
from app.terminal.port_queries import query_ports, proposal, summary
from app.terminal.plans import build_generated
from app.terminal.runner import execute_step


def test_query_scope():
    assert query_ports('检查一下8091 8092 8093 端口是否被占用') == [8091,8092,8093]
    assert query_ports('终止8091端口') is None
    with pytest.raises(ValueError): query_ports('检查99999端口占用')

@pytest.mark.asyncio
async def test_real_mixed_ports(tmp_path):
    # Owned sockets only; no user services are touched.
    occupied=socket.socket(); occupied.bind(('127.0.0.1',0)); occupied.listen()
    spare=socket.socket(); spare.bind(('127.0.0.1',0)); free=spare.getsockname()[1]; spare.close()
    ports=[free,occupied.getsockname()[1]]
    try:
        plan=build_generated(tmp_path,'.',proposal(ports),instruction=f'检查{ports[0]}和{ports[1]}端口占用')
        records=[]
        for i,step in enumerate(plan['steps']):
            result=await execute_step(step,plan,lambda out,err:None)
            assert result['status']=='completed',result
            assert result['error'] is None
            records.append(result)
        assert records[0]['facts']['listening'] is False
        assert records[1]['facts']['listening'] is True
        text=summary(records)
        assert str(ports[0]) in text and str(ports[1]) in text
        assert '未发现TCP监听' in text and '有TCP监听' in text
    finally: occupied.close()
