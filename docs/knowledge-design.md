# 知识库与引用问答技术方案

## 目标

单机导入 Markdown/TXT（单文件不超过4MB），以结构切片保存并索引，支持
十几万字资料的局部问题检索；回答附真实片段链接。不是一次性全文通读。

## 数据与一致性

SQLite为事实源：documents增加状态/错误/摘要哈希/版本/文件大小，chunks保存
文本、标题路径、原始行号和顺序。原始文件保存在配置数据目录，名称是随机ID，
拒绝用户提供路径。LanceDB仅存可重建的检索副本（chunk_id/vector/text）。
导入：写文件→解析/切片→事务保存pending记录→受控后台队列embedding→向量表
→状态ready。删除/重建与索引任务串行，SQLite ready文档ID过滤所有召回，
防止失败/删除的向量成为可见答案。重启将indexing状态回到pending并重试。
失败存安全错误，不删除原文。重复内容哈希可识别；修改可通过删除再导入。

## 切片

按Markdown标题树/段落/代码围栏扫描，保存heading和start/end_line。
不将代码中的#识别为标题，保留代码/表格段落，长块才按有界字符切分；
超长代码块允许被切分并明确其片段身份。参数验证防死循环。实际embedding
输入还验证长度，设置truncate=false，不静默截断。先保守控制每片600字。

## 本地嵌入及混合检索

使用已有Ollama运行bge-m3（公开权重，单独下载，接入只消费dense向量）。
LanceDB exact vector search用于小数据规模；不提前建立复杂近似索引。
关键词由SQLite FTS5实现，中文按连续字符的二元组、英文按单词切分生成FTS
字段；不把英文默认分词当作中文已支持。向量与关键词结果使用RRF融合，
限定ready文档并去重。返回Top-K及邻接来源元数据；无相关结果不强行作答。
LanceDB同步操作放线程，不阻塞事件循环；所有写操作串行。

## API

- POST /api/documents 上传，返回文档ID/索引状态。
- GET /api/documents 列表与进度。
- GET /api/documents/{id} 原文、片段、行号。
- POST /api/documents/{id}/reindex 重建任务。
- DELETE /api/documents/{id} 删除文件、元数据、向量。
- POST /api/knowledge/search 返回可预览引用片段。
- 聊天请求use_knowledge_base=true在生成前检索，SSE citation事件携带来源；
  对话存citation字段，刷新保留。模型使用[1]形式引用，候选来源与生成引用分开。

## 安全及失败处理

仅.md/.markdown/.txt；UTF-8、尺寸验证，不执行frontmatter、不跟随附件链接。
文档片段作为不可信证据，不能修改系统指令或授予工具权限。路径只来自服务端
生成；引用检索只在已导入集合内。索引与LLM并发控制，不允许无限任务堆积。
不下载PDF解析/OCR，也不读取其他本地目录。

## 验收与批次

批次1：schema/切片/存储/索引队列及单测，测试通过commit。
批次2：检索、聊天引用、知识UI（上传状态/预览/删除/重建），真实embedding+LLM
回归和浏览器操作通过commit，再整体push。测试包含中文精确词、代码标题、
索引失败/restart、删除后无召回、无文档、路径/扩展/大小拒绝及引用持久化。
