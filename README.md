# local-agent

**本地优先、运行时无需云 API 的开源 Agent 工作台。**

聊天、Markdown 知识库、带来源回答、受控工具执行在自己的电脑上运行。
代码 MIT，模型遵循各自许可。首版为单人单机开发者产品，不是多租户企业生产服务。

## 已实现

- **自由对话**：本地模型、流式回答、停止生成、SQLite 会话恢复。
- **知识库**：Markdown/TXT 上传、标题/代码围栏感知切片、索引进度、失败重试、
  原文及片段预览、删除、内容去重。
- **引用问答**：LanceDB 向量 + SQLite FTS5 中文二元词关键词召回，RRF融合，
  回答引用来源可跳回原文；引用随历史保存。
- **Agent**：模型自主选择知识搜索、文档读取、受控算术计算，工具事件持久化，
  可查看执行过程与历史记录；有步数、时间、上下文预算和取消机制。
- **会话管理**：搜索、重命名、删除、Markdown 导出、浏览器会话恢复。
- **内容展示**：本地数学公式、Markdown表格与代码高亮，消息复制、独立执行记录页。
- **本地边界**：仅loopback，拒绝云模型，工具无任意shell/网络/本地路径能力，
  不加载模型输出中的远端图片；无遥测、无贡献率采集或内部资源。

## 后台任务中心

打开导航中的“任务中心”，输入指令并提交。任务立即持久化到本机数据库，
由独立后台 worker 执行；网页默认展示状态和结果，工具事实/执行明细折叠可查。
刷新、换页或关闭网页不会取消任务；可取消排队/执行中的任务，失败、取消或
中断后可显式创建重试任务，旧记录保留。电脑和后台服务必须保持运行。

例如输入“查询8091端口被哪个进程监听”，**先勾选允许只读本机诊断**。
诊断仅开放 TCP 监听进程与系统基本信息，不开放任意命令、结束进程或桌面控制。
普通聊天不会自动获得诊断权限。服务重启继续排队任务，执行中任务标记中断，
不自动重放。详见[后台任务技术方案](docs/background-jobs-design.md)。

## AI终端（生成式V3）

自然语言描述 → AI生成实际命令/参数或完整shell脚本 → 查看命令、目录、风险 →
你确认 → 后台执行 → 原始stdout/stderr/退出码与AI解释。不是调用固定功能枚举，
内存/磁盘/系统查询、项目测试/构建、文件操作和复杂管道都可以生成命令计划。
脚本/安装等是否成功仍取决于本机环境和模型正确性，不保证任意任务成功。

每份计划必须确认当前账号权限；可能执行代码、修改文件或联网的计划还需额外
勾选对应影响。确认绑定完整命令，10分钟有效，修改后重新确认，失败不自动换
命令继续。刷新/换页不取消已确认执行；取消仅停止进程，不回滚文件修改。

**没有OS沙箱或网络防火墙。**初始cwd限制在配置工作区，但命令可以访问当前
账号能访问的文件和网络；风险提示不是安全证明。运行时推理本地，确认的命令
可能联网，与模型禁云是不同边界。不要对不可信项目/脚本提供授权。

默认工作区为本仓库，可通过本机`.env`的`TERMINAL_WORKSPACE`改为另一可信项目。
不提供sudo/密码交互、凭据目录操作、PTY或常驻服务。旧版只读任务记录保留；
旧失败记录点击重新规划即可走生成式流程。详见[生成式终端方案](docs/generative-terminal-design.md)。

## 快速开始

前置：Python 3.12 推荐（本机3.14测试通过）、Node 20.19+ / 22.12+、官方 Ollama。
下载依赖和权重需要联网；安装好后的应用请求走本机。

```bash
git clone https://github.com/ww028/local-agent.git
cd local-agent
cp .env.example .env
bash scripts/setup.sh
# 终端1，启动仅本地且禁用云的模型服务
bash scripts/ollama.sh serve
```

```bash
# 终端2，首次联网下载模型，已有则无需再下
bash scripts/ollama.sh pull qwen3:14b
bash scripts/ollama.sh pull bge-m3
bash scripts/start.sh
```

打开 **http://127.0.0.1:8000/**。模型选择 qwen3:14b，工作模式可选自由对话、
知识库问答或 Agent 工具。知识问答前先到知识库导入文档，等待状态“可检索”。
模型和依赖不随仓库分发，单文件最大4MB，上传只支持 UTF-8 Markdown/TXT。

第一次体验：导入 `examples/sample-knowledge.md`，在知识模式提问设计原则；
在 Agent 模式要求“使用计算工具计算 (73*4)+8/2”，展开执行记录观察调用过程。
工具只读，不会执行shell或外发消息。

## 架构与方案

| 层 | 实现 |
|---|---|
| Web | React / TypeScript / Vite |
| API | FastAPI / Pydantic / HTTPX |
| 推理 | 本地 Ollama 聊天与嵌入 |
| 业务数据 | SQLite：会话、文档、片段、任务队列、运行事件 |
| 检索副本 | LanceDB dense vectors + SQLite FTS5 |

方案先于模块实现：
- [总方案](docs/product-plan.md)
- [知识库方案](docs/knowledge-design.md)
- [Agent方案](docs/agent-design.md)
- [工作台方案](docs/workbench-design.md)
- [启动/配置](docs/setup.md)
- [验收记录](docs/product-acceptance.md)

## 验证

```bash
cd backend
.venv/bin/python -m pytest -q
.venv/bin/ruff check app tests
cd ../frontend
npm test
npm run build
```

真实本地测试另有 `scripts/smoke-local.py`，不能把mock测试当成真实推理。
仓库源检查：`python scripts/check-public.py`。它只是辅助检查，不是完整秘密扫描。

## 边界与后续

首版不支持PDF/OCR、看图、任意代码执行、联网搜索、企业连接器、多人登录，
不宣称十几万字能一次性装进上下文。知识库适用于局部证据检索；全文分层摘要
需后续设计。Agent工具选择仍受模型能力影响，执行记录是动作摘要，不是隐藏推理。

当前支持本地静态打包运行（8000）及Vite开发热更新（5173）；单后端worker，避免多实例共用数据库。无企业认证/
审计/高可用，不对公网开放。物理断网、长期压力与完整安全审计未认证。

## 开源

源码 [MIT](LICENSE)，模型许可见 [models.md](docs/models.md)。权重、私有资料、
`.env`、运行数据库和缓存不提交。贡献规则见 [CONTRIBUTING.md](CONTRIBUTING.md)。
