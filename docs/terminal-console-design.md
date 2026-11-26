# 会话式 AI 终端（Console）技术方案

## 目标

把当前“任务列表 + 详情面板”改成 macOS 终端窗口形态的单条会话流：

- 上方是终端窗口（标题栏、等宽字体、浅色终端底色），一条连续滚动的转录流：
  你说的需求、AI 生成的命令计划、你的确认、真实 stdout/stderr、退出码和 AI 解释，
按时间顺序出现。不做无功能的红黄绿圆点，避免只当装饰的假窗口控件。
- 虽然是终端外观，**内容是对话形态**：你的需求靠右显示为气泡（“你”），AI 的计划、
命令和结果靠左（“AI”头像），命令块保留等宽字体，阅读上像聊天、执行上像终端。
- 底部固定一个对话输入框（`❯` 提示符），你像和 AI 对话一样描述需求、回车提交；
  有待确认计划时，输入 `y`/`n` 直接回答确认/取消。
- 待确认是**明显的决策卡片**：琥珀色描边+“需要你确认才执行”标题+影响说明+
  大号“执行 (y) / 取消 (n)”按钮；输入框上方另有同色提示条，提示当前在等你决定。
- 新内容（新需求、AI 计划、输出刷新、确认状态变化）到达时自动滚到底部；
  只有你主动向上翻阅时暂停跟随，滚回底部后恢复。
- 不再是“先选一个任务再看右侧详情”，历史执行结果就是终端滚屏。

## 交互流程

1. 输入框输入自然语言 → 回车 → 转录流追加你的气泡，下方出现 AI 正在生成命令的提示，
   视图自动滚到最新内容。
2. 计划生成后同一位置变为 AI 气泡：目的、完整命令、执行目录、风险说明，末尾是
   醒目的待确认卡片（执行 (y) / 取消 (n)），光标闪烁提示等待你的决定。
3. 输入 `y` 回车（或点内联按钮）→ 计划以精确 hash 提交，追加 `$ 命令`、运行状态、
   stdout/stderr、`[exit 0]`，最后是 AI 解释。输入 `n` → 取消并显示“未执行”。
4. 失败/取消后可以继续输入新需求，也可以点击“重新规划”。
5. `↑`/`↓` 在输入框内翻看本次会话输入历史（像 shell 历史）；不是执行历史命令，
   仍需重新规划与确认。

确认语义不变：`y` 是对屏幕上看得到的那份固定计划的显式确认，一次性代表
“以当前账号运行、无 OS 沙箱、接受可能的文件修改/联网影响”。若计划文件/网络
影响较大，确认提示会先列出影响行；内容变化（hash 变）则 `y` 无效，必须重新生成。

## 会话上下文

终端转录天然是上下文。规划时后端附带最近若干轮（最多 6 条已结束任务）的
“需求 + 已知命令 + 退出码 + 截断输出”作为**不可信证据**给模型，使“再看看可用内存”
这类追问能引用上文；模型只能在上下文里读取，不能因为上下文把旧确认复用到新命令。
新命令仍是新计划、新 hash、新确认。SQLite 是事实源；页面只按时间正序展示。

## 后端改动

- `GET /api/terminal/transcript?limit=`：正序返回最近任务完整详情（plan/steps/
  summary/approval），用于首屏滚屏恢复；仍复用 `get()`，最多 20 条。
- `TerminalService` 规划时读取最近结束任务作为上下文，输出截断到有界字符数，
  并在提示中声明输出为不可信数据、不能当指令。
- 不新增执行能力；`/api/terminal`、确认、取消接口保持兼容。

## 前端改动

- 页面改为 console 布局：窗口框架 + 滚动转录 + 底部输入；模型、相对目录、工作区
  收进标题栏/工具行，不占主视觉。
- 转录条目组件按任务渲染：需求行、计划块、确认提示、执行输出、解释；`详情`
  折叠里保留环境变量、hash、授权记录，避免伪造“安全区”。
- 轮询仅在转录需要时（有 planning/queued/running 任务）加速；回车/`y`/`n` 的
  输入在请求中禁用重复提交。
- 明确 UI 文案：这不是交互式 PTY，自由文本一定先经 AI 规划，不会被直接当 shell 执行。


## 只读免确认与结果优先（2026-11-26）

用户反馈两点：确认卡片只说“无 OS 沙箱”，看不出到底要确认什么；回答把命令和解释
堆在一起，要先读长解释才能看到结果。据此调整：

