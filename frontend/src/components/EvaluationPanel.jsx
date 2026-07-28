import { useState } from "react";
import { buildReportView } from "../utils/report.js";
import { Empty, FeedbackGroup, FeedbackItem, StepCard, TagRow } from "./common.jsx";

export function EvaluationPanel({ report }) {
  const view = buildReportView(report);
  return (
    <StepCard number="04" title="本轮面试报告" tone="orange">
      <p>把模型评分转译成可执行反馈，不再直接堆砌重复的维度模板。</p>
      {view ? (
        <div className="score-card">
          <div className="score-total">
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
      >
        <span>第 {item.sequence} 题</span>
        <strong>{item.total}/20</strong>
        <small>{expanded ? "收起解析" : "展开解析"}</small>
      </button>
      <strong className="analysis-question">{item.question}</strong>
      <TagRow tags={item.dimensionTags} />
      <FeedbackItem title="为什么这样打分">{item.reason}</FeedbackItem>
      <FeedbackItem title="下一步补强">{item.suggestion}</FeedbackItem>
      {expanded && (
        <div className="analysis-detail">
          <FeedbackItem title="你的回答">{item.answer || "暂无回答内容"}</FeedbackItem>
          {item.covered.length > 0 && (
            <FeedbackItem title="已覆盖要点" tags={item.covered.slice(0, 4)}>
              这些内容是本题评分中的正向依据。
            </FeedbackItem>
          )}
          {item.missing.length > 0 && (
            <FeedbackItem title="缺失要点" tags={item.missing.slice(0, 4)}>
              这些内容建议在下一轮回答时补齐。
            </FeedbackItem>
          )}
          {item.incorrect.length > 0 && (
            <FeedbackItem title="不准确结论" tags={item.incorrect.slice(0, 4)}>
              这些表述可能影响面试官对知识边界的判断。
            </FeedbackItem>
          )}
          <FeedbackItem title="模型反馈">{item.feedback}</FeedbackItem>
        </div>
      )}
    </article>
  );
}
