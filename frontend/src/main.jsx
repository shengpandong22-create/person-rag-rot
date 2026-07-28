import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api/client.js";
import { EvaluationPanel } from "./components/EvaluationPanel.jsx";
import { InterviewPanel } from "./components/InterviewPanel.jsx";
import { KnowledgePanel } from "./components/KnowledgePanel.jsx";
import { NextPlanPanel, ProfilePanel } from "./components/ProfilePanel.jsx";
import { RagPanel } from "./components/RagPanel.jsx";
import { ReportHistoryPanel } from "./components/ReportHistoryPanel.jsx";
import { RuntimeInsights } from "./components/RuntimeInsights.jsx";
import { TrainingFocusPanel } from "./components/TrainingFocusPanel.jsx";
import { Metric, StatusPanel } from "./components/common.jsx";
import { runtimeLabel } from "./utils/formatters.js";
import { inferInterviewTopic } from "./utils/profile.js";
import "./styles.css";

const terminalDocumentStatuses = new Set(["ready", "failed", "archived"]);

const emptyProfile = {
  abilities: [],
  errors: [],
  tasks: [],
  plan: [],
  focuses: [],
};

function App() {
  const [status, setStatus] = useState("正在连接本地服务...");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [runtime, setRuntime] = useState({ llm_enabled: false, llm_model: null });
  const [knowledgeBase, setKnowledgeBase] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [askQuestion, setAskQuestion] = useState(
    "RAG 为什么能提升 AI 面试助手回答的可信度？",
  );
  const [askResult, setAskResult] = useState(null);
  const [interviewTopic, setInterviewTopic] = useState("AI Agent");
  const [topicEdited, setTopicEdited] = useState(false);
  const [interview, setInterview] = useState(null);
  const [answerDraft, setAnswerDraft] = useState("");
  const [report, setReport] = useState(null);
  const [reportHistory, setReportHistory] = useState([]);
  const [scoreTrends, setScoreTrends] = useState([]);
  const [profile, setProfile] = useState(emptyProfile);

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
      const [
        runtimeInfo,
        bases,
        abilities,
        errors,
        tasks,
        plan,
        focuses,
        history,
        trends,
      ] = await Promise.all([
        api("/health/runtime"),
        api("/api/v1/knowledge-bases"),
        api("/api/v1/profiles/me/abilities"),
        api("/api/v1/profiles/me/error-patterns"),
        api("/api/v1/review-tasks"),
        api("/api/v1/profiles/me/interview-plan"),
        api("/api/v1/profiles/me/training-focuses"),
        api("/api/v1/reports/history"),
        api("/api/v1/reports/trends"),
      ]);
      setRuntime(runtimeInfo);
      setProfile({ abilities, errors, tasks, plan, focuses });
      setReportHistory(history);
      setScoreTrends(trends);
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
      const [abilities, errors, tasks, plan, focuses, history, trends] = await Promise.all([
        api("/api/v1/profiles/me/abilities"),
        api("/api/v1/profiles/me/error-patterns"),
        api("/api/v1/review-tasks"),
        api("/api/v1/profiles/me/interview-plan"),
        api("/api/v1/profiles/me/training-focuses"),
        api("/api/v1/reports/history"),
        api("/api/v1/reports/trends"),
      ]);
      setReport(builtReport);
      setProfile({ abilities, errors, tasks, plan, focuses });
      setReportHistory(history);
      setScoreTrends(trends);
    });

  const openHistoricalReport = (item) =>
    run("打开历史报告", async () => {
      const historicalReport = await api(`/api/v1/interviews/${item.session_id}/report`);
      setReport(historicalReport);
      setStatus(`已打开历史报告：${item.topic}`);
    });

  function selectTrainingFocus(item) {
    setInterviewTopic(item.knowledge_point);
    setTopicEdited(true);
    setStatus(`已选择专项训练主题：${item.knowledge_point}`);
  }

  function changeInterviewTopic(value) {
    setInterviewTopic(value);
    setTopicEdited(true);
  }

  return (
    <main className="shell">
      <section className="hero">
        <div className="hero-copy">
          <div className="pill">AI Agent Interview Coach · Local V2</div>
          <h1>把学习资料变成可追溯、可复盘的 AI 面试训练。</h1>
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

      <RuntimeInsights runtime={runtime} askResult={askResult} report={report} />

      <section className="workflow">
        <KnowledgePanel
          knowledgeBase={knowledgeBase}
          documents={documents}
          busy={busy}
          onUpload={uploadDocument}
        />
        <RagPanel
          askQuestion={askQuestion}
          askResult={askResult}
          canUseKnowledgeBase={canUseKnowledgeBase}
          busy={busy}
          onQuestionChange={setAskQuestion}
          onAsk={ask}
        />
        <TrainingFocusPanel
          focuses={profile.focuses}
          disabled={busy || !canUseKnowledgeBase}
          onSelect={selectTrainingFocus}
        />
        <InterviewPanel
          documents={documents}
          profile={profile}
          interviewTopic={interviewTopic}
          interview={interview}
          answerDraft={answerDraft}
          busy={busy}
          canUseKnowledgeBase={canUseKnowledgeBase}
          completion={completion}
          isCompleted={isCompleted}
          currentQuestion={currentQuestion}
          currentDefaultAnswer={currentDefaultAnswer}
          onTopicChange={changeInterviewTopic}
          onStartInterview={startInterview}
          onAnswerDraftChange={setAnswerDraft}
          onUseDefaultAnswer={() => setAnswerDraft(currentDefaultAnswer)}
          onSubmitAnswer={submitAnswer}
          onEvaluateAndReport={evaluateAndReport}
        />
        <EvaluationPanel report={report} />
        <ProfilePanel profile={profile} />
        <NextPlanPanel profile={profile} />
        <ReportHistoryPanel
          history={reportHistory}
          trends={scoreTrends}
          onOpenReport={openHistoricalReport}
        />
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