- **可证明只读才自动执行**：新增 `read_only_invocation()` 与 `all_read_only(plan)`。
  仅当每一步都是 `exec`、程序位于 `/usr/bin`、`/bin`、`/usr/sbin`、`/sbin` 的固定
  绝对路径，且参数逐个命中白名单（`uname`/`sw_vers`/`sysctl -n` 已知键/`pwd`/`id`/
  `ls` 组合短参/`df`/`du`/`whoami`/`vm_stat`/`lsof -nP -iTCP`/`git status|log|branch`
  等）时才 `auto_run=true`；shell、管道、脚本、未知程序、写文件、联网一律仍需确认。
- **自动执行仍留审计**：保存计划后立即 `approval={"auto_readonly": true}`；执行前
  再次校验 `all_read_only`，防止保存后被篡改；自动计划跳过确认但仍在转录里可见。
- **确认卡片说人话**：`step_effects()` 产出“只读取信息 / 可能写入或覆盖文件 /
  可能删除文件 / 可能安装软件 / 可能修改系统设置 / 可能访问网络”，卡片先列这些
  影响，命令本身折叠在“查看即将执行的命令”里，供看得懂命令的人展开。
- **结果优先**：`result_digest()` 从真实 stdout 确定性生成一句话结论（架构、内存
  GiB、CPU 型号、macOS 版本、Git 分支/是否干净），写入 `terminal_tasks.digest`；
  有 digest 时直接以它作为“结果”卡片，模型的解释只作补充，原始输出折叠。
  总结提示同时改为“先给关键结果、最多两句说明、不建议额外命令、不用代码围栏”。
- **意图归一化**：问“CPU 型号/处理器/芯片”而模型只给 `uname -m` 时，
  `normalize_for_intent()` 换成 `sysctl -n machdep.cpu.brand_string`，避免再拿架构
  当型号；问“架构”保持 `uname -m`。

验收：后端 95 项（含只读自动执行、写文件仍需确认、绕库确认被拒、CPU 归一化）；
前端 17 项（含免确认徽标、影响清单 + 折叠命令、结果先于原始输出）。

## 验收

- 后端：transcript 正序、条数上限、context 注入不改变确认绑定的测试。
- 前端：转录渲染（需求/命令/输出/确认提示）与 `y`/`n` 解析的组件测试。
- 真实：用同一句“查看电脑内存”在 console 里完成对话式确认与结果展示；再用
  追问验证上下文；“n”取消不执行。
- 不改动既有聊天/知识/任务中心/端口事实范围；不新增依赖、不引入内部资源。

### 版本号查询与用户工具链（2026-11-26 追加）

- 现象：问“node 版本号”时模型先生成 `which node`，沙箱 PATH 不含 nvm，步骤退出码 1，
  后续 `node --version` 未执行，界面只剩“命令退出码非零”。
- 修正：`SEARCH_PATH` 增加用户自己的工具链目录（`~/.nvm` 默认版本 → Volta →
  `~/.local/bin` → `~/.cargo/bin` → Homebrew → 系统目录）；`read_only_program()` 以
  目录身份（含 macOS firmlink 解析）判定可信任路径。
- 对“某工具版本号”这类单一、纯查询请求走确定性快路径：直接解析到绝对路径并生成
  `--version` 计划，不经过模型、不产生 `which` 中继步骤；解析不到就明确说“PATH 里
  没有找到 node”，而不是留一个失败的 which。结果摘要固定为“Node.js 版本：24.14.1”。
- 失败文案改为“<程序> 退出码 N：<stderr 首行>；后续步骤未执行”，让人知道为什么。

### 脚本级只读证明与清单查询范围（2026-11-26 追加）

- 现象：`ls /Applications /usr/local/bin | grep -i 'mysql\|redis'` 这类纯读命令仍弹确认
  （旧逻辑把所有 `kind=shell` 一律当“写”）；确认后 `grep` 无匹配退出码 1，又被判成
  “命令退出码非零”，界面只剩失败文案。用户因此质疑“只读为什么还要确认、为什么像
  打补丁一样一个个加白名单”。
