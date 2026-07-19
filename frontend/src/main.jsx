import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const terminalDocumentStatuses = new Set(["ready", "failed", "archived"]);

const dimensionLabels = {
  correctness: "准确性",
  completeness: "完整性",
  reasoning: "推理链路",
  communication: "表达结构",
};

const errorLabels = {
  concept_confusion: "概念混淆",
  missing_key_point: "关键点遗漏",
  hallucination: "不可靠结论",
  no_answer: "回答不足",
};

const statusLabels = {
  open: "待完成",
  completed: "已完成",
};

function runtimeLabel(runtime) {
  return runtime.llm_enabled ? `真实 LLM 已启用：${runtime.llm_model}` : "本地基线模式";
}

function percent(value) {
  return `${Math.round((value ?? 0) * 100)}%`;
}

function profileScore(value) {
  return `${Math.round((value ?? 0) * 100)} / 100`;
}

function unique(items) {
  return [...new Set(items.filter(Boolean))];
}

function apiErrorMessage(responseStatus, data) {
  return data?.message ?? `请求失败：${responseStatus}`;
}

function inferInterviewTopic(documents, profile) {
  const readyDocuments = documents.filter((item) => item.status === "ready");
  const fileTopic = readyDocuments
    .map((item) => item.original_filename ?? "")
    .map((name) =>
      name
        .replace(/\.[^.]+$/, "")
        .replace(/[_-]+/g, " ")
        .replace(/学习|总结|资料|文档|笔记/gi, "")
        .trim(),
    )
    .find((name) => name.length >= 2);
  if (fileTopic) return fileTopic.slice(0, 60);

  const recommended = profile.plan?.[0]?.knowledge_point;
  if (recommended) return recommended;

  const weakAbility = [...(profile.abilities ?? [])].sort(
    (a, b) => a.mastery_score - b.mastery_score,
  )[0]?.knowledge_point;
  return weakAbility || "AI Agent";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers ?? {}),
    },
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(apiErrorMessage(response.status, data));
  }
  return data;
}

