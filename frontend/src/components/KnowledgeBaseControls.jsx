export function KnowledgeBaseSelector({
  bases,
  currentId,
  busy,
  onSelect,
  onCreate,
}) {
  return (
    <div className="knowledge-base-controls">
      <label>
        <span>当前知识库</span>
        <select
          value={currentId ?? ""}
          disabled={busy || bases.length === 0}
          onChange={(event) => onSelect(event.target.value)}
          aria-label="切换当前知识库"
        >
          {bases.length === 0 ? <option value="">尚未创建知识库</option> : null}
          {bases.map((base) => (
            <option value={base.id} key={base.id}>
              {base.name} · {base.documents_unavailable ? "状态待刷新" : `${base.document_count ?? 0} 份资料`}
            </option>
          ))}
        </select>
      </label>
      <button type="button" onClick={onCreate} disabled={busy}>
        新建知识库
      </button>
    </div>
  );
}

export function CreateKnowledgeBaseDialog({
  open,
  busy,
  name,
  description,
  onNameChange,
  onDescriptionChange,
  onCancel,
  onConfirm,
}) {
  if (!open) return null;
  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onCancel}>
      <section
        className="workspace-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-knowledge-base-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div>
          <p className="eyebrow">NEW WORKSPACE</p>
          <h2 id="create-knowledge-base-title">新建知识库</h2>
          <p>创建后会切换到新知识库，原有知识库及其资料不会被删除。</p>
        </div>
        <label>
          <span>知识库名称</span>
          <input
            autoFocus
            maxLength={160}
            value={name}
            disabled={busy}
            onChange={(event) => onNameChange(event.target.value)}
            placeholder="例如：LangGraph 学习知识库"
          />
        </label>
        <label>
          <span>描述（可选）</span>
          <textarea
            maxLength={4000}
            rows={4}
            value={description}
            disabled={busy}
            onChange={(event) => onDescriptionChange(event.target.value)}
            placeholder="记录该知识库的学习目标和资料范围"
          />
        </label>
        <div className="dialog-actions">
          <button className="secondary" type="button" onClick={onCancel} disabled={busy}>
            取消
          </button>
          <button type="button" onClick={onConfirm} disabled={busy || !name.trim()}>
            创建并切换
          </button>
        </div>
      </section>
    </div>
  );
}
