import { Empty, FeedbackItem, StepCard, TagRow } from "./common.jsx";

function formatDate(value) {
  if (!value) return "未知时间";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function ratioLabel(value) {
  return `${Math.round((value ?? 0) * 100)}%`;
}

function trendSummary(trends) {
  if (!trends?.length) return "完成多轮面试后，这里会展示总分和四维能力趋势。";
  if (trends.length === 1) return "当前只有一轮报告，继续训练后可观察趋势变化。";
  const first = trends[0];
  const last = trends[trends.length - 1];
  const delta = Math.round((last.score_ratio - first.score_ratio) * 100);
  if (delta > 0) return `最近 ${trends.length} 轮总分提升 ${delta} 个百分点，训练方向有效。`;
  if (delta < 0) return `最近 ${trends.length} 轮总分下降 ${Math.abs(delta)} 个百分点，建议回看低分维度。`;
  return `最近 ${trends.length} 轮总分保持稳定，建议增加更难的场景化追问。`;
}

function dimensionTrendTags(trends) {
  if (!trends?.length) return [];
  const last = trends[trends.length - 1];
  const labels = {
    correctness: "准确",
    completeness: "完整",
    reasoning: "推理",
    communication: "表达",
  };
  return Object.entries(last.dimension_averages ?? {}).map(
    ([key, value]) => `${labels[key] ?? key} ${Number(value).toFixed(1)}/5`,
  );
}

export function ReportHistoryPanel({ history, trends, onOpenReport }) {
  const reports = history ?? [];
  const trendItems = trends ?? [];
  return (
    <StepCard number="07" title="报告历史与多轮趋势" tone="blue">
      <p>把单轮评分沉淀为长期训练记录，用于观察分数变化、低分维度和下一轮训练方向。</p>
      <FeedbackItem title="趋势摘要" tags={dimensionTrendTags(trendItems)}>
        {trendSummary(trendItems)}
      </FeedbackItem>
      {trendItems.length > 0 && (
        <div className="trend-bars">
          {trendItems.map((item, index) => (
            <div className="trend-row" key={item.report_id}>
              <span>{index + 1}. {item.topic}</span>
              <div className="trend-track">
                <i style={{ width: ratioLabel(item.score_ratio) }} />
              </div>
              <strong>{item.total_score}/{item.max_score}</strong>
            </div>
          ))}
        </div>
      )}
      {reports.length > 0 ? (
        <div className="report-history-list">
          {reports.map((item) => (
            <button
              className="history-card"
              key={item.id}
              type="button"
              onClick={() => onOpenReport(item)}
            >
              <strong>{item.topic}</strong>
              <span>{formatDate(item.created_at)} · {item.difficulty}</span>
              <TagRow
                tags={[
                  `总分 ${item.total_score}/${item.max_score}`,
                  ratioLabel(item.score_ratio),
                  item.low_confidence_count ? `低置信 ${item.low_confidence_count}` : "置信正常",
                  item.disputed_count ? `争议 ${item.disputed_count}` : null,
                ].filter(Boolean)}
              />
            </button>
          ))}
        </div>
      ) : (
        <Empty text="暂无历史报告；完成一轮面试评分后会自动出现在这里。" />
      )}
    </StepCard>
  );
}
