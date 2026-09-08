import { Metric } from "./common.jsx";
import { embeddingLabel, runtimeStartedLabel, runtimeVersionLabel } from "../utils/formatters.js";

const navigation = [
  ["overview", "总览", "⌂"],
  ["knowledge", "知识库", "▤"],
  ["rag", "RAG 问答", "✦"],
  ["interview", "模拟面试", "◉"],
  ["reports", "训练报告", "▥"],
  ["profile", "能力画像", "◎"],
  ["system", "系统状态", "◇"],
];

const pageMeta = {
  overview: ["学习工作台", "聚焦下一步训练，而不是一次展示所有功能。"],
  knowledge: ["知识库", "维护学习资料、查看索引状态并处理失败文档。"],
  rag: ["RAG 问答", "基于当前知识库提问，并检查回答引用与生成模式。"],
  interview: ["模拟面试", "围绕当前资料和能力薄弱项，完成一轮可恢复训练。"],
  reports: ["训练报告", "查看逐题解析、历史结果和多轮得分趋势。"],
  profile: ["能力画像", "了解已掌握、待加强和下一轮优先训练的知识点。"],
  system: ["系统状态", "检查 LLM、RAG、评分和完整演示闭环的运行状态。"],
};

export function AppLayout({
  activeView,
  onNavigate,
  runtime,
  knowledgeBase,
  interview,
  actions,
  children,
}) {
  const [title, description] = pageMeta[activeView];
  return (
    <div className="app-layout">
      <aside className="app-sidebar">
        <button className="brand" type="button" onClick={() => onNavigate("overview")}>
          <span>AM</span>
          <div>
            <strong>AgentMentor</strong>
            <small>LOCAL V2</small>
          </div>
        </button>
        <nav aria-label="工作台导航">
          {navigation.map(([key, label, icon]) => (
            <button
              className={activeView === key ? "active" : ""}
              type="button"
              key={key}
              onClick={() => onNavigate(key)}
            >
              <span>{icon}</span>
              {label}
            </button>
          ))}
        </nav>
        <div className="sidebar-runtime">
          <span className={runtime.llm_enabled ? "status-dot online" : "status-dot"} />
          <div>
            <strong>{runtime.llm_enabled ? "LLM 已连接" : "本地降级模式"}</strong>
            <small>{runtime.llm_model ?? "Deterministic baseline"}</small>
            <small>{embeddingLabel(runtime)}</small>
          </div>
        </div>
      </aside>

      <div className="app-main">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">AI AGENT INTERVIEW COACH</p>
            <h1>{title}</h1>
            <p>{description}</p>
          </div>
          <div className="workspace-context">
            <div>
              <span>当前知识库</span>
              <strong>{knowledgeBase?.name ?? "尚未创建"}</strong>
            </div>
            {interview ? (
              <div>
                <span>当前面试</span>
                <strong>{interview.status}</strong>
              </div>
            ) : null}
          </div>
        </header>
        <div className="workspace-actions">{actions}</div>
        <section className="workspace-content">{children}</section>
      </div>
    </div>
  );
}

