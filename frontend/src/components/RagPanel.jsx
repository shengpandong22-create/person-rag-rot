import { Empty, ResultBox, StepCard } from "./common.jsx";

export function RagPanel({
  askQuestion,
  askResult,
  canUseKnowledgeBase,
  busy,
  onQuestionChange,
  onAsk,
}) {
  return (
    <StepCard number="02" title="RAG 问答与引用溯源" tone="purple">
      <p>你可以自己输入问题；启用 DeepSeek 后会由真实 LLM 基于检索证据组织回答。</p>
      <textarea
        value={askQuestion}
        onChange={(event) => onQuestionChange(event.target.value)}
        placeholder="输入你想问知识库的问题..."
        rows={4}
      />
      <button onClick={onAsk} disabled={!canUseKnowledgeBase || busy || !askQuestion.trim()}>
        提交 RAG 问题
      </button>
      {askResult ? (
        <ResultBox
          title={askResult.evidence_sufficient ? "证据充分" : "证据不足"}
          subtitle={`引用数量：${askResult.citations.length}`}
        >
          <p>{askResult.answer}</p>
          {askResult.citations.length > 0 ? (
            <div className="citation-list" aria-label="引用证据列表">
              {askResult.citations.slice(0, 4).map((citation) => (
                <article className="citation-card" key={citation.chunk_id}>
                  <strong>{citation.document_title}</strong>
                  <div className="tag-row">
                    <span>{citation.block_type || "paragraph"}</span>
                    <span>chunk {citation.chunk_index}</span>
                    {citation.page_number ? <span>第 {citation.page_number} 页</span> : null}
                  </div>
                  {citation.heading_path?.length ? (
                    <small>{citation.heading_path.join(" / ")}</small>
                  ) : null}
                  <code>{citation.retrieval_explanation || `score=${citation.score}`}</code>
                </article>
              ))}
            </div>
          ) : null}
        </ResultBox>
      ) : (
        <Empty text="先选择或创建知识库，再执行一次 RAG 问答" />
      )}
    </StepCard>
  );
}
