import { Info, Progress, ResultBox, StepCard } from "./common.jsx";

export function InterviewPanel({
  documents,
  profile,
  interviewTopic,
  interview,
  answerDraft,
  busy,
  canUseKnowledgeBase,
  completion,
  isCompleted,
  currentQuestion,
  currentDefaultAnswer,
  onTopicChange,
  onStartInterview,
  onAnswerDraftChange,
  onUseDefaultAnswer,
  onSubmitAnswer,
  onEvaluateAndReport,
}) {
  return (
    <StepCard number="03" title="可恢复模拟面试" tone="green">
      <p>
        三题面试会保存 checkpoint；主题默认根据已入库资料和画像推荐生成，也可以手动指定。
      </p>
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
        {documents.some((item) => item.status === "ready")
          ? "已入库资料"
          : profile.plan.length > 0
            ? "用户画像与复习计划"
            : "默认 AI Agent 主题"}
      </p>
      <button
        onClick={onStartInterview}
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
            </ResultBox>
          ) : (
            <button onClick={onEvaluateAndReport} disabled={busy || !isCompleted}>
              生成评分报告和画像
            </button>
          )}
        </div>
      )}
    </StepCard>
  );
}
