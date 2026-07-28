# V2 现有功能稳定性优化验收报告

## 1. 目标与边界

本轮不新增业务模块，不改变 V2 核心闭环，也不重写既有架构。优化范围限定为：

```text
资料入库 → 检索与 RAG → 模拟面试 → 可信评分 → 报告 → 能力画像
```

兼容性约束：

- 不修改既有 API 路径。
- 不删除既有响应字段，只为 RAG 响应增加运行态字段。
- 不修改数据库表结构。
- 不引入消息队列、外部向量服务或新的部署容器。
- 保持 Docker Compose 三容器和 16GB 本地开发机约束。

## 2. 第一批：运行态透明与前端容错

### 2.1 已完成

- RAG 响应增加 `generation_mode`、`model_name`、`fallback_reason`。
- 前端区分 LLM 成功、确定性降级和证据保护降级。
- 模型知识补充改为用户显式开启，默认只基于知识库证据回答。
- API 客户端兼容非 JSON 错误响应，并增加 30 秒超时提示。
- 工作台核心请求与可选面板请求解耦，画像或趋势接口失败不再拖垮整页。
- 保存最近使用的知识库，刷新后优先恢复。
- 工作流轨迹默认折叠。
- 演示就绪状态改为中文，并展示通过项数量。

### 2.2 验收标准

- 既有 API 路径保持不变。
- 未配置 LLM、LLM 调用失败、证据不足三种情况均可区分。
- 非核心面板失败时，知识库、RAG 和面试功能仍可使用。
- 前端生产构建通过。

## 3. 第二批：一致性与中断恢复

### 3.1 已完成

- 答案幂等键按“面试 + 题目”保存，请求成功后清除；网络重试复用原 Key。
- 报告由“先删除再新建”改为事务内创建或更新，失败时不删除旧报告。
- API 启动时识别超时的 `pending/processing` 文档，将其标记为可重试失败。
- 前端失败文档提供“重新索引”入口和错误原因。
- 重建索引按 `chunk_index` 原位更新，保留 chunk ID，避免破坏历史题目和评分引用。
- 复核既有画像防重复机制：
  - 应用层先查询 `ProfileUpdateEventModel`。
  - 数据库对 `evaluation_id` 设置唯一约束。
  - 无需新增表或迁移。

### 3.2 验收标准

- 同一题相同幂等键重复提交只保存一个答案。
- 同一面试重复生成报告保持同一个报告 ID。
- 同一批 Evaluation 重复应用画像，不重复增加版本和置信计数。
- 服务重启遗留的文档任务不会永久卡在处理中。

## 4. 第三批：检索效果与题目去重

### 4.1 已完成

- 保持 `DevelopmentEmbeddingGateway` 接口和 1536 维不变。
- 将“整段 SHA256 随机向量”替换为字符 n-gram 与英文词的 feature hashing 向量。
- 向量进行 L2 归一化，仍支持离线、确定性和低资源运行。
- 面试检索词按概念、场景、设计、排障题型加入不同检索提示。
- 出题 Prompt 带入本轮历史题目。
- 新题与历史题目相似度过高时，退回对应题型的确定性模板。

### 4.2 边界说明

该 embedding 是本地轻量语义近似基线，不冒充生产级神经网络 Embedding。它解决的是原 SHA256
向量完全不保留文本相似性的问题；生产环境仍可通过既有 `EmbeddingGateway` 端口替换为正式模型。

### 4.3 验收标准

- 相同输入向量完全一致。
- 向量维度保持配置值，非空文本向量归一化。
- 相关文本相似度高于无关文本。
- 同轮面试的高度重复题被拦截，不同考察角度正常放行。

## 5. 严格回归范围

自动化覆盖：

- 文档解析、分块与复杂块类型。
- 检索规范化、RRF、引用白名单和本地 embedding 相似度。
- RAG LLM 失败降级及运行态字段。
- 面试状态迁移、checkpoint、题型递进和题目去重。
- Rubric 评分、低置信复核路由和报告计算。
- 画像可信更新、错误模式、复习任务和训练排序。
- PostgreSQL/pgvector 真实入库与召回。
- 答案幂等、面试恢复、报告重复生成、画像重复消费。
- 文档后台任务中断恢复。

最终验收命令：

```powershell
docker run --rm --network personal-rag-bot_default `
  -e AGENT_MENTOR_TEST_DATABASE_URL=postgresql+asyncpg://agentmentor:agentmentor@db:5432/agentmentor_test `
  -e AGENT_MENTOR_APP_ENV=test `
  -v "D:\AgentStudy\personal-rag-bot:/work" -w /work personal-rag-bot-api `
  sh -c "python -m pytest"

npm.cmd run build
```

## 6. 对既有文档的影响

V1 与 V2 的项目背景、总体架构、核心数据流和状态机保持有效。本轮只需要在代码走读时补充：

1. 本地 embedding 已从随机确定性向量升级为 feature hashing 相似度基线。
2. RAG 接口可显式说明本次生成模式和降级原因。
3. 报告、答案和画像分别具备事务、幂等和唯一消费保护。
4. 本地 BackgroundTasks 发生进程中断后支持识别与手动重试。

这些内容是原有能力的稳定性增强，不构成 V3，也不需要重画总体架构图。

## 7. 最终验收结果

验收日期：2026-07-29。

| 检查项 | 结果 |
| --- | --- |
| 后端单元测试与数据库集成测试 | `42 passed` |
| PostgreSQL/pgvector 隔离数据库闭环 | 通过 |
| Ruff 静态检查 | `All checks passed` |
| Ruff 格式检查 | `72 files already formatted` |
| Pyright 类型检查 | `0 errors, 0 warnings` |
| React 生产构建 | 通过，36 modules transformed |
| Git 空白错误检查 | 通过 |
| Docker Compose 最终重建 | db、api、frontend 均成功启动 |
| API 健康检查 | `/health/ready` 返回 `ok` |
| LLM 运行态 | DeepSeek `deepseek-chat` 已启用 |
| 前端 HTTP 冒烟 | `http://localhost:3000/` 返回 200 |
| 演示就绪度 | `100% / ready` |
| 现有资料向量迁移 | 12 份活跃资料重新索引为 READY |
| RAG 运行态冒烟 | 证据充足、LLM 成功、3 条合法引用 |

结论：本轮优化未改变总体架构和核心数据流，现有功能通过单元、类型、格式、真实数据库集成、
容器重建和 HTTP 运行态五层验收，可以进入代码走读与面试材料准备阶段。

已知数据问题：一份早期 `agentmentor-phase1.md` 的源文件已不在 Docker uploads volume 中，系统按预期
保留 `failed` 状态和明确错误信息。其余 12 份活跃资料已完成新 embedding 空间迁移。该问题属于历史
源文件缺失，不是代码或索引算法失败；如仍需该资料，需要用户重新上传原文件。
