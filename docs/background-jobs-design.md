# 后台任务中心与只读本机诊断技术方案

## 1. 用户目标与首批范围

用户在网页提交指令，服务立即返回“已接收”；后台自行调用本地模型与工具，
网页默认只展示状态和最终结果，步骤折叠可查。刷新、换页、关闭网页不取消。

首批复用知识搜索/文档读取/计算，新增可选只读诊断：check_port(port)查询本机
TCP监听进程、system_info()获取OS/CPU/内存/磁盘基本信息。不支持结束进程、
任意命令、任意目录读取、写文件、桌面鼠标操作、浏览器自动化或外发。
“任务后台执行”与“任何电脑操作均支持”是两件事。

## 2. 架构与生命周期

Web提交 → POST /api/jobs (202) → SQLite持久化 → 独立JobWorker →
共享模型并发锁 → 模型工具循环 → SQLite结果/事件 → Web轮询。
worker由FastAPI lifespan创建，不由HTTP请求/SSE连接持有。SQLite为队列事实源，
内存仅保留当前正在执行的asyncio.Task及唤醒事件，不依赖内存队列恢复。
单后端worker、单任务执行，与聊天共享chat_lock；任务等待模型期间仍为queued。
用户提交/查询不需维持长连接。

启动时queued任务可继续，旧running/cancelling变为interrupted并写明服务停止。
不自动重放可能已执行的动作；本轮虽只有只读工具，也遵守后续写工具的安全边界。
用户重试创建新任务并标parent_job_id，旧结果保留。后台退出取消当前子任务并落库。
电脑睡眠/关机/后端退出不会继续；不声称系统常驻守护或多进程HA。

## 3. 状态机与数据

queued → running → completed / failed / cancelled / interrupted。
运行中取消先写cancelling，取消模型请求/工具子进程，finally写cancelled。
排队取消立即cancelled，重复取消返回当前状态；终态不能被晚到结果覆盖。

jobs字段：job_id、instruction、model、allow_diagnostics、status、summary、result、
error、run_id、conversation_id、parent_job_id、created/started/finished/updated。
run_events沿用已实现的模型/工具事件；任务关联内部会话，任务中心只展示指令与
结果，兼容现有历史记录。删除会话若关联任务拒绝；不在首批提供删除任务。
列表分页最多50，指令最大2000字符，待运行任务最大32，单任务整体180秒/现有
Agent6步8调用预算；可查询、取消、重试。

## 4. 权限与电脑诊断

诊断仅在提交页面显式勾选allow_diagnostics时注册进该任务Tools对象，普通聊天
不获得诊断工具。后端也检查开关，模型提示词不是权限。

check_port只允许1–65535整数，macOS/Linux固定路径/usr/sbin/lsof或/usr/bin/lsof，
参数固定-Fpcn -nP -iTCP:{port} -sTCP:LISTEN，无shell=True、无用户命令串、无sudo。
命令超时5秒，限制输出64KB，使用异步子进程，取消时terminate并等待，必要时kill。
返回监听状态/PID/进程短名称/地址，不输出环境变量、完整命令行或用户身份。
lsof返回1且无输出仅表示当前可见范围无监听；权限/缺依赖/不支持OS独立错误，
不得将查询失败宣称“端口空闲”。这是TCP监听检测，不覆盖UDP或远端主机。

system_info使用Python标准库和OS读取接口，不取序列号、用户名、主机名、网络
标识；只提供平台版本、CPU核心、物理内存和系统盘容量，缺值明确说明。

禁止任何公司内部依赖/SDK/代码复用。诊断工具是公开仓库自行实现的固定只读
适配器。结果/事件可能包含本机进程信息，仅保存在ignored data目录。
未来写/删除/发送工具需要单独方案及后台“等待授权”状态，本批不做假确认按钮。

## 5. API 与网页

- POST /api/jobs：instruction/model/allow_diagnostics →202 job详情。
- GET /api/jobs?limit&offset：分页列表（不返回完整result/指令日志之外的敏感数据）。
- GET /api/jobs/{id}：状态、结果、允许诊断、时间、关联执行事件（默认UI折叠）。
- POST /api/jobs/{id}/cancel：幂等取消。
- POST /api/jobs/{id}/retry：仅failed/interrupted/cancelled允许，新job入队。

新增“任务中心”导航、指令框/本机诊断复选框、模型选择、状态列表、最终结果
Markdown、取消/重试、折叠步骤。不调用streamChat；2秒轮询，页面卸载只停止
轮询，不发送取消。失败和中断提供原因，模型不可用不静默下载/改调云。
任务结果展示工具事实和模型文本分开，诊断没有实际成功调用不能标成完成。

## 6. 分批落地与验收

方案和相关文档先写入仓库并交付，然后批次1：schema/repository/worker/诊断/
API及单测，自测后commit；批次2：任务中心UI/真实模型/浏览器，验收后commit，
完整业务模块push。只暂存本批明确源文件，模型/资料/系统结果不进Git。

测试：POST立即返回、不依赖HTTP客户端；慢模型关闭请求后完成；排队/运行取消、
重试新ID、崩溃启动恢复、持久化结果、非法端口/开关拒绝、subprocess超时/取消、
lsof无监听与权限错误区分；现有聊天/RAG/Agent回归；真实任务检查8091端口
（可用临时监听服务可复算），浏览器提交后刷新/换页/重开完成结果。
不认证通用GUI自动化、任意任务成功率、整机物理断网和长时生产可靠性。
