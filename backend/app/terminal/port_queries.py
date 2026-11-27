"""Exact TCP port query plans and fact summaries, never infer no-match from arbitrary exit codes."""
import re
from pathlib import Path

def query_ports(text):
    if not re.search(r'端口|\bports?\b', text, re.I) or not re.search(r'检查|查询|查看|占用|监听|check', text, re.I):
        return None
    if re.search(r'kill|终止|停止|关闭|删除|启动|安装', text, re.I):
        return None
    numbers = re.findall(r'(?<![\d.])\d+(?![\d.])', text)
    ports = list(dict.fromkeys(map(int, numbers)))
    if not ports:
        return None
    if len(ports) > 4 or any(not 1 <= p <= 65535 for p in ports):
        raise ValueError('每次请查询1–4个端口，端口范围1–65535。')
    return ports

def proposal(ports):
    return {'goal':'检查TCP端口'+ '、'.join(map(str,ports))+'的当前可见监听情况', 'steps':[{'kind':'exec','program':'/usr/sbin/lsof','args':['-nP',f'-iTCP:{p}','-sTCP:LISTEN','-Fpcfn'],'description':f'查询TCP端口{p}监听','timeout_seconds':10} for p in ports]}

def step_port(step):
    if step.get('kind') != 'exec' or Path(step.get('executable','')).name != 'lsof': return None
    args = step.get('args',[])
    ports = [re.fullmatch(r'-iTCP:(\d+)',a) for a in args]
    ports = [int(m.group(1)) for m in ports if m]
    if len(ports)==1 and set(args)=={'-nP',f'-iTCP:{ports[0]}','-sTCP:LISTEN','-Fpcfn'}:
        return ports[0]
    return None

def summary(records):
    facts = [r.get('facts') for r in records]
    if not facts or not all(f and 'port' in f for f in facts): return None
    lines=[]
    for f in facts:
        processes=f.get('processes',[])
        if f['listening']:
            names='、'.join(str(p.get('process','进程'))+'（PID '+str(p['pid'])+'）' for p in processes)
            lines.append(f"端口{f['port']}：有TCP监听，{names}。")
        else:
            lines.append(f"端口{f['port']}：当前用户可见范围未发现TCP监听。")
    return '\n'.join(lines)+'\n仅反映本次查询，不代表UDP占用或未来状态。'
