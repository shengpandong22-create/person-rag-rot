import { Empty, Info, StepCard } from "./common.jsx";

export function KnowledgePanel({
  knowledgeBase,
  documents,
  busy,
  onUpload,
  onReindex,
  onOpenSelector,
}) {
  return (
    <StepCard number="01" title="知识库与资料入库" tone="blue">
      <p>资料按知识库独立维护；你可以随时切换知识库，原有资料不会丢失。</p>
      <Info label="当前知识库" value={knowledgeBase?.name ?? "尚未创建"} />
      <label className={`upload ${!knowledgeBase || busy ? "disabled" : ""}`}>
        上传学习资料
        <input type="file" onChange={onUpload} disabled={!knowledgeBase || busy} />
      </label>
      {documents.length ? (
        <div className="mini-list">
          {documents.map((item) => (
            <div className="document-row" key={item.id}>
              <span>{item.original_filename} · {item.status}</span>
              {item.status === "failed" ? (
                <button
                  className="secondary compact"
                  type="button"
                  disabled={busy}
                  onClick={() => onReindex(item.id)}
                >
                  重新索引
                </button>
              ) : null}
              {item.error_message ? <small>{item.error_message}</small> : null}
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-workspace">
          <Empty text="当前知识库暂时没有资料。你可以上传资料，或者切换回已有知识库。" />
          <button className="secondary compact" type="button" onClick={onOpenSelector}>
            切换知识库
          </button>
        </div>
      )}
    </StepCard>
  );
}
