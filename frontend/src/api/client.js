function apiErrorMessage(responseStatus, data) {
  return data?.message ?? `请求失败：${responseStatus}`;
}

export async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers ?? {}),
    },
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(apiErrorMessage(response.status, data));
  }
  return data;
}
