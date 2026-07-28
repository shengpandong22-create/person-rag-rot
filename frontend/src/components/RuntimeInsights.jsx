export function RuntimeInsights({ runtime, askResult, report }) {
  const llmMode = runtime?.llm_enabled
    ? `真实 LLM：${runtime.llm_model ?? "已配置"}`
    : "本地确定性降级";
  const evidenceLabel =
    askResult == null ? "尚未执行 RAG" : askResult.evidence_sufficient ? "证据充足" : "证据不足";
  const reportLabel =
    report == null
      ? "尚未生成评分"
      : report.low_confidence_items?.length
        ? `低置信 ${report.low_confidence_items.length} 项`
        : "评分置信正常";

  return (
    <section className="runtime-insights" aria-label="系统运行态观测">
      <div>
        <span>LLM 状态</span>
        <strong>{llmMode}</strong>
      </div>
      <div>
        <span>最近 RAG</span>
        <strong>{evidenceLabel}</strong>
      </div>
      <div>
        <span>最近评分</span>
        <strong>{reportLabel}</strong>
      </div>
    </section>
  );
}
