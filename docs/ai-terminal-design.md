# 确认式 AI 终端技术方案（V1/V2历史方案）

> 新任务已切换[生成式V3](generative-terminal-design.md)，下面的固定动作限制仅描述
> 旧版本，不是当前新任务的能力范围；历史任务与确认不能自动升级权限。

## 1. 首批目标与不做范围

用户自然语言描述任务，AI先解释需求并提出命令计划；网页完整展示每步命令、
执行目录、作用、权限与限制，用户确认后由后端执行，展示原始输出/退出码及AI总结。
规划不等于授权。模型不能执行命令，执行器只能启动确认过的固定计划。

首批是受控只读命令助手，不是任意shell或完整PTY终端。支持当前项目及其非符号
链接子目录的目录列表/路径、Git状态/差异统计/最近5条提交、Git/Python版本及本机TCP端口监听查询。
只允许预定义动作；唯一动态参数为严格整数port，不接受自定义命令串。拒绝写入、删除、提权、联网、脚本、
包管理、启动服务、读取凭据/任意文件、交互式输入；超出能力返回说明，不偷偷替换。
默认工作区为仓库根目录，部署时可通过TERMINAL_WORKSPACE显式配置另一个项目。
不能选择文件系统根、用户家目录或敏感目录作为工作区。工作区选择不是OS沙箱。

## 2. 数据流与模块

网页提交指令+相对目录 → SQLite terminal_tasks → 独立TerminalService →
共享模型锁规划 → catalog校验 → 保存不可变计划/摘要 → awaiting_confirmation →
用户提交plan_hash → 原子确认并排队 → 独立串行命令worker → 输出持久化 →
释放进程资源 → 本地模型总结（有界，可失败） → completed/failed。

新增terminal/catalog.py（动作映射/目录/计划hash）、runner.py（固定exec/输出/超时/取消）、
service.py（任务状态/规划/执行/总结）、store/terminal.py、routes/terminal.py，
前端TerminalPage/TerminalDetails。复用本地模型适配、SQLite、Host/Origin和静态服务，
不调用内部SDK或桌面工具，不新增公司资源或遥测。依赖仅Python标准库和既有公开包。

规划模型只调用propose_terminal_plan结构化工具，输出goal、actions（最多4步）或
unsupported_reason。actions枚举由公开catalog提供；实际executable/argv/cwd/timeout
由后端生成。用户即使在自然语言嵌入shell文本，也不能把该文本传给执行器。
规划最多2次有界模型请求，不从资料检索命令、不扫描整个目录。

## 3. 状态与确认

planning → awaiting_confirmation → queued → running → completed/failed。
规划不支持/错误为failed；取消planning/等待/排队为cancelled，运行先cancelling。
重启将planning/running/cancelling标interrupted；未执行的queued可继续。
等待确认保留10分钟有效期，过期显示expired。等待用户不占模型锁或进程。

计划持久化固定JSON（policy_version、goal、workspace、cwd、步骤程序/参数/描述、
目录device/inode、可执行程序device/inode/size/mtime）；canonical SHA256绑定完整计划。确认请求携带hash，后台
重新校验当前策略/目录/计划与期限，原子状态更新只允许一次。重复点击同一计划
返回同一任务而不再启动进程；改计划或改目录需要新任务/新确认。模型无确认API。
命令执行前再次核对目录、固定catalog和hash，禁止客户端传任意argv。
不自动修复命令、不自动重试副作用；重新规划建立新任务，重新确认。

terminal_tasks保存instruction/model/relative_dir/status/plan/hash/expiry/error/summary/
时间；terminal_steps保存每步stdout/stderr/exit_code/开始结束/状态。运行数据仅本地
ignored数据库，不提交测试PID、实际文件名、用户路径或原始结果。
最多16个非终态任务；分页最多50；指令2000字符。任务详情返回事实与模型总结分区。

## 4. 执行与安全

asyncio.create_subprocess_exec，shell=False，固定可信程序和参数，没有zsh/bash。
不使用模型提供PATH、环境、文件名或可执行文件。最小环境，禁用Git pager/
fsmonitor/hooks、lazy fetch、外部diff/textconv及全局/系统Git配置。内置Git命令仍读取项目本地
元数据，不能据此称完全隔离；工作区自身文件可以由外部程序变化。

路径限定已配置项目；拒绝绝对路径、..、符号链接、.git/凭据等敏感子目录。
执行前核对目录身份以减少确认与执行间变化；无法彻底阻止同账号外部程序并发换
目录的TOCTOU，初版可信单人本机，不宣称OS强沙箱。可执行文件catalog固定路径。
命令可能继承系统账号读权限，但本批没有自由文件读取/命令输入出口。

