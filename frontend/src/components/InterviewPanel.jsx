import { Info, Progress, ResultBox, StepCard } from "./common.jsx";

const practiceCounts = [1, 3, 5];
const difficultyOptions = [
  { value: "easy", label: "简单 easy" },
  { value: "medium", label: "中等 medium" },
  { value: "hard", label: "困难 hard" },
];

function difficultyLabel(value) {
  return difficultyOptions.find((item) => item.value === value)?.label ?? value;
}

export function InterviewPanel({
  documents,
  profile,
  interviewTopic,
  trainingMode,
  practiceQuestionCount,
  practiceDifficulty,
  interview,
  answerDraft,
  busy,
  canUseKnowledgeBase,
  completion,
  isCompleted,
  currentQuestion,
  currentFollowUp,
  currentDefaultAnswer,
  followUpDraft,
  workflowTrace,
  onTopicChange,
  onTrainingModeChange,
  onPracticeQuestionCountChange,
  onPracticeDifficultyChange,
  onStartInterview,
  onAnswerDraftChange,
  onFollowUpDraftChange,
  onUseDefaultAnswer,
  onSubmitAnswer,
  onSubmitFollowUpAnswer,
  onEvaluateAndReport,
}) {
  const interviewPolicy = currentQuestion?.rubric?.interview_policy;
  const isWaitingForFollowUp = Boolean(currentFollowUp);
  const isPractice = trainingMode === "practice";
  const runningPractice = interview?.training_mode === "practice";
  return (
    <StepCard number="03" title="可恢复模拟面试" tone="green">
      <p>
        画像训练固定 3 题中等难度，计入能力画像与知识覆盖；自定义练习可自选题数和难度，
        仅用于演练，不计入任何统计。
      </p>
      <div className="mode-switch" role="group" aria-label="面试模式">
        <button
          type="button"
          className={isPractice ? "" : "active"}
          onClick={() => onTrainingModeChange("profile_training")}
          disabled={busy}
        >
          画像训练
        </button>
        <button
          type="button"
          className={isPractice ? "active" : ""}
          onClick={() => onTrainingModeChange("practice")}
          disabled={busy}
        >
          自定义练习
        </button>
      </div>
      {isPractice ? (
        <div className="practice-config">
          <p className="practice-warning">本次练习不计入能力画像和知识覆盖统计</p>
          <div className="option-row">
            <span className="option-label">题数</span>
            {practiceCounts.map((count) => (
              <button
                key={count}
                type="button"
                className={`option-chip ${practiceQuestionCount === count ? "active" : ""}`}
                onClick={() => onPracticeQuestionCountChange(count)}
                disabled={busy}
              >
                {count} 题
              </button>
            ))}
          </div>
          <div className="option-row">
            <span className="option-label">难度</span>
            {difficultyOptions.map((item) => (
              <button
                key={item.value}
                type="button"
                className={`option-chip ${practiceDifficulty === item.value ? "active" : ""}`}
                onClick={() => onPracticeDifficultyChange(item.value)}
                disabled={busy}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <p className="hint">画像训练：固定 3 题 / 中等难度，计入画像与覆盖</p>
      )}
      <label className="field-label" htmlFor="interview-topic">
        本轮面试主题
      </label>
      <input
        id="interview-topic"
        className="text-input"
        value={interviewTopic}
        onChange={(event) => onTopicChange(event.target.value)}
        placeholder="例如：LangGraph、Checkpoint、Human-in-the-loop"
      />
      <p className="hint">
        当前推荐来源：
        {profile.plan.length > 0
          ? "知识覆盖计划、用户画像与复习计划"
          : documents.some((item) => item.status === "ready")
            ? "已入库资料"
            : "默认 AI Agent 主题"}
      </p>
      <button
        onClick={onStartInterview}
        disabled={!canUseKnowledgeBase || busy || !interviewTopic.trim()}
      >
        {isPractice
          ? `开始自定义练习（${practiceQuestionCount} 题 · ${difficultyLabel(practiceDifficulty)}）`
          : "开始画像训练（3 题 · 中等难度）"}
      </button>
      {interview && (
        <div className="interview-box">
          <Progress value={completion} />
          <Info label="Workflow Status" value={interview.status} />
          <Info label="Training Mode" value={runningPractice ? "practice" : "profile_training"} />
          {runningPractice ? (
            <p className="practice-warning">练习模式，不计入画像和覆盖统计</p>
          ) : null}
          {workflowTrace.length > 0 ? (
            <details className="workflow-trace">
              <summary>Agent 工作流轨迹（{workflowTrace.length} 个 checkpoint）</summary>
              {workflowTrace.map((item) => (
                <article className="trace-item" key={item.checkpoint_id}>
                  <span>{item.label}</span>
                  <small>{item.event}</small>
                  <p>{item.output_summary}</p>
                </article>
              ))}
            </details>
          ) : null}
          {currentQuestion ? (
            <ResultBox title={`第 ${currentQuestion.sequence} 题`} subtitle="当前等待回答">
              {interviewPolicy ? (
                <div className="policy-note">
                  <span>轻量面试官策略</span>
                  <strong>{interviewPolicy.target_topic}</strong>
                  <p>{interviewPolicy.reason}</p>
                  <small>{interviewPolicy.deterministic_gate}</small>
                </div>
              ) : null}
              <strong>{currentQuestion.question_text}</strong>
              {isWaitingForFollowUp ? (
                <div className="follow-up-card">
                  <span className="pill">受控追问 · 最多 1 次</span>
                  <h4>{currentFollowUp.prompt}</h4>
                  <p>{currentFollowUp.reason}</p>
                  {currentFollowUp.expected_points.length > 0 ? (
                    <div className="tag-row">
                      {currentFollowUp.expected_points.map((point) => (
                        <span className="tag" key={point}>
                          {point}
                        </span>
                      ))}
                    </div>
                  ) : null}
                  <textarea
                    value={followUpDraft}
                    onChange={(event) => onFollowUpDraftChange(event.target.value)}
                    placeholder="这里回答追问；留空提交会使用本题追问参考答案完成演示闭环。"
                    rows={6}
                  />
                  <div className="inline-actions">
                    <button
                      className="secondary"
                      type="button"
                      onClick={() => onFollowUpDraftChange(currentFollowUp.reference_answer)}
                      disabled={busy || !currentFollowUp.reference_answer}
                    >
                      使用追问参考答案
                    </button>
                    <button
                      onClick={onSubmitFollowUpAnswer}
                      disabled={
                        busy ||
                        (!followUpDraft.trim() && !currentFollowUp.reference_answer?.trim())
                      }
                    >
                      {followUpDraft.trim() ? "提交追问回答" : "使用追问参考答案提交"}
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <textarea
                    value={answerDraft}
                    onChange={(event) => onAnswerDraftChange(event.target.value)}
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
                      onClick={onUseDefaultAnswer}
                      disabled={busy || !currentDefaultAnswer}
                    >
                      使用本题参考答案
                    </button>
                    <button
                      onClick={onSubmitAnswer}
                      disabled={busy || (!answerDraft.trim() && !currentDefaultAnswer)}
                    >
                      {answerDraft.trim() ? "提交我的答案" : "使用默认答案提交"}
                    </button>
                  </div>
                </>
              )}
            </ResultBox>
          ) : (
            <button onClick={onEvaluateAndReport} disabled={busy || !isCompleted}>
              {runningPractice ? "生成练习报告（不计入画像）" : "生成评分报告和画像"}
            </button>
          )}
        </div>
      )}
    </StepCard>
  );
}
