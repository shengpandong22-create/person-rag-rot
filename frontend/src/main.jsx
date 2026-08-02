import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api/client.js";
import { AppLayout, OverviewDashboard } from "./components/AppLayout.jsx";
import { EvaluationPanel } from "./components/EvaluationPanel.jsx";
import { InterviewPanel } from "./components/InterviewPanel.jsx";
import {
  CreateKnowledgeBaseDialog,
  KnowledgeBaseSelector,
} from "./components/KnowledgeBaseControls.jsx";
import { KnowledgePanel } from "./components/KnowledgePanel.jsx";
import { NextPlanPanel, ProfilePanel } from "./components/ProfilePanel.jsx";
import { RagPanel } from "./components/RagPanel.jsx";
import { ReportHistoryPanel } from "./components/ReportHistoryPanel.jsx";
import { RuntimeInsights } from "./components/RuntimeInsights.jsx";
import { TrainingFocusPanel } from "./components/TrainingFocusPanel.jsx";
import { StatusPanel } from "./components/common.jsx";
import { runtimeLabel } from "./utils/formatters.js";
import { inferInterviewTopic } from "./utils/profile.js";
import "./styles.css";

const terminalDocumentStatuses = new Set(["ready", "failed", "archived"]);
const activeInterviewKey = "agentmentor.activeInterviewId";
const activeKnowledgeBaseKey = "agentmentor.activeKnowledgeBaseId";
const answerIdempotencyPrefix = "agentmentor.answerIdempotency";

function interviewStorageKey(knowledgeBaseId) {
  return `${activeInterviewKey}.${knowledgeBaseId}`;
}

const emptyProfile = {
  abilities: [],
  errors: [],
  tasks: [],
  plan: [],
  focuses: [],
  coverage: null,
};

async function optionalApi(path, fallback) {
  try {
    return await api(path);
  } catch {
    return fallback;
  }
}

