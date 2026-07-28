export function runtimeLabel(runtime) {
  return runtime.llm_enabled ? `真实 LLM 已启用：${runtime.llm_model}` : "本地基线模式";
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
