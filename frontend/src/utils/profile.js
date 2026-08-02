import { profileScore, unique } from "./formatters.js";

export const errorLabels = {
  concept_confusion: "概念混淆",
  missing_key_point: "关键点遗漏",
  hallucination: "不可靠结论",
  no_answer: "回答不足",
};

export const statusLabels = {
  open: "待完成",
  completed: "已完成",
};

export function inferInterviewTopic(documents, profile) {
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

  const focused = profile.focuses?.[0]?.knowledge_point;
  if (focused) return focused;

  const recommended = profile.plan?.[0]?.knowledge_point;
  if (recommended) return recommended;

  const weakAbility = [...(profile.abilities ?? [])].sort(
    (a, b) => a.mastery_score - b.mastery_score,
  )[0]?.knowledge_point;
  return weakAbility || "AI Agent";
}

export function normalizeKnowledgePoint(point) {
  const text = String(point ?? "").trim();
  const lower = text.toLowerCase();
  if (!text) return { title: "未命名知识点", raw: "" };

  if (
    lower.includes("compact") ||
    lower.includes("micro_compact") ||
    lower.includes("auto_compact") ||
    lower.includes("摘要") ||
    lower.includes("压缩")
  ) {
    return { title: "上下文压缩与记忆管理", raw: text };
  }
  if (
    lower.includes("token") ||
    lower.includes("context window") ||
    lower.includes("上下文窗口") ||
    lower.includes("窗口有限") ||
    lower.includes("超限")
  ) {
    return { title: "上下文窗口与 Token 管理", raw: text };
  }
  if (
    lower.includes("stream") ||
    lower.includes("writer") ||
    lower.includes("custom") ||
    lower.includes("流式") ||
    lower.includes("自定义数据")
  ) {
    return { title: "流式输出与事件通道", raw: text };
  }
  if (lower.includes("checkpoint") || lower.includes("checkpointer")) {
    return { title: "Checkpoint 与状态恢复", raw: text };
  }
  if (lower.includes("state") || lower.includes("状态")) {
    return { title: "状态建模与工作流控制", raw: text };
  }
  if (lower.includes("node") || lower.includes("edge") || lower.includes("graph") || lower.includes("langgraph")) {
    return { title: "LangGraph 图编排基础", raw: text };
  }
  if (lower.includes("interrupt") || lower.includes("human-in-the-loop")) {
    return { title: "人工介入与可恢复执行", raw: text };
  }
  if (lower.includes("rag") || lower.includes("retrieval")) {
    return { title: "RAG 检索增强生成", raw: text };
  }
  if (lower.includes("tool") || lower.includes("function calling")) {
    return { title: "工具调用与结果处理", raw: text };
  }
  if (lower.includes("memory") || lower.includes("记忆")) {
    return { title: "长期记忆与用户画像", raw: text };
  }
  return { title: text.length > 36 ? `${text.slice(0, 34)}...` : text, raw: text };
}

export function mergeKnowledgeItems(items, scoreField = "mastery_score") {
  const groups = new Map();
  for (const item of items) {
    const hierarchyTitle =
      item.subtopic_title || item.topic_title || item.knowledge_point;
    const normalized = item.profile_level && item.profile_level !== "legacy"
      ? { title: hierarchyTitle, raw: hierarchyTitle }
      : normalizeKnowledgePoint(item.knowledge_point);
    const existing = groups.get(normalized.title) ?? {
      ...item,
      id: normalized.title,
      display_title: normalized.title,
      raw_points: [],
      occurrence_count: 0,
      source_count: 0,
    };
    existing.raw_points = unique([...existing.raw_points, normalized.raw]).slice(0, 3);
    existing.source_count += 1;
    if (scoreField in item) {
      existing[scoreField] = Math.min(existing[scoreField] ?? item[scoreField], item[scoreField]);
    }
    if ("occurrence_count" in item) {
      existing.occurrence_count += item.occurrence_count;
    }
    existing.priority = Math.max(existing.priority ?? 0, item.priority ?? 0);
    existing.status = existing.status ?? item.status;
    existing.error_type = existing.error_type ?? item.error_type;
    existing.reason = existing.reason ?? item.reason;
    groups.set(normalized.title, existing);
  }
  return [...groups.values()];
}

export function compactRawLabel(value) {
  const text = String(value ?? "").trim();
  if (!text) return "原始细项";
  return text.length > 22 ? `${text.slice(0, 20)}...` : text;
}