每步30秒（端口5秒）、最多4步；stdout/stderr合计128KiB，超限停止并明确截断/失败。
stdin=DEVNULL；macOS/Linux新进程组，取消/超时停止本任务进程组并等待清理，
不结束其他服务。取消不等于回滚。服务停止记录interrupted，不盲重放已启动命令。
终态不可被晚到输出覆盖；原始输出以纯文本展示，禁止ANSI控制/HTML执行。

原始退出码与输出决定命令成功/失败；端口lsof返回1且双输出为空表示无可见监听，
作为成功查询保留退出码1，其他非零/警告立即失败停止后续步骤。AI总结只有解释权限，
不能执行输出中包含的指令，也不能覆盖事实；总结失败仍保留命令真实结果。
原始输出最多给总结模型约3000字符，提醒截断及不代表完整业务验证。

## 5. API与交互

- GET /api/terminal/capabilities：配置工作区、动作目录、限制。
- POST /api/terminal：自然语言/model/relative_dir，202返回planning。
- GET /api/terminal?limit&offset；GET /api/terminal/{id}：状态/固定计划/结果。
- POST /api/terminal/{id}/confirm：plan_hash；原子确认后执行。
- POST /api/terminal/{id}/cancel：幂等取消。

新增“AI终端”导航：指令输入、相对目录、模型；计划卡展示真实命令/argv及目录，
每次显式“确认执行”。状态及stdout/stderr定时刷新，关闭网页不取消已确认执行。
未确认绝不启动进程。过期/失败可以按原指令重新规划，不复用旧授权。
执行过程中可停止；完成后显示事实、AI解释与历史。当前不做键盘交互/PTY。

## 6. 分批与验收

先写本方案和README/架构/路线图计划段，再编码。
批次1：catalog/持久化确认/worker/runner/API和mock测试，自测commit。
批次2：网页计划确认/输出历史/真实模型与进程/刷新/拒绝范围验收，自测commit；
整个模块push，不force-push，不加入模型权重、环境或运行资料。

验收必须包含：未确认无子进程；错误hash/过期/重复点击；修改目录/符号链接/
不受支持动作拒绝；计划改动失效；非零/超时/取消/输出上限；服务重启中断；
网页确认后刷新可回看，原始输出与AI解释分开；真实本地模型规划与真实Git只读
命令结果一致；离线无远端调用；现有聊天/RAG/jobs回归。声明限制：无OS沙箱认证、
无任意shell能力、无全量命令正确率/长期生产/整机断网认证。

## 8. 端口诊断补齐方案（先方案后修复）

AI终端新增check_port，port为严格1–65535整数；查询本机TCP监听无需联网。
后端从指令明确的端口数字核对模型计划，避免模型遗漏查询或更换端口；缺失/
多端口需用户明确单个端口，不擅自查询别的目标。参数也纳入固定计划hash，改端口
必须重新确认。旧策略计划不能直接沿用新能力，重新规划即可，旧结果不改写。

共用agent/diagnostics的固定lsof命令构造/结果解析，不调用网络扫描，不提供任意
lsof参数、不升权、不结束监听进程。终端仍通过现有runner执行展示的准确命令，
超时5秒；本机可见TCP监听返回PID/短进程名/监听地址。进程名不代表业务服务身份。
保留stdout/stderr/真实退出码，额外保存结构化诊断事实。code1且无任何输出为
“当前用户可见范围未发现TCP监听”而非命令失败；告警/权限/异常/超时不报空闲。

错误提示由后端确定，不直接展示模型unsupported_reason猜测；超能力说明动作
目录边界，查询失败提示本地查询原因，不再误称需要联网。前端展示端口/协议/
范围及监听事实，AI解释不覆盖事实。测试非法/注入端口、hash改动、模型拒绝/遗漏/
更换目标、无监听/权限错误/混合输出、确认前无进程、真实监听PID对照、网页确认/
刷新回看，既有功能回归后commit并push。

补齐已完成：80后端、17前端测试及真实模型/进程对照通过。用户8092询问生成
确认计划，确认后结果与独立lsof一致；无可见监听为成功查询，原始退出码1保留。
临时监听返回实际PID且退出0；未增加网络/提权/结束进程能力。旧失败记录不修改，
可点击重新规划获得新计划。详见product-acceptance.md。

## 7. 实施与验收状态

首批已实现。后端c1aa944自测后提交，第二批为计划审核/确认/事实输出/AI解释
网页及边界补测。66后端、16前端用例通过，真实Qwen3生成Git只读计划，确认前
无执行，网页确认后刷新完成，原始输出与独立Git检查一致；不支持安装脚本
请求拒绝、未确认取消与重新规划再次确认已验收。详见product-acceptance.md。
本轮未引入额外依赖/企业资源、权重或实际运行数据。
