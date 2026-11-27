"""Compile explicit supported intents to immutable plans; model fallback remains separate."""
import os
import re
from app.terminal.port_queries import query_ports, proposal as query_proposal
from app.terminal.plans import build_generated, detect_version_query, version_proposal
from app.terminal.termination import listeners, process_identity

def stop_ports(text):
    if not re.search(r'端口|\bports?\b',text,re.I): return None
    if not re.search(r'kill|终止|停止|关掉|关闭',text,re.I): return None
    if re.search(r'不要|别|不能|是否|能不能|如果|假如|怎么|如何|强制|kill\s*-9',text,re.I): return None
    # Reject negative/fractional ports instead of truncating them.
    values=re.findall(r'(?<![\d.])-?\d+(?:\.\d+)?(?![\d.])',text)
    if not values: return None
    if any(not x.isdigit() for x in values): raise ValueError('端口必须为1–65535的整数。')
    ports=list(dict.fromkeys(map(int,values)))
    if len(ports)>4 or any(not 1<=p<=65535 for p in ports): raise ValueError('每次请指定1–4个有效端口。')
    return ports

async def compile_request(workspace, relative_dir, instruction):
    ports=stop_ports(instruction)
    identities=None
    if ports:
        mapping=await listeners(ports)
        pids=sorted(set().union(*mapping.values()))
        if len(pids)>4: raise ValueError('目标监听进程超过4个，请缩小范围，未终止任何进程。')
        if os.getpid() in pids: raise ValueError('目标包含本工作台后端，不能从内部终止自身。')
        if not pids:
            candidate=query_proposal(ports)
        else:
            identities={str(pid):await process_identity(pid) for pid in pids}
            candidate={'goal':'正常终止TCP端口'+ '、'.join(map(str,ports))+'的监听进程','steps':[{'kind':'exec','program':'/bin/kill','args':['-TERM',str(pid)],'description':f'向已核对监听进程{pid}发送TERM；可能中断服务，未保存数据可能丢失，不自动强杀','timeout_seconds':10} for pid in pids]}
    else:
        ports=query_ports(instruction)
        if ports:
            candidate=query_proposal(ports)
        else:
            fast=detect_version_query(instruction)
            if fast is None: return None
            tool, executable=fast
            if not executable: raise ValueError(f'本机PATH中没有找到{tool}。')
            candidate=version_proposal(tool,executable)
    plan=build_generated(workspace,relative_dir,candidate,instruction=instruction)
    if identities:
        plan['target_identities']=identities
        plan['target_ports']=ports
    return plan
