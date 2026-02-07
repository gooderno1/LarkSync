/* ------------------------------------------------------------------ */
/*  API 请求封装                                                       */
/* ------------------------------------------------------------------ */

// 默认无前缀（开发模式由 Vite 代理，生产模式由 FastAPI 同源服务）
// 如需自定义前缀，可通过 VITE_API_BASE 环境变量设置
const apiBase: string = import.meta.env.VITE_API_BASE ?? "";

export function apiUrl(path: string): string {
  return `${apiBase}${path}`;
}

export function getLoginUrl(): string {
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  return origin
    ? `${apiUrl("/auth/login")}?redirect=${encodeURIComponent(origin)}`
    : apiUrl("/auth/login");
}

/** 统一 fetch 封装：自动解析 JSON、统一抛错 */
export async function apiFetch<T = unknown>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(apiUrl(path), init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      (body as Record<string, string>).detail || `请求失败 (${res.status})`
    );
  }
  return res.json() as Promise<T>;
}