- **原则取代白名单**：新增 `read_only_script(script)`——先剔除允许的重定向
  （`2>/dev/null`、`>/dev/null`、`2>&1`、`&>/dev/null`），再拒绝反引号、`$(`、括号、
  残留的 `&`/`<`/`>`；按未引号区的 `| ; & 换行` 切段；每段首程序须在 `SEARCH_PATH`
  里解析到系统目录或用户工具链目录，参数走 `read_only_invocation()` 或 `READ_TOOLS`
  专用校验（grep/cat/head/tail/wc/cut/tr/echo/printf/basename/dirname/file/stat/
  strings/jq/ps/ls/which/launchctl 等；sort 禁 `-o`、uniq 位置参数 ≤1、find 禁
  `-delete/-exec/-fprint*`、launchctl 只允许 `list`）。`sudo/eval/xargs/sh/rm/mv/cp/
  dd/mkdir/touch/ln/chmod/kill/brew/pip/npm/open/curl/ssh/rsync` 等任一段出现即拒。
  于是 `a | b`、`a; b`、`2>/dev/null` 组合的纯读脚本一次性全部免确认，新增只读工具
  不必再改白名单，只要它在 `READ_TOOLS` 里或参数通过通用校验。
- **只读步骤非零不算失败**：`grep`/`find`/`lsof` 退出码 1 表示“无匹配”，执行循环把
  只读步骤的非零当 `completed` 继续，不再阻断后续步骤。
- **无匹配固定结论**：全部步骤 `exit_code==1` 且 stdout 为空时，结果卡写
  “没有找到匹配项（命令退出码 1 表示没有匹配，不是执行出错）”。
- **grep 交替修正**：BSD grep 不认 GNU `\|`，`fix_grep_alternation()` 把
  `grep -i 'a\|b'` 归一为 `grep -Ei 'a|b'`。
- **清单查询必须搜真实安装目录**：模型只猜 `/Applications`、`/usr/local/bin`，而 MySQL
  实际装在 `/opt/homebrew/bin`，结论误报“没有”。因此问“装了哪些软件/数据库/工具”时，
  `fix_inventory_scope()` 把 `ls <dirs> | grep ...` 的目录补全为 `SEARCH_PATH` 里真实存在
  的目录（去重、跳过工作台自身 venv），免确认规则不变；非清单类 `ls` 不动。
- 规划上下文新增 `path_dirs`，并在提示里写明“已安装程序在这些目录、清单类问题用一条
  只读 `ls <dirs> | grep -Ei` 步骤”。

验收：问“我的电脑上目前有啥数据库啊”自动执行（无确认卡），一条只读管道覆盖
`/opt/homebrew/bin`，结果给出 `mysql`、`sqlite3`；`ls | grep` 无匹配时给“没有找到匹配项”
而不是失败红字。后端 99 项用例通过。

### 确认策略 REDESIGN：按“会不会改东西”判断，不按工具白名单（2026-11-26 追加）

用户第三条反馈点破根因：判断逻辑本身不对——白名单式“可证明只读”永远追不上用户下一个
问题，于是同一个“查看”请求时而免确认、时而又弹卡（`python 版本呢？` 被解析成
DoubaoWork 沙箱里的 python3.14，不在受信任目录 → 确认；确认卡还写“可能访问网络”）。

新策略只有两条判据，不再枚举工具：

1. **请求是不是“看”**：`OBSERVE_INTENT`（查看/看看/查一下/查询/列出/是什么/多少/
   有没有/哪些/版本/型号/状态/装了…）。是“看”，默认直接执行。
2. **命令会不会改东西**：`writes_anything(step)` 硬拦截写、删、装、改设置、联网——
   `rm/rmdir/mv/cp/dd/truncate/touch/mkdir/ln/tee/chmod/chown/kill(pkill)/shutdown/
   diskutil/sed -i`、写文件重定向（`>`/`>>`，`/dev/null` 除外）、`brew|apt|pip|npm|
   yarn|pnpm|gem|cargo|go + install/update/remove`、`git add|commit|push|pull|reset|
   checkout|switch|restore|clean|merge|rebase|stash|tag|init|clone|remote|config|
   branch -D`、`sudo/doas/xargs`、解释器带脚本或 `-c/-e`（`bash scripts/start.sh`、
   `python3 -c ...`）、`osascript/defaults write/networksetup/systemctl/launchctl
   load|unload|...`、`open/curl/wget/nc/ssh/scp/rsync`、`docker run|rm|...`、
   `find -exec/-delete`、`tar -x/-c`，以及数据库客户端里的 `drop/delete/insert/
   update/alter/...`。
   命中任意一条就回到确认，不管问句多么像“查看”。

两条同时满足 → `observation=True`、`auto_run=True`，审计标记
`{"auto_observe": true}`；执行前 `check_approval()` 用同一套判据复验，防止保存后被改。
确认卡的影响文案对这类计划统一写“只读取信息，不会修改文件或系统设置”。

