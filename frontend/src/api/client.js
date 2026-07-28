function apiErrorMessage(responseStatus, data) {
  if (data && typeof data === "object") {
    return data.message ?? data.detail ?? `请求失败：${responseStatus}`;
  }
  return typeof data === "string" && data.trim()
    ? `请求失败：${responseStatus} · ${data.trim().slice(0, 160)}`
    : `请求失败：${responseStatus}`;
}

export async function api(path, options = {}) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), options.timeoutMs ?? 30000);
  try {
    const response = await fetch(path, {
      ...options,
      signal: options.signal ?? controller.signal,
      headers: {
        ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...(options.headers ?? {}),
      },
    });
    const text = await response.text();
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = text;
      }
    }
    if (!response.ok) {
      throw new Error(apiErrorMessage(response.status, data));
    }
    return data;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("请求超时，请检查本地服务或稍后重试。");
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}
