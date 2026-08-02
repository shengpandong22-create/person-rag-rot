# 知识库画像隔离与新资料库验收报告

验收日期：2026-08-02

## 1. 改造目标

- 能力画像、错误模式、复习任务、更新事件、报告历史和趋势全部绑定知识库。
- 切换知识库时只恢复对应知识库的学习状态，不展示上一个知识库的残留数据。
- 清理旧面试与画像历史，同时保留知识库、文档、切片和 RAG 聊天数据。
- 创建一套按主题拆分的 AI Agent 面试知识库，并完成真实闭环验收。

## 2. 数据迁移与清理

- 数据库迁移版本：`20260802_0009`。
- 迁移后 `ability_profiles`、`profile_update_events` 的空知识库归属均为 0。
- 清理前：32 场面试、65 条评分、23 份报告、151 个画像节点、86 个错误模式、86 个复习任务、63 条画像更新事件。
- 清理后：上述训练历史均为 0。
- 保留：37 个知识库、16 份旧文档、317 个旧切片。
- 可恢复备份：`backups/agentmentor-before-learning-reset-20260802.dump`。该目录已加入 `.gitignore`，备份只保存在本机。

## 3. 新知识库

- 名称：AI Agent 开发面试知识库
- ID：`46691546-593a-4d21-bcfc-0d16986c20a7`
- 资料目录：`docs/evaluations/fixtures/agent-interview-kb-20260802/`
- 文档数量：8，全部解析为 `ready`。
- 覆盖主题：RAG、LangChain、LangGraph、上下文与 Memory、工具调用与 MCP、评估与可靠性、Agent 生产工程。

资料基于官方文档整理，主要来源：

- https://docs.langchain.com/oss/python/langchain/agents
- https://docs.langchain.com/oss/python/langchain/structured-output
- https://docs.langchain.com/oss/python/langchain/middleware/overview
- https://docs.langchain.com/oss/python/langgraph/persistence
- https://docs.langchain.com/oss/python/langgraph/interrupts
- https://docs.langchain.com/oss/python/langchain/context-engineering
- https://docs.langchain.com/oss/python/langchain/tools
- https://docs.langchain.com/oss/python/langchain/mcp
- https://learn.microsoft.com/azure/developer/ai/advanced-retrieval-augmented-generation
- https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents

## 4. RAG 知识边界验收

### 资料内问题

问题：LangGraph 的 Checkpoint 能解决什么问题，又不能自动保证什么？

结果：`evidence_sufficient=true`，返回 3 条引用，使用 LLM 基于证据生成。

### 资料外问题

问题：要求回答资料库未收录的量子色动力学最新实验结论。

结果：`evidence_sufficient=false`，引用为 0，生成模式为 `evidence_guard`，降级原因为 `insufficient_evidence`。系统明确提示补充资料或允许带标记的模型知识，不把模型常识伪装为资料结论。

## 5. 面试与画像隔离验收

- 验收会话：`70c1ed7c-0fb8-42ce-8509-2e41b9979c2a`
- 主题：LangGraph
- 题数：3
- 状态迁移：前两题提交后为 `waiting_for_answer`，第三题后为 `completed`。
- 报告：58/60，共 3 条逐题评分。
- 新知识库：5 个画像节点，1 条报告历史。
- 对照知识库 `5142fba3-f9e6-4628-a3f5-855f4ffd8361`：0 个画像节点，0 条报告历史。

结论：面试、报告和画像的知识库隔离成立；同一本机用户在不同知识库中拥有独立画像。

## 6. 自动化回归

- Ruff：通过。
- Pytest：51 passed，1 skipped。跳过项为需要独立 PostgreSQL 测试库的集成测试；跨知识库隔离断言已写入该用例，并另行通过 Docker 实库验收。
- 前端生产构建：通过，43 个模块完成构建。

## 7. 旧知识库清理

在完整数据库备份已校验的前提下，进一步删除了 37 个历史测试知识库及其关联数据：

- 16 份旧资料。
- 317 个旧切片。
- 37 个旧聊天会话、74 条旧消息和 33 条旧引用。

清理完成时数据库只保留 `AI Agent 开发面试知识库`：

- 知识库：1 个。
- 文档：8 份，全部为 `ready`。
- 能力画像：5 个节点。
- 面试报告：1 份。

## 8. Java 对照知识库与双向隔离复验

为使知识库切换和画像隔离可以在最终界面中持续复验，新增：

- 名称：Java 后端面试知识库
- ID：`2c6f2730-852e-4d94-8bc8-3de1b840ed95`
- 资料：4 份，覆盖 JVM、Java 并发、Spring 事务与生产化，全部为 `ready`。
- 资料目录：`docs/evaluations/fixtures/java-backend-interview-kb-20260802/`

Java 验收面试：

- 会话：`fdb39ddf-597d-42a7-9b22-1f3a09f2b07c`
- 三题均引用 Java 知识库自己的检索片段。
- 报告：56/60。
- Java 画像：从 0 增长至 3 个节点，报告历史 1 条。

隔离对照：

- Java 面试前后，AI Agent 画像均为 5 个节点，报告历史保持 1 条。
- Java 知识库为 3 个画像节点、1 条报告历史。
- 在 AI Agent 知识库询问 `volatile/count++`：证据不足，拒答。
- 在 Java 知识库询问 `LangGraph interrupt`：证据不足，拒答。

最终数据库包含 2 个可切换知识库，两套画像和报告相互独立。
