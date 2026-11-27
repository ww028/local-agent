"""Fail-closed checks for approved direct port-process termination, not execution permission."""
import asyncio
import re
from pathlib import Path


def termination_targets(plan):
    killing = [s for s in plan['steps'] if Path(s.get('executable', '')).name in {'kill', 'pkill', 'killall'} or (s.get('kind') == 'shell' and re.search(r'\b(?:kill|pkill|killall)\b', s.get('script', '')))]
    if not killing:
        return None
    text = plan.get('instruction', '') + ' ' + plan.get('goal', '')
    if not re.search(r'端口|\bport\b', text, re.I):
        return None
    ports = sorted({int(x) for x in re.findall(r'(?<!\d)\d{1,5}(?!\d)', text)})
    if not ports or any(not 1 <= p <= 65535 for p in ports):
        raise ValueError('无法明确端口目标，未终止进程，请重新规划。')
    pids = set()
    for step in killing:
        args = step.get('args', [])
        if step.get('kind') != 'exec' or Path(step.get('executable', '')).name != 'kill':
            raise ValueError('端口终止只接受可核对的直接kill计划，不执行批量名称或动态脚本，请重新规划。')
        values = args[1:] if args and args[0] in {'-9', '-15', '-TERM', '-KILL'} else args
        if not values or any(not str(v).isdigit() or int(v) <= 1 for v in values):
            raise ValueError('终止目标必须是明确的正进程号，未执行。')
        pids.update(map(int, values))
    return ports, pids

async def read_command(*args):
    process = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(process.communicate(), 5)
    except BaseException:
        if process.returncode is None:
            process.kill()
        await process.wait()
        raise
    return process.returncode, out.decode(errors='replace'), err.decode(errors='replace')

async def listeners(ports):
    result = {}
    for port in ports:
        code, out, err = await read_command('/usr/sbin/lsof', '-nP', f'-iTCP:{port}', '-sTCP:LISTEN', '-t')
        if code not in {0, 1} or err.strip():
            raise ValueError('端口检查失败或权限不完整，未能验证目标。')
        if any(not line.isdigit() for line in out.split()):
            raise ValueError('端口进程结果无效，未执行。')
        result[port] = set(map(int, out.split()))
    return result

async def process_identity(pid):
    code, out, err = await read_command('/bin/ps', '-p', str(pid), '-o', 'lstart=,command=')
    if code != 0 or err.strip() or not out.strip():
        raise ValueError('目标进程已变化或无法核对，未继续执行。')
    return out.strip()

async def preflight(targets):
    ports, pids = targets
    mapping = await listeners(ports)
    current = set().union(*mapping.values())
    if current != pids:
        raise ValueError('端口监听进程与已确认计划不一致，未终止任何进程；请重新规划和确认。')
    identities = {pid: await process_identity(pid) for pid in pids}
    return identities

async def revalidate(targets, identities):
    mapping = await listeners(targets[0])
    current = set().union(*mapping.values())
    if not current.issubset(targets[1]):
        raise ValueError('端口出现新监听进程，停止后续终止操作，请重新规划。')
    for pid in current:
        if await process_identity(pid) != identities[pid]:
            raise ValueError('进程身份已变化，停止后续操作。')
    return current

async def postflight(targets):
    # Bounded settling, not a promise that a supervisor will never restart later.
    for _ in range(5):
        mapping = await listeners(targets[0])
        if not any(mapping.values()):
            break
        await asyncio.sleep(.2)
    remaining = [str(p) for p, ids in mapping.items() if ids]
    if remaining:
        return False, '终止命令已返回，但复查仍发现TCP监听端口：' + '、'.join(remaining) + '。可能未退出或已自动重启，未自动再次终止。'
    return True, '终止命令已返回；复查端口' + '、'.join(map(str, targets[0])) + '，当前用户可见范围未发现TCP监听。不保证服务以后不会重启。'
