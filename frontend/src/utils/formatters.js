export function runtimeLabel(runtime) {
  return runtime?.llm_enabled ? `真实 LLM 已启用：${runtime.llm_model ?? "已配置"}` : "本地基线模式";
}

export function runtimeVersionLabel(runtime) {
  return runtime?.app_version ? `API ${runtime.app_version}` : "API 版本未知";
}

export function runtimeStartedLabel(runtime) {
  if (!runtime?.started_at || runtime.started_at === "unknown") return "启动时间未知";
  const startedAt = new Date(runtime.started_at);
  if (Number.isNaN(startedAt.getTime())) return runtime.started_at;
  return startedAt.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function embeddingLabel(runtime) {
  const provider = runtime?.embedding_provider ?? "unknown";
  const dimension = runtime?.embedding_dimension;
  if (provider === "unknown") return "Embedding 未知";
  return `${provider}${dimension ? ` · ${dimension}维` : ""}`;
}

export function percent(value) {
  return `${Math.round((value ?? 0) * 100)}%`;
}

export function profileScore(value) {
  return `${Math.round((value ?? 0) * 100)} / 100`;
}

export function unique(items) {
  return [...new Set(items.filter(Boolean))];
}