function App() {
  const [status, setStatus] = useState("正在连接本地服务...");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [runtime, setRuntime] = useState({ llm_enabled: false, llm_model: null });
  const [knowledgeBase, setKnowledgeBase] = useState(null);
  const [knowledgeBases, setKnowledgeBases] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newKnowledgeBaseName, setNewKnowledgeBaseName] = useState("");
  const [newKnowledgeBaseDescription, setNewKnowledgeBaseDescription] = useState("");
  const [askQuestion, setAskQuestion] = useState(
    "RAG 为什么能提升 AI 面试助手回答的可信度？",
  );
  const [askResult, setAskResult] = useState(null);
  const [allowModelKnowledge, setAllowModelKnowledge] = useState(false);
  const [interviewTopic, setInterviewTopic] = useState("AI Agent");
  const [selectedTrainingFocus, setSelectedTrainingFocus] = useState(null);
  const [topicEdited, setTopicEdited] = useState(false);
  const [interview, setInterview] = useState(null);
  const [workflowTrace, setWorkflowTrace] = useState([]);
  const [answerDraft, setAnswerDraft] = useState("");
  const [report, setReport] = useState(null);
  const [reportHistory, setReportHistory] = useState([]);
  const [scoreTrends, setScoreTrends] = useState([]);
  const [readiness, setReadiness] = useState(null);
  const [profile, setProfile] = useState(emptyProfile);
  const [activeView, setActiveView] = useState("overview");

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
      const runtimeInfo = await optionalApi("/health/runtime", {
        llm_enabled: false,
        llm_model: null,
        status_unavailable: true,
      });
      setRuntime(runtimeInfo);
      const bases = await api("/api/v1/knowledge-bases");
      const catalog = await Promise.all(
        bases.map(async (base) => {
          const baseDocuments = await optionalApi(
            `/api/v1/knowledge-bases/${base.id}/documents`,
            null,
          );
          return {
            ...base,
            document_count: baseDocuments?.length ?? null,
            documents: baseDocuments,
            documents_unavailable: baseDocuments === null,
          };
        }),
      );
      const restored = await restoreKnowledgeWorkspace(catalog);
      // An empty knowledge base is still a real workspace. Keep the full catalog so
      // creating one can never make an older workspace disappear from the selector.
      setKnowledgeBases(catalog);
      if (restored.base) {
        setKnowledgeBase(restored.base);
        setDocuments(restored.documents);
        await loadKnowledgeBaseLearningState(restored.base.id);
        await restoreActiveInterview(restored.base.id);
        const suffix = restored.documents.length ? `，资料 ${restored.documents.length} 份` : "";
        setStatus(`${runtimeLabel(runtimeInfo)}，已恢复知识库：${restored.base.name}${suffix}`);
      } else {
        clearKnowledgeBaseLearningState();
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
    const preferredId = window.localStorage.getItem(activeKnowledgeBaseKey);
    const orderedBases = [...bases].sort((left, right) => {
      if (left.id === preferredId) return -1;
      if (right.id === preferredId) return 1;
      return 0;
    });
    let fallback = { base: orderedBases[0] ?? null, documents: [] };
    for (const base of orderedBases) {
      const persistedDocuments =
        base.documents ??
        (await optionalApi(`/api/v1/knowledge-bases/${base.id}/documents`, []));
      if (base === orderedBases[0]) {
        fallback = { base, documents: persistedDocuments };
      }
      if (base.id === preferredId || persistedDocuments.length > 0) {
        window.localStorage.setItem(activeKnowledgeBaseKey, base.id);
        return { base, documents: persistedDocuments };
      }
    }
    return fallback;
  }

  function clearKnowledgeBaseLearningState() {
    setProfile(emptyProfile);
    setReportHistory([]);
    setScoreTrends([]);
    setReport(null);
  }

  async function loadKnowledgeBaseLearningState(knowledgeBaseId) {
    clearKnowledgeBaseLearningState();
    const basePath = `/api/v1/knowledge-bases/${knowledgeBaseId}`;
    const [abilities, errors, tasks, plan, focuses, coverage, history, trends, demoReadiness] =
      await Promise.all([
        optionalApi(`${basePath}/profile/abilities`, []),
        optionalApi(`${basePath}/profile/error-patterns`, []),
        optionalApi(`${basePath}/review-tasks`, []),
        optionalApi(`${basePath}/interview-plan`, []),
        optionalApi(`${basePath}/training-focuses`, []),
        optionalApi(`${basePath}/coverage`, null),
        optionalApi(`${basePath}/reports/history`, []),
        optionalApi(`${basePath}/reports/trends`, []),
        optionalApi("/api/v1/demo/readiness", null),
      ]);
    setProfile({ abilities, errors, tasks, plan, focuses, coverage });
    setReportHistory(history);
    setScoreTrends(trends);
    setReadiness(demoReadiness);
  }

  async function restoreActiveInterview(knowledgeBaseId) {
    setInterview(null);
    setWorkflowTrace([]);
    setAnswerDraft("");
    const scopedKey = interviewStorageKey(knowledgeBaseId);
    const interviewId =
      window.localStorage.getItem(scopedKey) ??
      window.localStorage.getItem(activeInterviewKey);
    if (!interviewId) return null;
    try {
      const restoredInterview = await api(`/api/v1/interviews/${interviewId}`);
      if (restoredInterview.knowledge_base_id !== knowledgeBaseId) {
        window.localStorage.removeItem(scopedKey);
        return null;
      }
      setInterview(restoredInterview);
      setWorkflowTrace(await loadWorkflowTrace(restoredInterview.id));
      window.localStorage.setItem(scopedKey, restoredInterview.id);
      window.localStorage.removeItem(activeInterviewKey);
      return restoredInterview;
    } catch {
      window.localStorage.removeItem(scopedKey);
      return null;
    }
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

  async function activateKnowledgeBase(base) {
    const baseDocuments = await api(`/api/v1/knowledge-bases/${base.id}/documents`);
    setKnowledgeBase(base);
    setDocuments(baseDocuments);
    setKnowledgeBases((items) =>
      items.map((item) =>
        item.id === base.id
          ? { ...item, document_count: baseDocuments.length, documents: baseDocuments }
          : item,
      ),
    );
    window.localStorage.setItem(activeKnowledgeBaseKey, base.id);
    setAskResult(null);
    setReport(null);
    setSelectedTrainingFocus(null);
    setTopicEdited(false);
    await loadKnowledgeBaseLearningState(base.id);
    await restoreActiveInterview(base.id);
    setReadiness(await api("/api/v1/demo/readiness"));
  }

  const switchKnowledgeBase = (knowledgeBaseId) => {
    if (
      answerDraft.trim() &&
      !window.confirm("当前输入的答案尚未提交，切换知识库会清空本地草稿，是否继续？")
    ) {
      return;
    }
    return run("切换知识库", async () => {
      if (!knowledgeBaseId || knowledgeBaseId === knowledgeBase?.id) return;
      const nextBase = knowledgeBases.find((item) => item.id === knowledgeBaseId);
      if (!nextBase) throw new Error("选择的知识库不存在，请刷新后重试。");
      await activateKnowledgeBase(nextBase);
      setStatus(`已切换知识库：${nextBase.name}`);
      setActiveView("knowledge");
    });
  };

  function openCreateKnowledgeBaseDialog() {
    setNewKnowledgeBaseName("");
    setNewKnowledgeBaseDescription("");
    setCreateDialogOpen(true);
  }

  function closeCreateKnowledgeBaseDialog() {
    if (busy) return;
    setCreateDialogOpen(false);
  }

  const createKnowledgeBase = () =>
    run("创建知识库", async () => {
      const name = newKnowledgeBaseName.trim();
      if (!name) throw new Error("请输入知识库名称。");
      const kb = await api("/api/v1/knowledge-bases", {
        method: "POST",
        body: JSON.stringify({
          name,
          description: newKnowledgeBaseDescription.trim() || null,
        }),
      });
      const created = { ...kb, document_count: 0, documents: [] };
      setKnowledgeBases((items) => [...items, created]);
      await activateKnowledgeBase(created);
      setCreateDialogOpen(false);
      setActiveView("knowledge");
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
      setKnowledgeBases((items) =>
        items.map((item) =>
          item.id === knowledgeBase.id
            ? {
                ...item,
                document_count:
                  (item.documents ?? []).some((existing) => existing.id === document.id)
                    ? item.document_count
                    : (item.document_count ?? 0) + 1,
                documents: [
                  document,
                  ...(item.documents ?? []).filter((existing) => existing.id !== document.id),
                ],
              }
            : item,
        ),
      );
      await pollDocumentStatus(document.id);
      event.target.value = "";
    });

  const reindexDocument = (documentId) =>
    run("重新索引资料", async () => {
      const document = await api(`/api/v1/documents/${documentId}/reindex`, {
        method: "POST",
      });
      replaceDocument(document);
      await pollDocumentStatus(document.id);
    });

  const ask = () =>
    run("执行带引用 RAG 问答", async () => {
      const result = await api(`/api/v1/knowledge-bases/${knowledgeBase.id}/ask`, {
        method: "POST",
        body: JSON.stringify({
          question: askQuestion,
          allow_model_knowledge: allowModelKnowledge,
        }),
      });
      setAskResult(result);
    });

  const startInterview = () =>
    run("创建并启动三题面试", async () => {
      const routedTopic = selectedTrainingFocus
        ? [
            selectedTrainingFocus.topic_title,
            selectedTrainingFocus.subtopic_title,
          ]
            .filter(Boolean)
            .join(" · ")
        : interviewTopic.trim();
      const created = await api("/api/v1/interviews", {
        method: "POST",
        body: JSON.stringify({
          knowledge_base_id: knowledgeBase.id,
          topic: routedTopic || inferInterviewTopic(documents, profile),
          profile_topic_key: selectedTrainingFocus?.topic_key ?? null,
          profile_topic_title: selectedTrainingFocus?.topic_title ?? null,
          profile_subtopic_key: selectedTrainingFocus?.subtopic_key ?? null,
          profile_subtopic_title: selectedTrainingFocus?.subtopic_title ?? null,
          difficulty: "medium",
          question_count: 3,
        }),
      });
      const started = await api(`/api/v1/interviews/${created.id}/start`, { method: "POST" });
      setInterview(started);
      window.localStorage.setItem(interviewStorageKey(knowledgeBase.id), started.id);
      setWorkflowTrace(await loadWorkflowTrace(started.id));
      setAnswerDraft("");
      setReport(null);
      setActiveView("interview");
    });

  const submitAnswer = () =>
    run("提交答案并推进工作流", async () => {
      const finalAnswer =
        answerDraft.trim() ||
        currentDefaultAnswer ||
        "我暂时无法完整回答这道题，需要结合参考资料继续学习。";
      const storageKey = `${answerIdempotencyPrefix}.${interview.id}.${currentQuestion.id}`;
      let idempotencyKey = window.localStorage.getItem(storageKey);
      if (!idempotencyKey) {
        idempotencyKey = crypto.randomUUID();
        window.localStorage.setItem(storageKey, idempotencyKey);
      }
      const updated = await api(`/api/v1/interviews/${interview.id}/answers`, {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: JSON.stringify({
          question_id: currentQuestion.id,
          answer: finalAnswer,
        }),
      });
      window.localStorage.removeItem(storageKey);
      setInterview(updated);
      window.localStorage.setItem(interviewStorageKey(knowledgeBase.id), updated.id);
      setWorkflowTrace(await loadWorkflowTrace(updated.id));
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
      setWorkflowTrace(await loadWorkflowTrace(interview.id));
      await loadKnowledgeBaseLearningState(knowledgeBase.id);
      setReport(builtReport);
      setActiveView("reports");
    });

  const openHistoricalReport = (item) =>
    run("打开历史报告", async () => {
      const historicalReport = await api(`/api/v1/interviews/${item.session_id}/report`);
      setReport(historicalReport);
      setStatus(`已打开历史报告：${item.topic}`);
      setActiveView("reports");
    });

  function selectTrainingFocus(item) {
    setInterviewTopic(item.knowledge_point);
    setSelectedTrainingFocus(item);
    setTopicEdited(true);
    setStatus(`已选择专项训练主题：${item.knowledge_point}`);
  }

  function changeInterviewTopic(value) {
    setInterviewTopic(value);
    setSelectedTrainingFocus(null);
    setTopicEdited(true);
  }

  async function loadWorkflowTrace(interviewId) {
    return api(`/api/v1/interviews/${interviewId}/workflow-trace`);
  }

  return (
    <AppLayout
      activeView={activeView}
      onNavigate={setActiveView}
      runtime={runtime}
      knowledgeBase={knowledgeBase}
      interview={interview}
      actions={
        <>
          <KnowledgeBaseSelector
            bases={knowledgeBases}
            currentId={knowledgeBase?.id}
            busy={busy}
            onSelect={switchKnowledgeBase}
            onCreate={openCreateKnowledgeBaseDialog}
          />
          <button className="secondary" onClick={refreshWorkspace} disabled={busy}>
            刷新状态
          </button>
          <a href="/api/v1/docs" target="_blank" rel="noreferrer">
            OpenAPI
          </a>
        </>
      }
    >
      {activeView === "overview" ? (
        <OverviewDashboard
          runtime={runtime}
          documents={documents}
          interview={interview}
          completion={completion}
          readiness={readiness}
          profile={profile}
          reportHistory={reportHistory}
          onNavigate={setActiveView}
          onSelectFocus={selectTrainingFocus}
          onOpenReport={openHistoricalReport}
        />
      ) : null}
      {activeView === "knowledge" ? (
        <div className="task-stage">
          <KnowledgePanel
            knowledgeBase={knowledgeBase}
            documents={documents}
            busy={busy}
            onUpload={uploadDocument}
            onReindex={reindexDocument}
            onOpenSelector={() => {
              document.querySelector(".knowledge-base-controls select")?.focus();
              setStatus("请从顶部“当前知识库”选择器切换知识库");
            }}
          />
        </div>
      ) : null}
      <CreateKnowledgeBaseDialog
        open={createDialogOpen}
        busy={busy}
        name={newKnowledgeBaseName}
        description={newKnowledgeBaseDescription}
        onNameChange={setNewKnowledgeBaseName}
        onDescriptionChange={setNewKnowledgeBaseDescription}
        onCancel={closeCreateKnowledgeBaseDialog}
        onConfirm={createKnowledgeBase}
      />
      {activeView === "rag" ? (
        <div className="task-stage">
          <RagPanel
            askQuestion={askQuestion}
            askResult={askResult}
            allowModelKnowledge={allowModelKnowledge}
            canUseKnowledgeBase={canUseKnowledgeBase}
            busy={busy}
            onQuestionChange={setAskQuestion}
            onAllowModelKnowledgeChange={setAllowModelKnowledge}
            onAsk={ask}
          />
        </div>
      ) : null}
      {activeView === "interview" ? (
        <div className="task-split interview-layout">
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
            workflowTrace={workflowTrace}
            onTopicChange={changeInterviewTopic}
            onStartInterview={startInterview}
            onAnswerDraftChange={setAnswerDraft}
            onUseDefaultAnswer={() => setAnswerDraft(currentDefaultAnswer)}
            onSubmitAnswer={submitAnswer}
            onEvaluateAndReport={evaluateAndReport}
          />
        </div>
      ) : null}
      {activeView === "reports" ? (
        <div className="report-layout">
          <EvaluationPanel report={report} />
          <ReportHistoryPanel
            history={reportHistory}
            trends={scoreTrends}
            onOpenReport={openHistoricalReport}
          />
        </div>
      ) : null}
      {activeView === "profile" ? (
        <div className="task-split profile-layout">
          <ProfilePanel profile={profile} />
          <NextPlanPanel profile={profile} />
        </div>
      ) : null}
      {activeView === "system" ? (
        <div className="system-layout">
          <StatusPanel status={status} error={error} busy={busy} runtime={runtime} />
          <RuntimeInsights
            runtime={runtime}
            askResult={askResult}
            report={report}
            readiness={readiness}
          />
        </div>
      ) : null}
    </AppLayout>
  );
}

createRoot(document.getElementById("root")).render(<App />);