export function OverviewDashboard({
  runtime,
  documents,
  interview,
  completion,
  readiness,
  profile,
  reportHistory,
  onNavigate,
  onSelectFocus,
  onOpenReport,
}) {
  const focus = profile.focuses[0] ?? profile.plan[0] ?? null;
  const readyCount = documents.filter((item) => item.status === "ready").length;
  const passedChecks = readiness?.checks.filter((item) => item.passed).length ?? 0;
  const totalChecks = readiness?.checks.length ?? 0;
  const demoSteps = [
    {
      key: "knowledge",
      title: "1. 准备知识库",
      detail: readyCount
        ? `当前已有 ${readyCount} 份可检索资料，可以直接演示 RAG 和面试。`
        : "先上传一份学习资料，等待索引 ready 后再开始演示。",
      action: "查看知识库",
      view: "knowledge",
      ready: readyCount > 0,
    },
    {
      key: "interview",
      title: "2. 跑一轮面试",
      detail: interview
        ? `当前面试进度 ${completion}%，可继续答题或生成报告。`
        : "基于画像、覆盖盲区和历史题冷却生成三题面试。",
      action: "进入面试",
      view: "interview",
      ready: Boolean(interview),
    },
    {
      key: "reports",
      title: "3. 讲报告画像",
      detail: reportHistory.length
        ? `已有 ${reportHistory.length} 份历史报告，可展示趋势、画像和复习任务。`
        : "完成面试后生成评分报告，再观察画像如何反哺下一轮训练。",
      action: "查看报告",
      view: "reports",
      ready: reportHistory.length > 0,
    },
  ];
  const trustSignals = readiness?.signals ?? [
    {
      key: "rag_trust",
      label: "RAG 可信边界",
      detail: "证据门禁、引用白名单和显式降级会在系统就绪后展示。",
    },
    {
      key: "workflow_control",
      label: "工作流控制",
      detail: "状态机、checkpoint 和幂等提交会在完成面试后形成证据。",
    },
  ];
  const enterpriseBoundaries = readiness?.enterprise_boundaries ?? [
    "当前定位为本地单用户学习训练系统，不包装成企业级多租户平台。",
  ];
  return (
    <div className="overview-dashboard">
      <section className="welcome-card">
        <div>
          <p className="eyebrow">YOUR NEXT BEST ACTION</p>
          <h2>{focus ? `继续加强：${focus.knowledge_point}` : "从一份学习资料开始训练"}</h2>
          <p>
            {focus?.reason ??
              "上传 Markdown、PDF 或 DOCX，系统会把资料变成可追溯的问答与面试训练。"}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            if (focus) onSelectFocus(focus);
            onNavigate(focus ? "interview" : "knowledge");
          }}
        >
          {focus ? "开始专项训练" : "维护知识库"}
        </button>
      </section>

      <section className="overview-metrics">
        <Metric label="模型模式" value={runtime.llm_enabled ? "真实 LLM" : "本地降级"} />
        <Metric label="API 版本" value={runtimeVersionLabel(runtime)} />
        <Metric label="Embedding" value={embeddingLabel(runtime)} />
        <Metric label="可检索资料" value={`${readyCount} 份`} />
        <Metric label="当前面试" value={interview ? `${completion}%` : "未开始"} />
        <Metric label="演示就绪" value={`${passedChecks}/${totalChecks}`} />
        <Metric label="启动时间" value={runtimeStartedLabel(runtime)} />
      </section>

      <section className="demo-mode-card">
        <div className="section-heading">
          <div>
            <span>INTERVIEW DEMO MODE</span>
            <h3>按这条路线演示，面试官更容易理解项目价值</h3>
          </div>
          <strong>{readiness ? `${readiness.score}% 就绪` : "待自检"}</strong>
        </div>
        <div className="demo-mode-grid">
          {demoSteps.map((step) => (
            <article className={step.ready ? "ready" : ""} key={step.key}>
              <span>{step.ready ? "已具备" : "待完成"}</span>
              <h4>{step.title}</h4>
              <p>{step.detail}</p>
              <button type="button" className="text-button" onClick={() => onNavigate(step.view)}>
                {step.action} →
              </button>
            </article>
          ))}
        </div>
        <div className="demo-evidence-grid">
          <div>
            <h4>工程可信性证据</h4>
            <ul>
              {trustSignals.slice(0, 4).map((signal) => (
                <li key={signal.key}>
                  <strong>{signal.label}</strong>
                  <span>{signal.detail}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4>企业级边界口径</h4>
            <ul>
              {enterpriseBoundaries.slice(0, 3).map((boundary) => (
                <li key={boundary}>
                  <span>{boundary}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <div className="overview-columns">
        <section className="overview-card">
          <div className="section-heading">
            <div>
              <span>能力摘要</span>
              <h3>优先处理最薄弱的知识点</h3>
            </div>
            <button className="text-button" type="button" onClick={() => onNavigate("profile")}>
              查看画像 →
            </button>
          </div>
          <div className="focus-summary-list">
            {(profile.focuses.length ? profile.focuses : profile.plan).slice(0, 3).map((item) => (
              <button
                type="button"
                key={`${item.knowledge_point}-${item.source_type ?? "plan"}`}
                onClick={() => {
                  onSelectFocus(item);
                  onNavigate("interview");
                }}
              >
                <span>{item.knowledge_point}</span>
                <small>{item.reason}</small>
                <strong>{item.mastery_score == null ? "待训练" : `${Math.round(item.mastery_score * 100)}%`}</strong>
              </button>
            ))}
            {!profile.focuses.length && !profile.plan.length ? (
              <p className="overview-empty">完成一次面试后，这里会生成个性化训练重点。</p>
            ) : null}
          </div>
        </section>

        <section className="overview-card">
          <div className="section-heading">
            <div>
              <span>最近训练</span>
              <h3>用历史结果观察长期变化</h3>
            </div>
            <button className="text-button" type="button" onClick={() => onNavigate("reports")}>
              全部报告 →
            </button>
          </div>
          <div className="recent-report-list">
            {reportHistory.slice(0, 4).map((item) => (
              <button type="button" key={item.id} onClick={() => onOpenReport(item)}>
                <div>
                  <strong>{item.topic}</strong>
                  <small>{item.created_at.slice(0, 10)} · {item.difficulty}</small>
                </div>
                <span>{item.total_score}/{item.max_score}</span>
              </button>
            ))}
            {!reportHistory.length ? (
              <p className="overview-empty">暂无历史报告，完成一轮面试后会自动沉淀。</p>
            ) : null}
          </div>
        </section>
      </div>
    </div>
  );
}