function App() {
  const [status, setStatus] = useState("正在连接本地服务...");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [runtime, setRuntime] = useState({ llm_enabled: false, llm_model: null });
  const [knowledgeBase, setKnowledgeBase] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [askQuestion, setAskQuestion] = useState("RAG 为什么能提升 AI 面试助手回答的可信度？");
  const [askResult, setAskResult] = useState(null);
  const [interviewTopic, setInterviewTopic] = useState("AI Agent");
  const [topicEdited, setTopicEdited] = useState(false);
  const [interview, setInterview] = useState(null);
  const [answerDraft, setAnswerDraft] = useState("");
  const [report, setReport] = useState(null);
  const [profile, setProfile] = useState({
    abilities: [],
    errors: [],
    tasks: [],
    plan: [],
  });

  const currentQuestion = interview?.current_question;
  const completion = useMemo(() => {
    if (!interview) return 0;
    return Math.round((interview.current_question_index / interview.question_count) * 100);
  }, [interview]);
  const isCompleted = interview?.status === "completed";
  const canUseKnowledgeBase = Boolean(knowledgeBase?.id);
  const currentDefaultAnswer = currentQuestion?.reference_answer?.trim() ?? "";

  useEffect(() => {
    bootstrap();
  }, []);

  useEffect(() => {
    const suggested = inferInterviewTopic(documents, profile);
    if (!topicEdited) {
      setInterviewTopic(suggested);
    }
  }, [documents, profile, topicEdited]);

  async function bootstrap() {
    setBusy(true);
    setError("");
    try {
      await api("/health/ready");
      const [runtimeInfo, bases, abilities, errors, tasks, plan] = await Promise.all([
        api("/health/runtime"),
        api("/api/v1/knowledge-bases"),
        api("/api/v1/profiles/me/abilities"),
        api("/api/v1/profiles/me/error-patterns"),
        api("/api/v1/review-tasks"),
        api("/api/v1/profiles/me/interview-plan"),
      ]);
      setRuntime(runtimeInfo);
      setProfile({ abilities, errors, tasks, plan });
      const restored = await restoreKnowledgeWorkspace(bases);
      if (restored.base) {
        setKnowledgeBase(restored.base);
        setDocuments(restored.documents);
        const suffix = restored.documents.length ? `，资料 ${restored.documents.length} 份` : "";
        setStatus(`${runtimeLabel(runtimeInfo)}，已恢复知识库：${restored.base.name}${suffix}`);
      } else {
        setStatus(`${runtimeLabel(runtimeInfo)}，请创建你的第一个知识库`);
      }
    } catch (err) {
      setStatus("本地服务未就绪");
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function restoreKnowledgeWorkspace(bases) {
    let fallback = { base: bases[0] ?? null, documents: [] };
    for (const base of bases) {
      const persistedDocuments = await api(`/api/v1/knowledge-bases/${base.id}/documents`);
      if (base === bases[0]) {
        fallback = { base, documents: persistedDocuments };
      }
      if (persistedDocuments.length > 0) {
        return { base, documents: persistedDocuments };
      }
    }
    return fallback;
  }

  function replaceDocument(nextDocument) {
    setDocuments((items) =>
      items.map((item) => (item.id === nextDocument.id ? nextDocument : item)),
    );
  }

  async function pollDocumentStatus(documentId) {
    for (let attempt = 0; attempt < 30; attempt += 1) {
      await new Promise((resolve) => {
        window.setTimeout(resolve, 1000);
      });
      const latest = await api(`/api/v1/documents/${documentId}`);
      replaceDocument(latest);
      if (terminalDocumentStatuses.has(latest.status)) {
        setStatus(latest.status === "ready" ? "资料索引完成：ready" : "资料处理结束");
        return latest;
      }
    }
    setStatus("资料仍在处理中，可稍后刷新状态查看");
    return null;
  }

  async function run(label, action) {
    setBusy(true);
    setError("");
    setStatus(label);
    try {
      await action();
      setStatus(`${label}：完成`);
    } catch (err) {
      setError(err.message);
      setStatus(`${label}：失败`);
    } finally {
      setBusy(false);
    }
  }

  const createKnowledgeBase = () =>
    run("创建知识库", async () => {
      const kb = await api("/api/v1/knowledge-bases", {
        method: "POST",
        body: JSON.stringify({
          name: "AgentMentor 学习知识库",
          description: "用于沉淀学习资料、RAG 问答、模拟面试和能力画像的个人知识库。",
        }),
      });
      setKnowledgeBase(kb);
      setDocuments([]);
      setAskResult(null);
      setInterview(null);
      setReport(null);
      setTopicEdited(false);
    });

  const refreshWorkspace = () =>
    run("刷新工作台状态", async () => {
      await bootstrap();
    });

  const uploadDocument = (event) =>
    run("上传并索引资料", async () => {
      const file = event.target.files?.[0];
      if (!file || !knowledgeBase) return;
      const form = new FormData();
      form.append("file", file);
      form.append("trust_level", "curated");
      const document = await api(`/api/v1/knowledge-bases/${knowledgeBase.id}/documents`, {
        method: "POST",
        body: form,
      });
      setDocuments((items) => [document, ...items.filter((item) => item.id !== document.id)]);
      await pollDocumentStatus(document.id);
      event.target.value = "";
    });

  const ask = () =>
    run("执行带引用 RAG 问答", async () => {
      const result = await api(`/api/v1/knowledge-bases/${knowledgeBase.id}/ask`, {
        method: "POST",
        body: JSON.stringify({
          question: askQuestion,
          allow_model_knowledge: true,
        }),
      });
      setAskResult(result);
    });

  const startInterview = () =>
    run("创建并启动三题面试", async () => {
      const created = await api("/api/v1/interviews", {
        method: "POST",
        body: JSON.stringify({
          knowledge_base_id: knowledgeBase.id,
          topic: interviewTopic.trim() || inferInterviewTopic(documents, profile),
          difficulty: "medium",
          question_count: 3,
        }),
      });
      const started = await api(`/api/v1/interviews/${created.id}/start`, { method: "POST" });
      setInterview(started);
      setAnswerDraft("");
      setReport(null);
    });

  const submitAnswer = () =>
    run("提交答案并推进工作流", async () => {
      const finalAnswer =
        answerDraft.trim() ||
        currentDefaultAnswer ||
        "我暂时无法完整回答这道题，需要结合参考资料继续学习。";
      const updated = await api(`/api/v1/interviews/${interview.id}/answers`, {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({
          question_id: currentQuestion.id,
          answer: finalAnswer,
        }),
      });
      setInterview(updated);
      setAnswerDraft("");
    });

  const evaluateAndReport = () =>
    run("生成评分报告与画像闭环", async () => {
      await api(`/api/v1/interviews/${interview.id}/evaluations`, {
        method: "POST",
        body: JSON.stringify({ reviewer_available: true }),
      });
      const builtReport = await api(`/api/v1/interviews/${interview.id}/report`, {
        method: "POST",
        body: JSON.stringify({ reviewer_available: true }),
      });
      await api(`/api/v1/interviews/${interview.id}/profile-updates`, { method: "POST" });
      const [abilities, errors, tasks, plan] = await Promise.all([
        api("/api/v1/profiles/me/abilities"),
        api("/api/v1/profiles/me/error-patterns"),
        api("/api/v1/review-tasks"),
        api("/api/v1/profiles/me/interview-plan"),
      ]);
      setReport(builtReport);
      setProfile({ abilities, errors, tasks, plan });
    });

  return (
    <main className="shell">
      <section className="hero">
        <div className="hero-copy">
          <div className="pill">AI Agent Interview Coach · Local V1</div>
          <h1>把学习资料变成可追溯的 AI 面试训练。</h1>
          <p>
            AgentMentor 聚合 RAG、可恢复工作流、可信评分和能力画像，帮助 Java
            后端开发者向 AI Agent 开发转型。
          </p>
          <div className="hero-actions">
            <button onClick={createKnowledgeBase} disabled={busy}>
              创建新知识库
            </button>
            <button className="secondary" onClick={refreshWorkspace} disabled={busy}>
              刷新已有状态
            </button>
            <a href="/api/v1/docs" target="_blank" rel="noreferrer">
              OpenAPI 文档
            </a>
          </div>
          <p className="model-note">
            当前运行模式：
            {runtime.llm_enabled
              ? `真实 LLM 已启用（${runtime.llm_model}）`
              : "本地确定性基线，未启用真实 LLM"}
            。RAG、面试出题和评分支持无 Key 自动降级。
          </p>
        </div>
        <StatusPanel status={status} error={error} busy={busy} runtime={runtime} />
      </section>

      <section className="metrics">
        <Metric label="模型模式" value={runtime.llm_enabled ? "LLM" : "Local"} />
        <Metric label="知识库" value={knowledgeBase ? "Ready" : "Pending"} />
        <Metric label="已入库资料" value={documents.length} />
        <Metric label="面试进度" value={interview ? `${completion}%` : "0%"} />
      </section>

      <section className="workflow">
        <StepCard number="01" title="知识库与资料入库" tone="blue">
          <p>刷新页面会自动恢复最近一个有资料的知识库、资料列表和本机用户画像。</p>
          <Info label="Knowledge Base" value={knowledgeBase?.id ?? "尚未创建"} />
          <label className={`upload ${!knowledgeBase || busy ? "disabled" : ""}`}>
            上传学习资料
            <input type="file" onChange={uploadDocument} disabled={!knowledgeBase || busy} />
          </label>
          <MiniList
            items={documents.map((item) => `${item.original_filename} · ${item.status}`)}
            empty="暂无上传资料"
          />
        </StepCard>

        <StepCard number="02" title="RAG 问答与引用溯源" tone="purple">
          <p>你可以自己输入问题；启用 DeepSeek 后会由真实 LLM 基于检索证据组织回答。</p>
          <textarea
            value={askQuestion}
            onChange={(event) => setAskQuestion(event.target.value)}
            placeholder="输入你想问知识库的问题..."
            rows={4}
          />
          <button onClick={ask} disabled={!canUseKnowledgeBase || busy || !askQuestion.trim()}>
            提交 RAG 问题
          </button>
          {askResult ? (
            <ResultBox
              title={askResult.evidence_sufficient ? "证据充分" : "证据不足"}
              subtitle={`引用数量：${askResult.citations.length}`}
            >
              {askResult.answer}
            </ResultBox>
          ) : (
            <Empty text="先选择或创建知识库，再执行一次 RAG 问答" />
          )}
        </StepCard>

        <StepCard number="03" title="可恢复模拟面试" tone="green">
          <p>三题面试会保存 checkpoint；主题默认根据已入库资料和画像推荐生成，也可以手动指定。</p>
          <label className="field-label" htmlFor="interview-topic">
            本轮面试主题
          </label>
          <input
            id="interview-topic"
            className="text-input"
            value={interviewTopic}
            onChange={(event) => {
              setInterviewTopic(event.target.value);
              setTopicEdited(true);
            }}
            placeholder="例如：LangGraph、Checkpoint、Human-in-the-loop"
          />
          <p className="hint">
            当前推荐来源：
            {documents.some((item) => item.status === "ready")
              ? "已入库资料"
              : profile.plan.length > 0
                ? "用户画像与复习计划"
                : "默认 AI Agent 主题"}
          </p>
          <button
            onClick={startInterview}
            disabled={!canUseKnowledgeBase || busy || !interviewTopic.trim()}
          >
            启动三题面试
          </button>
          {interview && (
            <div className="interview-box">
              <Progress value={completion} />
              <Info label="Workflow Status" value={interview.status} />
              {currentQuestion ? (
                <ResultBox title={`第 ${currentQuestion.sequence} 题`} subtitle="当前等待回答">
                  <strong>{currentQuestion.question_text}</strong>
                  <textarea
                    value={answerDraft}
                    onChange={(event) => setAnswerDraft(event.target.value)}
                    placeholder="在这里输入你的真实回答；如果留空提交，会使用本题随题生成的参考答案。"
                    rows={7}
                  />
                  {currentDefaultAnswer && (
                    <p className="hint">
                      本题已生成参考答案，可用于演示评分闭环；真实训练时建议先自己回答。
                    </p>
                  )}
                  <div className="inline-actions">
                    <button
                      className="secondary"
                      type="button"
                      onClick={() => setAnswerDraft(currentDefaultAnswer)}
                      disabled={busy || !currentDefaultAnswer}
                    >
                      使用本题参考答案
                    </button>
                    <button
                      onClick={submitAnswer}
                      disabled={busy || (!answerDraft.trim() && !currentDefaultAnswer)}
                    >
                      {answerDraft.trim() ? "提交我的答案" : "使用默认答案提交"}
                    </button>
                  </div>
                </ResultBox>
              ) : (
                <button onClick={evaluateAndReport} disabled={busy || !isCompleted}>
                  生成评分报告和画像
                </button>
              )}
            </div>
          )}
        </StepCard>

        <InterviewReportCard report={report} />
        <ProfileCard profile={profile} />
        <NextPlanCard profile={profile} />
      </section>
    </main>
  );
}

function buildReportView(report) {
  if (!report) return null;
  const scoreRatio = report.max_score ? report.total_score / report.max_score : 0;
  const evaluations = report.evaluations ?? [];
  const weakDimensions = Object.entries(report.dimension_summary ?? {})
    .map(([key, value]) => ({
      key,
      label: dimensionLabels[key] ?? key,
      average: Number(value?.average ?? 0),
    }))
    .filter((item) => item.average < 3)
    .sort((a, b) => a.average - b.average);
  const missingPoints = unique(evaluations.flatMap((item) => item.missing_points ?? [])).slice(
    0,
    4,
  );
  const feedback = unique(evaluations.map((item) => item.feedback)).slice(0, 3);
  const lowConfidenceCount = report.low_confidence_items?.length ?? 0;
  const verdict =
    scoreRatio >= 0.8
      ? "整体表现较稳定，可以开始增加场景化追问。"
      : scoreRatio >= 0.55
        ? "已经能覆盖部分要点，但工程细节和表达结构还需要补强。"
        : "当前回答更像概念性描述，需要补充引用依据、工程边界和可验证细节。";
  const issueSummary =
    missingPoints.length > 0
      ? `主要缺口集中在：${missingPoints.join("、")}。`
      : weakDimensions.length > 0
        ? `低分维度集中在：${weakDimensions.map((item) => item.label).join("、")}。`
        : "本轮没有明显缺失点，建议提高回答的案例密度。";
  const action =
    weakDimensions.length > 0
      ? `下一轮优先按「定义 → 流程 → 风险 → 工程方案」重答，并重点提升 ${weakDimensions[0].label}。`
      : "下一轮可以尝试加入更具体的系统设计、指标和异常处理说明。";

  return {
    verdict,
    issueSummary,
    action,
    feedback,
    questionAnalyses: evaluations.map(buildQuestionAnalysis),
    tags: [
      `总分 ${report.total_score}/${report.max_score}`,
      lowConfidenceCount ? `低置信 ${lowConfidenceCount} 项` : "置信度正常",
      report.disputed_items?.length ? `争议 ${report.disputed_items.length} 项` : "无争议项",
    ],
  };
}

function buildQuestionAnalysis(evaluation, index) {
  const weakDimensions = [
    ["correctness", evaluation.correctness],
    ["completeness", evaluation.completeness],
    ["reasoning", evaluation.reasoning],
    ["communication", evaluation.communication],
  ]
    .filter(([, score]) => score < 3)
    .map(([key]) => dimensionLabels[key] ?? key);
  const missing = evaluation.missing_points ?? [];
  const incorrect = evaluation.incorrect_claims ?? [];
  const covered = evaluation.covered_points ?? [];
  const reason =
    missing.length > 0
      ? `主要扣分来自遗漏：${missing.slice(0, 3).join("、")}。`
      : weakDimensions.length > 0
        ? `主要扣分维度：${weakDimensions.join("、")}。`
        : "本题基础要点覆盖较好，扣分主要来自表达完整度或工程细节不足。";
  const suggestion =
    missing.length > 0
      ? "建议按“概念定义 → 核心流程 → 工程边界 → 示例/指标”重新组织答案。"
      : "建议进一步补充项目落地细节、异常处理和可观测指标。";

  return {
    id: evaluation.id,
    sequence: evaluation.sequence ?? index + 1,
    question: evaluation.question_text ?? `第 ${index + 1} 题`,
    answer: evaluation.user_answer ?? "",
    total: evaluation.total,
    confidence: evaluation.confidence,
    knowledgePoints: evaluation.knowledge_points ?? [],
    covered,
    missing,
    incorrect,
    reason,
    suggestion,
    feedback: evaluation.feedback,
    dimensionTags: [
      `准确 ${evaluation.correctness}/5`,
      `完整 ${evaluation.completeness}/5`,
      `推理 ${evaluation.reasoning}/5`,
      `表达 ${evaluation.communication}/5`,
    ],
  };
}

function buildProfileView(profile) {
  const abilities = [...profile.abilities].sort((a, b) => b.mastery_score - a.mastery_score);
  const strengths = abilities.filter((item) => item.mastery_score >= 0.6).slice(0, 3);
  const weaknesses = abilities.filter((item) => item.mastery_score < 0.6).slice(0, 3);
  const errors = [...profile.errors]
    .sort((a, b) => b.occurrence_count - a.occurrence_count)
    .slice(0, 3);

  return {
    strengths,
    weaknesses,
    errors,
    summary:
      abilities.length === 0
        ? "完成一次面试报告后，这里会沉淀你的本机用户画像。"
        : `已沉淀 ${abilities.length} 个知识点画像，${weaknesses.length} 个需要优先补强。`,
  };
}

function buildPlanView(profile) {
  const openTasks = profile.tasks
    .filter((item) => item.status !== "completed")
    .sort((a, b) => b.priority - a.priority)
    .slice(0, 3);
  const recommendations = [...profile.plan].sort((a, b) => b.priority - a.priority).slice(0, 3);
  const completedCount = profile.tasks.filter((item) => item.status === "completed").length;

  return {
    openTasks,
    recommendations,
    completedCount,
    summary:
      openTasks.length > 0
        ? `当前有 ${openTasks.length} 个待完成复习任务，建议先处理高优先级项。`
        : recommendations.length > 0
          ? "暂无到期复习任务，可根据下一轮推荐继续训练。"
          : "完成评分和画像更新后，这里会生成下一轮训练计划。",
  };
}

function InterviewReportCard({ report }) {
  const view = buildReportView(report);
  return (
    <StepCard number="04" title="本轮面试报告" tone="orange">
      <p>把模型评分转译成可执行反馈，不再直接堆叠重复的维度模板。</p>
      {view ? (
        <div className="score-card">
          <div>
            <span>{report.total_score}</span>
            <small>/ {report.max_score}</small>
          </div>
          <TagRow tags={view.tags} />
          <FeedbackItem title="总体结论">{view.verdict}</FeedbackItem>
          <FeedbackItem title="主要问题">{view.issueSummary}</FeedbackItem>
          <FeedbackItem title="下一步怎么练">{view.action}</FeedbackItem>
          {view.feedback.length > 0 && (
            <FeedbackItem title="模型反馈摘录">{view.feedback.join("；")}</FeedbackItem>
          )}
          {view.questionAnalyses.length > 0 && (
            <FeedbackGroup title="每题评分解析">
              {view.questionAnalyses.map((item) => (
                <QuestionAnalysisItem key={item.id} item={item} />
              ))}
            </FeedbackGroup>
          )}
        </div>
      ) : (
        <Empty text="完成三题面试后生成报告；这里会展示总结、问题和下一步建议。" />
      )}
    </StepCard>
  );
}

function QuestionAnalysisItem({ item }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <article className="analysis-item">
      <button
        className="analysis-summary"
        type="button"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
      >
        <span>
          第 {item.sequence} 题 · {item.total}/20
        </span>
        <small>{expanded ? "收起解析" : "展开解析"}</small>
      </button>
      <strong className="analysis-question">{item.question}</strong>
      <TagRow
        tags={[
          `置信度 ${percent(item.confidence)}`,
          ...item.dimensionTags,
          ...item.knowledgePoints.slice(0, 2),
        ]}
      />
      <p>{item.reason}</p>
      {expanded && (
        <div className="analysis-detail">
          <FeedbackItem title="你的回答摘录">{item.answer || "暂无回答内容"}</FeedbackItem>
          <FeedbackItem title="为什么这样评分">{item.feedback || item.reason}</FeedbackItem>
          <FeedbackItem title="答对的点">
            {item.covered.length ? item.covered.join("、") : "暂未识别到稳定覆盖的关键点。"}
          </FeedbackItem>
          <FeedbackItem title="遗漏或不准确">
            {[...item.missing, ...item.incorrect].length
              ? [...item.missing, ...item.incorrect].join("、")
              : "没有明显事实错误，主要优化空间在表达结构和工程细节。"}
          </FeedbackItem>
          <FeedbackItem title="建议补强">{item.suggestion}</FeedbackItem>
        </div>
      )}
    </article>
  );
}

function ProfileCard({ profile }) {
  const view = buildProfileView(profile);
  return (
    <StepCard number="05" title="能力画像摘要" tone="cyan">
      <p>画像固定绑定本机默认用户；画像分来自最近答题评分和错误累计，用于训练排序，不等同于真实能力百分比。</p>
      <FeedbackItem title="画像结论">{view.summary}</FeedbackItem>
      {view.strengths.length > 0 && (
        <FeedbackGroup title="较熟悉">
          {view.strengths.map((item) => (
            <FeedbackItem
              key={item.id}
              title={item.knowledge_point}
              tags={[`画像分 ${profileScore(item.mastery_score)}`]}
            >
              最近回答能覆盖该知识点的主要内容，可在下一轮加入场景化追问。
            </FeedbackItem>
          ))}
        </FeedbackGroup>
      )}
      {view.weaknesses.length > 0 && (
        <FeedbackGroup title="需要加强">
          {view.weaknesses.map((item) => (
            <FeedbackItem
              key={item.id}
              title={item.knowledge_point}
              tags={[`画像分 ${profileScore(item.mastery_score)}`]}
            >
              画像分偏低，说明最近回答在评分或错误模式上不稳定，建议用“定义、流程、风险、工程方案”重新组织一次回答。
            </FeedbackItem>
          ))}
        </FeedbackGroup>
      )}
      {view.errors.length > 0 && (
        <FeedbackGroup title="高频错误">
          {view.errors.map((item) => (
            <FeedbackItem
              key={item.id}
              title={errorLabels[item.error_type] ?? item.error_type}
              tags={[`${item.occurrence_count} 次`, item.knowledge_point]}
            >
              这个错误会影响面试官对知识边界的判断，下一轮训练需要专门验证。
            </FeedbackItem>
          ))}
        </FeedbackGroup>
      )}
    </StepCard>
  );
}

function NextPlanCard({ profile }) {
  const view = buildPlanView(profile);
  return (
    <StepCard number="06" title="下一轮训练计划" tone="pink">
      <p>只展示待完成或推荐训练项，不再暴露 open、due_review_task 等内部字段。</p>
      <FeedbackItem title="计划结论" tags={[`已完成 ${view.completedCount} 项`]}>
        {view.summary}
      </FeedbackItem>
      {view.openTasks.length > 0 && (
        <FeedbackGroup title="待完成复习">
          {view.openTasks.map((item) => (
            <FeedbackItem
              key={item.id}
              title={`补强：${item.knowledge_point}`}
              tags={[
                statusLabels[item.status] ?? item.status,
                `优先级 P${item.priority}`,
                errorLabels[item.error_type] ?? item.error_type,
              ]}
            >
              来源于最近面试中的错误模式。建议重新回答相关题目，并主动补充引用依据和边界条件。
            </FeedbackItem>
          ))}
        </FeedbackGroup>
      )}
      {view.recommendations.length > 0 && (
        <FeedbackGroup title="推荐下一轮题目">
          {view.recommendations.map((item) => (
            <FeedbackItem
              key={`${item.knowledge_point}-${item.reason}`}
              title={item.knowledge_point}
              tags={[
                `优先级 P${item.priority}`,
                item.mastery_score ? `画像分 ${profileScore(item.mastery_score)}` : "新知识点",
              ]}
            >
              {translateReason(item.reason)}
            </FeedbackItem>
          ))}
        </FeedbackGroup>
      )}
    </StepCard>
  );
}

function translateReason(reason) {
  if (reason?.startsWith("due_review_task")) return "来自到期复习任务，说明这个知识点最近出错过，需要优先巩固。";
  if (reason === "low_mastery") return "掌握度偏低，适合作为下一轮面试训练主题。";
  return reason || "系统根据画像和复习任务推荐。";
}

function StatusPanel({ status, error, busy, runtime }) {
  return (
    <aside className="status-panel">
      <div className={`orb ${busy ? "loading" : ""}`} />
      <div>
        <span>Runtime Status</span>
        <strong>{status}</strong>
        <p>
          {error ||
            `${runtimeLabel(runtime)}；本地 Docker Compose 运行，适合 16GB 普通开发机演示。`}
        </p>
      </div>
    </aside>
  );
}

function Metric({ label, value }) {
  return (
    <article className="metric">
      <small>{label}</small>
      <strong>{value}</strong>
    </article>
  );
}

function StepCard({ number, title, tone, children }) {
  return (
    <article className={`step-card ${tone}`}>
      <div className="step-title">
        <span>{number}</span>
        <h2>{title}</h2>
      </div>
      {children}
    </article>
  );
}

function Info({ label, value }) {
  return (
    <div className="info">
      <small>{label}</small>
      <code>{value}</code>
    </div>
  );
}

function ResultBox({ title, subtitle, children }) {
  return (
    <div className="result-box">
      <div>
        <strong>{title}</strong>
        <small>{subtitle}</small>
      </div>
      <div className="result-content">{children}</div>
    </div>
  );
}

function Progress({ value }) {
  return (
    <div className="progress" aria-label={`面试进度 ${value}%`}>
      <span style={{ width: `${value}%` }} />
    </div>
  );
}

function TagRow({ tags }) {
  if (!tags?.length) return null;
  return (
    <div className="tag-row">
      {tags.map((tag) => (
        <span key={tag}>{tag}</span>
      ))}
    </div>
  );
}

function FeedbackGroup({ title, children }) {
  return (
    <section className="feedback-group">
      <h3>{title}</h3>
      <div className="feedback-list">{children}</div>
    </section>
  );
}

function FeedbackItem({ title, tags, children }) {
  return (
    <article className="feedback-item">
      <div className="feedback-item-head">
        <strong>{title}</strong>
        <TagRow tags={tags} />
      </div>
      <p>{children}</p>
    </article>
  );
}

function MiniList({ items, empty }) {
  if (!items.length) return <Empty text={empty} />;
  return (
    <ul className="mini-list">
      {items.slice(0, 4).map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function Empty({ text }) {
  return <div className="empty">{text}</div>;
}

createRoot(document.getElementById("root")).render(<App />);
