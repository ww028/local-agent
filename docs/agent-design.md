# Agent 工具执行技术方案

## 目标与边界

把纯RAG聊天升级为模型驱动的工具循环：模型决定要不要搜索知识、读取片段、
计算；工具结果返回模型继续作答。UI显示步骤事件而不是暴露模型内部推理。
默认只读，无shell/任意Python/网络/写文件/外发动作。一个运行最多6步/8次
工具调用/120秒工具循环，超过预算明确结束，不假装完成。

## 实现

Ollama /api/chat 的tools JSON Schema，think=false，非流式工具决策；
当tool_calls非空：Pydantic校验参数→查已注册工具→执行→持久化tool_start/
result/error事件→将结构化tool结果回灌。无tool_calls时输出最终内容。
若模型不支持tools，则拒绝Agent模式并提示普通聊天。最后答案照常保存会话。

工具：search_knowledge(query,top_k)、read_document(document_id,chunk_id可选)、
calculator(expression)。读取限已导入文档、单次不超过6000字符，返回片段
元数据。计算AST只允许数值、括号及加减乘除幂，限制输入长度/节点/指数，
拒绝变量/属性/函数调用/大型指数，不能eval用户表达式。

SQLite runs表(会话/消息/模型/状态/开始结束)与run_events(run_id/seq/type/
JSON)；事件每次写入，可刷新重开。SSE增加step事件，run_id跟随meta，
取消传播到HTTP请求和工具await，finally记录interrupted并解锁。
工具结果和导入内容是不可信证据，不能授予新工具权限。工具注册白名单是
权限边界，不把提示词当安全边界。

## 接口及UI

ChatRequest增加mode=chat|knowledge|agent；兼容use_knowledge_base。
GET /api/runs/{id}查询事件，GET /api/runs列表。对话消息存run_id，
执行面板列出工具名称、参数、结果摘要和耗时；不呈现隐藏推理。

## 测试与批次

批次1：AST计算、工具参数/读取范围、运行记录/预算/取消单测→commit。
批次2：Ollama工具循环、SSE执行面板、真实Qwen调用至少一个工具→commit→push。
模拟覆盖未知工具、非法参数、空知识库、重复调用、预算耗尽和断流；真实测试
不能用手动直调工具冒充模型工具选择。
