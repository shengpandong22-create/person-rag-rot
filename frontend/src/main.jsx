import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const sampleAnswer =
  "RAG 会先从知识库检索相关片段，再基于证据组织回答。它的关键价值是让答案可追溯，通过引用 chunk 降低幻觉风险；如果资料不足，系统应该明确说明证据不足，而不是伪造引用。";

const terminalDocumentStatuses = new Set(["ready", "failed", "archived"]);

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
    throw new Error(data?.message ?? `请求失败：${response.status}`);
  }
  return data;
}

function App() {
  const [status, setStatus] = useState("正在连接本地服务...");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [knowledgeBase, setKnowledgeBase] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [askQuestion, setAskQuestion] = useState("RAG 为什么能提升 AI 面试助手回答的可信度？");
  const [askResult, setAskResult] = useState(null);
  const [interview, setInterview] = useState(null);
  const [answerDraft, setAnswerDraft] = useState(sampleAnswer);
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

  useEffect(() => {
    bootstrap();
  }, []);

  async function bootstrap() {
    setBusy(true);
    setError("");
    try {
      await api("/health/ready");
      const [bases, abilities, errors, tasks, plan] = await Promise.all([
        api("/api/v1/knowledge-bases"),
        api("/api/v1/profiles/me/abilities"),
        api("/api/v1/profiles/me/error-patterns"),
        api("/api/v1/review-tasks"),
        api("/api/v1/profiles/me/interview-plan"),
      ]);
      setProfile({ abilities, errors, tasks, plan });
      const restored = await restoreKnowledgeWorkspace(bases);
      if (restored.base) {
        setKnowledgeBase(restored.base);
        setDocuments(restored.documents);
        const suffix = restored.documents.length ? `，资料 ${restored.documents.length} 份` : "";
        setStatus(`已恢复知识库：${restored.base.name}${suffix}`);
      } else {
        setStatus("本地服务已就绪，请创建你的第一个知识库");
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
          topic: "RAG",
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
      const updated = await api(`/api/v1/interviews/${interview.id}/answers`, {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({
          question_id: currentQuestion.id,
          answer: answerDraft,
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
            当前运行模式：本地确定性基线。RAG、画像、评分链路已跑通；真实 LLM Gateway
            尚未启用，后续可接 OpenAI-compatible API。
          </p>
        </div>
        <StatusPanel status={status} error={error} busy={busy} />
      </section>

      <section className="metrics">
        <Metric label="知识库" value={knowledgeBase ? "Ready" : "Pending"} />
        <Metric label="已入库资料" value={documents.length} />
        <Metric label="面试进度" value={interview ? `${completion}%` : "0%"} />
        <Metric label="报告总分" value={report ? `${report.total_score}/${report.max_score}` : "—"} />
      </section>

      <section className="workflow">
        <StepCard number="01" title="知识库与资料入库" tone="blue">
          <p>刷新页面会自动恢复最近的知识库和资料列表；不需要每次重新创建。</p>
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
          <p>你可以自己输入问题；系统会基于知识库检索证据并返回引用。</p>
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
          <p>三题面试会保存 checkpoint；你可以输入自己的答案，示例答案只作为辅助。</p>
          <button onClick={startInterview} disabled={!canUseKnowledgeBase || busy}>
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
                    placeholder="在这里输入你的真实回答..."
                    rows={7}
                  />
                  <div className="inline-actions">
                    <button
                      className="secondary"
                      type="button"
                      onClick={() => setAnswerDraft(sampleAnswer)}
                      disabled={busy}
                    >
                      填入示例
                    </button>
                    <button onClick={submitAnswer} disabled={busy || !answerDraft.trim()}>
                      提交我的答案
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

        <StepCard number="04" title="可信评分报告" tone="orange">
          <p>总分由应用层规则计算，低置信与争议结果显式展示，不伪造确定结论。</p>
          {report ? (
            <div className="score-card">
              <div>
                <span>{report.total_score}</span>
                <small>/ {report.max_score}</small>
              </div>
              <MiniList items={report.next_steps} empty="暂无建议" />
            </div>
          ) : (
            <Empty text="完成三题面试后生成报告" />
          )}
        </StepCard>

        <StepCard number="05" title="能力画像与错题模式" tone="cyan">
          <p>画像保存在数据库中，刷新页面后会恢复；只有可信 Evaluation 才会更新画像。</p>
          <MiniList
            items={profile.abilities.map(
              (item) => `${item.knowledge_point} · mastery ${item.mastery_score}`,
            )}
            empty="暂无能力画像"
          />
          <MiniList
            items={profile.errors.map(
              (item) => `${item.knowledge_point} · ${item.error_type} × ${item.occurrence_count}`,
            )}
            empty="暂无错误模式"
          />
        </StepCard>

        <StepCard number="06" title="复习任务与下一轮计划" tone="pink">
          <p>复习间隔按重复错误推进，下一轮训练优先选择到期任务和低掌握度知识点。</p>
          <MiniList
            items={profile.tasks.map(
              (item) => `${item.knowledge_point} · ${item.status} · P${item.priority}`,
            )}
            empty="暂无复习任务"
          />
          <MiniList
            items={profile.plan.map((item) => `${item.knowledge_point} · ${item.reason}`)}
            empty="暂无推荐计划"
          />
        </StepCard>
      </section>
    </main>
  );
}

function StatusPanel({ status, error, busy }) {
  return (
    <aside className="status-panel">
      <div className={`orb ${busy ? "loading" : ""}`} />
      <div>
        <span>Runtime Status</span>
        <strong>{status}</strong>
        <p>{error || "本地 Docker Compose 运行；适合在 16GB 普通开发机演示完整闭环。"}</p>
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
