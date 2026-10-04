# 用户触发二阶段检索：API、Trace 与上下文预算设计

## 1. 状态与范围

本文定义二阶段扩展检索的实现契约，但不实现或授权生产功能。当前生产 `ask`、Retriever、
RRF、Embedding、Evidence Gate、阈值和前端均保持不变。

机器可读契约为
[`two-stage-retrieval-contract-v1.json`](two-stage-retrieval-contract-v1.json)。后续实现若改变
字段、预算或幂等语义，必须先更新版本并重新审核，不能静默修改 v1。

## 2. 现有链路约束

当前同步问答接口为：

```text
POST /api/v1/knowledge-bases/{knowledge_base_id}/ask
```

每次调用会创建一个 `chat_session`，持久化一条 user message 和一条 assistant message，并
返回 `session_id`、assistant `message_id`、回答、引用和候选。assistant message 的
`retrieval_diagnostics` 已能保存候选分数和生成状态。

二阶段请求不能让客户端重新提交 question，否则“扩展同一次检索”会退化成一个可篡改的
新请求；也不能让客户端扩大 candidate_k、启用模型常识或选择内部策略。

## 3. API 契约

### 3.1 请求

```http
POST /api/v1/knowledge-bases/{knowledge_base_id}/answers/{message_id}/expand-retrieval
Content-Type: application/json

{
  "idempotency_key": "6abcf359-cba3-4df0-b10f-4e0189bea809",
  "trigger": "user_requested_more_evidence"
}
```

服务端通过 `message_id` 加载：

- 原 assistant message、所属 session 和 knowledge base；
- session 内对应的原 user question；
- 首轮候选、引用、证据结论和 `allow_model_knowledge` 状态；
- 首轮 Top-6 的稳定顺序。

请求不接受 `question`、`top_k`、`candidate_k`、`allow_model_knowledge` 或检索策略。路径中的
knowledge base 必须与父消息所属 session 一致。

### 3.2 响应

```json
{
  "expansion_id": "...",
  "session_id": "...",
  "parent_message_id": "...",
  "message_id": "...",
  "answer": "...",
  "evidence_sufficient": true,
  "generation_mode": "llm",
  "model_name": "...",
  "fallback_reason": null,
  "citations": [
    {"chunk_id": "...", "retrieval_stage": "primary", "is_new": false},
    {"chunk_id": "...", "retrieval_stage": "supplemental", "is_new": true}
  ],
  "primary_candidates": [],
  "supplemental_candidates": [],
  "retrieval_trace": {}
}
```

二阶段答案作为新的 assistant message 写入同一 session，并通过 `parent_message_id` 指回首轮
答案。首轮消息和引用不覆盖，前端才能展示前后变化。

第一增量只设计同步 JSON 接口，不同时扩展 SSE，避免把幂等、恢复和事件重放问题混入首轮
实现。后续如增加流式，必须复用同一个 expansion 记录和状态机。

### 3.3 错误语义

- `404 PARENT_ANSWER_NOT_FOUND`：父消息不存在或不属于路径 knowledge base；
- `409 EXPANSION_ALREADY_EXISTS`：该父回答已由另一个 key 完成扩展；
- `409 EXPANSION_IN_PROGRESS`：另一请求已取得执行权；
- `422 PARENT_MESSAGE_NOT_ASSISTANT`：message 不是 assistant 回答；
- `422 PARENT_CONTEXT_UNAVAILABLE`：旧数据缺少恢复首轮上下文所需的 diagnostics。

错误响应继续使用现有统一 `trace_id` 契约。

## 4. 幂等和并发

实现阶段需要新增 `chat_retrieval_expansions` 持久化记录，而不是只写 JSONB：

```text
id
parent_message_id        UNIQUE
result_message_id        NULLABLE
idempotency_key
status                   started/completed/failed
request_snapshot
trace
created_at/updated_at
```

建议数据库唯一约束为 `UNIQUE(parent_message_id)`，因为 v1 每个首轮回答只允许一次完整扩展。
相同 key 重试返回已保存响应；不同 key 在已开始或完成后返回409。取得唯一约束成功的请求才
能调用第二阶段检索，避免双击产生两份上下文和回答。

失败记录保留 `failure_code`。是否允许人工重试应另行设计，v1 不自动删除失败记录或在同一
请求中无限重试。

## 5. 检索不变量

- 首轮 Top-6 的 chunk ID 和相对顺序100%保留；
- supplemental 只能追加，不能将首轮证据挤出 combined context；
- exact chunk ID 去重；不同 heading 的相邻块不能仅因 chunk_index 接近而删除；
- supplemental 策略身份固定为 `heading_supplemental_v1`，但本文不实现其算法；
- 不改变 RRF 权重、Embedding、Evidence Gate、production min score 或默认问答链路；
- 二阶段引用白名单是 primary 与实际消费 supplemental 的并集，LLM 仍不能引用候选集外
  chunk；
- 原请求若不允许模型常识，二阶段也不能提升权限。

当 supplemental 没有提供任何新 chunk 时，返回 `status=no_new_evidence`，可以复用首轮回答
或给出“没有找到更多资料”，但不能伪造一次改善。

## 6. 上下文预算

| 预算项 | v1 硬限制 |
| --- | ---: |
| Primary chunks | 固定最多6，全部保留 |
| Supplemental chunks | 最多7 |
| Combined chunks | 最多13 |
| Supplemental content | 最多7,000字符 / 估算4,000 tokens |
| Combined content | 最多18,000字符 / 估算10,000 tokens |
| 总 citations | 最多5 |
| Supplemental citations | 最多3 |

预算按完整 chunk 消费，不截断 chunk 内容；下一个 chunk 会导致任一预算超限时，在加入前
停止。这样引用 quote、原文和 prompt 使用的是同一证据，不会因静默截断产生难以解释的
provenance。

Token 仅作为可观测估算，硬执行同时使用 chunk 数和字符数，避免不同 tokenizer 版本改变
线上行为。实现必须记录实际模型 usage（若 provider 返回），但不能用它事后放宽预算。

## 7. Trace 契约

每次扩展必须生成独立 `trace_id` 与 `expansion_id`，并记录：

- 身份：session、父/结果 message、trigger、策略版本、question SHA-256；
- 候选：primary、supplemental candidate、实际消费、去重和预算拒绝 chunk ID；
- 预算：三类候选数量、字符数、估算 token、预算上限；
- 结果：combined context、最终 citation ID、扩展前后 evidence decision；
- 性能：retrieval、generation、total latency；
- 状态：completed、no_new_evidence 或 failed，以及 failure code。

trace 不重复持久化原问题正文，只保存 question hash；问题正文继续由 chat message 管理。日志
默认只记录计数、耗时、ID 和 hash，不记录 chunk content。

## 8. 验收边界

契约实现至少需要以下测试：

1. 首轮6个 chunk 在 combined context 中 ID 和顺序完全不变；
2. supplemental 最多7个，combined 最多13个；
3. 字符预算超限时不截断、不越界；
4. exact chunk 去重，重复点击只产生一个 expansion 和一个结果 message；
5. 路径 knowledge base 与 parent 不一致时拒绝；
6. 客户端无法改变原 question 或提升模型知识权限；
7. 所有 citation 均属于 combined context；
8. no-new-evidence、生成失败和并发冲突都有稳定 trace；
9. 旧 `POST /ask` 的请求与响应契约完全不变；
10. production feature flag 默认关闭。

这些契约测试通过后，才进入 service orchestration；Retriever 算法实验仍需独立 Development
消融，不能借 API 实现阶段顺手调参。
