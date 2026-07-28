function scoreLabel(value) {
  if (value == null) return "暂无画像分";
  return `画像分 ${Math.round(value * 100)} / 100`;
}

function sourceLabel(sourceType) {
  if (sourceType === "review_task") return "来自复习任务";
  if (sourceType === "ability") return "来自能力画像";
  return "来自训练计划";
}

export function TrainingFocusPanel({ focuses, disabled, onSelect }) {
  const items = focuses ?? [];
  return (
    <section className="training-focus-panel" aria-label="画像驱动专项训练">
      <div className="section-heading">
        <span>画像驱动专项训练</span>
        <small>优先使用复习任务和低掌握度知识点生成下一轮面试主题</small>
      </div>
      {items.length > 0 ? (
        <div className="focus-grid">
          {items.slice(0, 3).map((item) => (
            <button
              className="focus-card"
              key={`${item.source_type}-${item.knowledge_point}`}
              type="button"
              disabled={disabled}
              onClick={() => onSelect(item)}
            >
              <strong>{item.knowledge_point}</strong>
              <span>{sourceLabel(item.source_type)} · P{item.priority}</span>
              <span>{scoreLabel(item.mastery_score)}</span>
              <small>{item.reason}</small>
            </button>
          ))}
        </div>
      ) : (
        <p className="hint">
          还没有足够画像数据。完成一轮面试评分后，这里会推荐可直接发起专项训练的薄弱点。
        </p>
      )}
    </section>
  );
}
