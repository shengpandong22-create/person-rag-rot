import {
  embeddingLabel,
  runtimeStartedLabel,
  runtimeVersionLabel,
} from "../utils/formatters.js";

export function RuntimeInsights({ runtime, askResult, report, readiness }) {
  const llmMode = runtime?.llm_enabled
    ? `真实 LLM：${runtime.llm_model ?? "已配置"}`
    : "本地确定性降级";
  const embeddingMode = embeddingLabel(runtime);
  const apiVersion = runtimeVersionLabel(runtime);
  const startedAt = runtimeStartedLabel(runtime);
  const evidenceLabel =
    askResult == null
      ? "尚未执行 RAG"
      : `${askResult.evidence_sufficient ? "证据充足" : "证据不足"} · ${
          askResult.generation_mode === "llm" ? "LLM" : "已降级"
        }`;
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
        <span>Embedding</span>
        <strong>{embeddingMode}</strong>
        <small>{runtime?.embedding_model ?? "模型未返回"}</small>
      </div>
      <div>
        <span>API 运行态</span>
        <strong>{apiVersion}</strong>
        <small>启动：{startedAt}</small>
      </div>
      <div>
        <span>最近 RAG</span>
        <strong>{evidenceLabel}</strong>
      </div>
      <div>
        <span>最近评分</span>
        <strong>{reportLabel}</strong>
      </div>
      <div>
        <span>演示就绪度</span>
        <strong>
          {readiness
            ? `${readiness.checks.filter((item) => item.passed).length}/${readiness.checks.length} · ${
                { ready: "可完整演示", partial: "部分就绪", not_ready: "尚未就绪" }[
                  readiness.status
                ] ?? readiness.status
              }`
            : "待自检"}
        </strong>
        {readiness ? <small>{readiness.next_action}</small> : null}
      </div>
    </section>
  );
}
