import {
  buildPlanView,
  buildProfileView,
  compactRawLabel,
  errorLabels,
  errorNarrative,
  profileScore,
  statusLabels,
  strengthNarrative,
  translateReason,
  weaknessNarrative,
} from "../utils/profile.js";
import { Empty, FeedbackGroup, FeedbackItem, StepCard, TagRow } from "./common.jsx";

export function ProfilePanel({ profile }) {
  const view = buildProfileView(profile);
  const coverage = profile.coverage;
  return (
    <StepCard number="05" title="能力画像摘要" tone="cyan">
      <p>画像固定绑定本机默认用户；画像分来自最近答题评分和错误累计，用于训练排序，不等同于真实能力百分比。</p>
      <FeedbackItem title="画像结论">{view.summary}</FeedbackItem>
      {coverage && (
        <FeedbackItem
          title="知识查漏覆盖"
          tags={[
            `总计 ${coverage.total}`,
            `待覆盖 ${coverage.uncovered}`,
            `验证中 ${coverage.attempted}`,
            `已验证 ${coverage.verified}`,
          ]}
        >
          新导入资料只会增加待覆盖知识点，不会降低已有能力分。只有题目实际引用资料切片并取得可信评分后，知识点才会进入已验证状态。
        </FeedbackItem>
      )}
      {view.strengths.length > 0 && (
        <FeedbackGroup title="相对稳定">
          {view.strengths.map((item) => (
            <FeedbackItem
              key={item.id}
              title={item.display_title}
              tags={[profileScore(item.mastery_score)]}
            >
              {strengthNarrative(item)}
              {item.subtopics?.length > 0 && (
                <TagRow
                  tags={item.subtopics.map(
                    (point) =>
                      `${point.subtopic_title} ${Math.round(point.mastery_score * 100)}`,
                  )}
                />
              )}
            </FeedbackItem>
          ))}
        </FeedbackGroup>
      )}
      {view.weaknesses.length > 0 && (
        <FeedbackGroup title="需要加强">
          {view.weaknesses.map((item) => (
            <FeedbackItem
              key={item.id}
              title={item.display_title}
              tags={[
                profileScore(item.mastery_score),
                item.source_count > 1 ? `合并 ${item.source_count} 个细项` : null,
              ].filter(Boolean)}
            >
              {weaknessNarrative(item)}
              {item.raw_points?.length > 0 && (
                <TagRow tags={item.raw_points.map((point) => compactRawLabel(point))} />
              )}
              {item.subtopics?.length > 0 && (
                <TagRow
                  tags={item.subtopics.map(
                    (point) =>
                      `${point.subtopic_title} ${Math.round(point.mastery_score * 100)}`,
                  )}
                />
              )}
            </FeedbackItem>
          ))}
        </FeedbackGroup>
      )}
      {view.errors.length > 0 ? (
        <FeedbackGroup title="高频错误">
          {view.errors.map((item) => (
            <FeedbackItem
              key={item.id}
              title={errorLabels[item.error_type] ?? item.error_type}
              tags={[`${item.occurrence_count} 次`, item.display_title]}
            >
              {errorNarrative(item)}
            </FeedbackItem>
          ))}
        </FeedbackGroup>
      ) : (
        <Empty text="暂无错误模式；完成评分后会出现高频错误归纳。" />
      )}
    </StepCard>
  );
}

export function NextPlanPanel({ profile }) {
  const view = buildPlanView(profile);
  return (
    <StepCard number="06" title="下一轮训练计划" tone="pink">
      <p>只展示待完成或推荐训练项，不再暴露 open、due_review_task 等内部字段。</p>
      <FeedbackItem title="计划结论" tags={[view.completedCount ? `已完成 ${view.completedCount} 项` : null].filter(Boolean)}>
        {view.summary}
      </FeedbackItem>
      {view.openTasks.length > 0 && (
        <FeedbackGroup title="待完成复习">
          {view.openTasks.map((item) => (
            <FeedbackItem
              key={item.id}
              title={`补强：${item.display_title}`}
              tags={[
                statusLabels[item.status] ?? item.status,
                `优先级 P${item.priority}`,
                errorLabels[item.error_type] ?? item.error_type,
                `验证 ${Math.min(item.verification_streak ?? 0, 2)}/2`,
              ]}
            >
              来源于最近面试中的错误模式。建议重新回答相关题目，并主动补充引用依据和边界条件。
            </FeedbackItem>
          ))}
        </FeedbackGroup>
      )}
      {view.recommendations.length > 0 ? (
        <FeedbackGroup title="推荐下一轮题目">
          {view.recommendations.map((item) => (
            <FeedbackItem
              key={item.id}
              title={item.display_title}
              tags={[`优先级 P${item.priority}`, item.mastery_score != null ? profileScore(item.mastery_score) : null].filter(Boolean)}
            >
              {translateReason(item.reason)}
            </FeedbackItem>
          ))}
        </FeedbackGroup>
      ) : (
        <Empty text="完成一轮评分后，这里会给出下一轮训练推荐。" />
      )}
    </StepCard>
  );
}