export function buildProfileView(profile) {
  const topicAbilities = (profile.abilities ?? [])
    .filter((item) => item.profile_level === "topic")
    .map((item) => ({
      ...item,
      id: item.topic_key,
      display_title: item.topic_title || item.knowledge_point,
      source_count: item.confidence_weighted_count,
      subtopics: (profile.abilities ?? [])
        .filter(
          (child) =>
            child.profile_level === "subtopic" &&
            child.topic_key === item.topic_key,
        )
        .sort((a, b) => a.mastery_score - b.mastery_score),
    }));
  const abilities = (
    topicAbilities.length > 0
      ? topicAbilities
      : mergeKnowledgeItems(profile.abilities ?? [])
  ).sort(
    (a, b) => b.mastery_score - a.mastery_score,
  );
  const strengths = abilities.filter((item) => item.mastery_score >= 0.6).slice(0, 3);
  const weaknesses = abilities
    .filter((item) => item.mastery_score < 0.6)
    .sort((a, b) => b.source_count - a.source_count || a.mastery_score - b.mastery_score)
    .slice(0, 3);
  const errors = mergeKnowledgeItems(profile.errors, "occurrence_count")
    .sort((a, b) => b.occurrence_count - a.occurrence_count)
    .slice(0, 3);

  return {
    strengths,
    weaknesses,
    errors,
    summary:
      abilities.length === 0
        ? "完成一次面试报告后，这里会沉淀你的本机用户画像。"
        : `已沉淀 ${abilities.length} 个稳定主题画像，${weaknesses.length} 个需要优先补强；子知识点仅作为诊断证据。`,
  };
}

export function buildPlanView(profile) {
  const openTasks = mergeKnowledgeItems(
    profile.tasks.filter((item) => item.status !== "completed"),
    "priority",
  )
    .sort((a, b) => b.priority - a.priority)
    .slice(0, 3);
  const recommendations = mergeKnowledgeItems(profile.plan, "priority")
    .sort((a, b) => b.priority - a.priority)
    .slice(0, 3);
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

export function strengthNarrative(item) {
  if (item.display_title.includes("RAG")) {
    return "最近回答已经能覆盖检索、生成和引用溯源的主链路，下一轮可以增加召回质量和证据不足场景的追问。";
  }
  if (item.display_title.includes("状态") || item.display_title.includes("Checkpoint")) {
    return "你已经能说明状态保存或恢复的基本作用，下一轮可以补充失败恢复、并发隔离和状态一致性细节。";
  }
  return "最近回答能覆盖该主题的主要内容，下一轮可以加入更贴近项目实现的场景化追问。";
}

export function weaknessNarrative(item) {
  const score = Math.round((item.mastery_score ?? 0) * 100);
  if (item.display_title.includes("状态")) {
    return `画像分 ${score}，说明状态流转、节点边界或恢复链路还不够稳定。建议按“状态字段 → 节点职责 → 状态迁移 → 异常恢复”重答一次。`;
  }
  if (item.display_title.includes("RAG")) {
    return `画像分 ${score}，说明检索、证据引用或答案生成边界还没讲扎实。建议补充 Query 改写、召回排序、引用校验和证据不足处理。`;
  }
  if (item.display_title.includes("压缩") || item.display_title.includes("Token")) {
    return `画像分 ${score}，说明上下文裁剪、摘要保真或 token 成本控制还需要补强。建议说明触发条件、保留策略和信息丢失风险。`;
  }
  if (item.display_title.includes("流式")) {
    return `画像分 ${score}，说明流式事件、writer 输出和前端消费链路还不够清晰。建议按“事件来源 → 通道协议 → UI 消费 → 错误处理”梳理。`;
  }
  return `画像分 ${score}，说明这个主题最近回答不够稳定。建议用“定义、流程、边界、工程方案”重新组织一次回答。`;
}

export function errorNarrative(item) {
  const label = errorLabels[item.error_type] ?? item.error_type;
  if (item.error_type === "missing_detail" || label.includes("遗漏")) {
    return `最近 ${item.occurrence_count} 次出现细节遗漏，重点补齐 ${item.display_title} 的关键步骤、边界条件和异常场景。`;
  }
  if (item.error_type === "concept_confusion" || label.includes("概念")) {
    return `这里主要是概念边界混淆：需要区分 ${item.display_title} 中相近概念的职责、输入输出和适用场景。`;
  }
  if (item.error_type === "incorrect_reasoning") {
    return "推理链路不够稳定，建议把结论拆成“前提、依据、推导、限制条件”，避免跳步。";
  }
  return `该错误在 ${item.display_title} 上重复出现，下一轮训练应验证原因、修正表达，并观察是否再次复发。`;
}

export function translateReason(reason) {
  if (reason?.startsWith("coverage_gap:uncovered"))
    return "该知识点来自已入库资料，但尚未被面试题实际覆盖，建议优先查漏。";
  if (reason?.startsWith("coverage_gap:attempted"))
    return "该知识点已经出题，但还没有可信评分，需要继续完成验证。";
  if (reason?.startsWith("coverage_gap:insufficient_evidence"))
    return "该知识点只有一次可信评分，证据不足，建议再验证一轮。";
  if (reason?.startsWith("due_review_task")) return "来自到期复习任务，说明这个知识点最近出错过，需要优先巩固。";
  if (reason === "low_mastery") return "掌握度偏低，适合作为下一轮面试训练主题。";
  return reason || "系统根据画像和复习任务推荐。";
}

export { profileScore };