顺带把版本查询兜底做到通用：不再依赖工具名表，问“X 版本呢”时把句子里能 `which`
到的唯一工具作为目标（`python`→`python3`、`pip`→`pip3`、`nodejs`→`node` 有别名），
所以“我的python 版本呢？”直接走确定性路径，结果为“Python 版本：3.9.6”。

验收（真实环境）：
- “我的python 版本呢？”→ 免确认，`/usr/bin/python3 --version`，结果“Python 版本：3.9.6”。
- “看看我的磁盘还剩多少”→ 免确认，`/bin/df -h`，结果“磁盘剩余空间：665Gi”。
- “在 /tmp 下新建一个 a.txt 写 hello”→ 仍要求确认（`echo ... > /tmp/a.txt` 命中写重定向）。
- 后端 101 项用例通过。

### 上下文预算（2026-11-26 追加）

终端从设计上就不会把对话无限堆给模型，现有三道闸门：

1. **会话窗口是固定的**：`session_context()` 只取最近 6 次完成/失败的交换，每次保留
   最多 4 条命令、每步输出截 400 字符、整体输出再截 600 字符。历史只作“理解追问”的
   证据，明确标注是不可信数据、不能沿用旧授权。
2. **执行输出是封顶的**：单步 `LIMIT = 128KiB`，超限即停并提示“不代表完整结果”；
   一个计划最多 4 步；单步 300s、整体 1230s。
3. **提示词按 NUM_CTX 记账**（本次新增，与聊天/Agent 同一套约定，1 字节记 1 token 保守估算）：
   - `prompt_budget()` = `num_ctx - num_predict - 512`；
   - 规划：系统提示 + 当前问题的字节数若已超预算，任务直接 `failed` 并说明
     “系统提示加问题约 X 字节，已超过预算 Y 字节（NUM_CTX=…），请精简问题，或在 .env
     调大 NUM_CTX”——不再静默溢出（Ollama 溢出时会悄悄裁掉最前面的 system/instruction）；
   - 没超时，`session_context(budget=剩余预算)` 会把最旧的轮次先丢掉，只留放得下的部分；
   - 汇总：给模型的证据长度改为 `min(3000, 剩余预算)` 动态计算，而不是永远 3000 字符。

仍未做的（明确记录，不假装有）：真正 tokenizer 计数（现为字节保守估算）；证据截断
只保留前段（长输出的尾部信息可能丢）；不做跨任务摘要，终端永远只有 6 轮窗口，更早的
历史需要用户重新说明。

验收：`my python 版本呢？` 正常执行不受影响；1600 字的超长问题返回
“这次请求太长 …（NUM_CTX=8192），请精简问题，或在 .env 调大 NUM_CTX”，不再把请求
送进一个装不下的窗口。后端 103 项用例通过。

### 会话与上下文用量（2026-11-26 追加）

终端原来只有一条全局转录，追问没有边界，也看不见自己占了多少窗口。现在拆成会话：

- **每段对话是一个 `conversation_id`**：`terminal_conversations` 存会话，`terminal_tasks`
  增列 `conversation_id`；历史任务在迁移时归到最早的那个会话，不会凭空消失。
- **历史只在本会话内使用**：`session_context()` 按 `conversation_id` 过滤，规划提示里的
  “最近终端转录”只含本会话最近 6 轮；换会话即换上下文，模型不会串味。
- **新开对话**：`POST /api/terminal/conversation` 建新会话并返回它的用量；前端标题栏
  的“新开对话”按钮直接切过去，转录清空，旧会话的记录仍留在库里可按 id 查看。
- **上下文用量可见**：`GET /api/terminal/conversation` 返回
  `system_bytes`（固定提示约 3.3K）、`history_bytes`（实际送进模型的历史，已按剩余预算裁剪）、
  `raw_history_bytes`（本会话原始历史）、`budget_bytes`（NUM_CTX 预算）、`used_bytes`、
  `remaining_bytes`、`percent`、`turns`/`raw_turns`。底部状态栏显示
  “上下文 3.4K / 6.5K（52%）· 历史 1/6 轮 · 剩 3.1K”，悬停可看原始历史被裁到多少。
- 预算不足时先裁最旧轮次；只剩一轮还装不下时把这一轮的 `request/commands/output`
  缩到 80 字符保留——**宁可短，也不要把“上一句是什么”整个丢掉**，否则追问会答非所问。

验收：新会话 `turns=0`；切回旧会话仍能看到原任务与用量；59 条历史的老会话
`raw_history_bytes=15.2K` 而 `history_bytes` 被裁到 154 字节，`percent` 仍为 52%，
追问（“那内存呢？”）依旧能识别上下文。后端 104 项、前端 17 项用例通过。
