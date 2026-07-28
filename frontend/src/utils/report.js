import { unique } from "./formatters.js";

export const dimensionLabels = {
  correctness: "准确性",
  completeness: "完整性",
  reasoning: "推理链路",
  communication: "表达结构",
};

export function buildReportView(report) {
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
      ? `下一轮优先按“定义 → 流程 → 风险 → 工程方案”重答，并重点提升 ${weakDimensions[0].label}。`
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

export function buildQuestionAnalysis(evaluation, index) {
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
