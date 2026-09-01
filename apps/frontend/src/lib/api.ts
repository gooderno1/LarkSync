/* ------------------------------------------------------------------ */
/*  API 请求封装                                                       */
/* ------------------------------------------------------------------ */

// 默认无前缀（开发模式由 Vite 代理，生产模式由 FastAPI 同源服务）
// 如需自定义前缀，可通过 VITE_API_BASE 环境变量设置
const apiBase: string = import.meta.env.VITE_API_BASE ?? "";

export function apiUrl(path: string): string {
  return `${apiBase}${path}`;
}

export function getCurrentAppUrl(): string {
  if (typeof window === "undefined") return "";
  return window.location.href;
}

export function getActiveAccountId(): string {
  try {
    return window.localStorage.getItem("larksync.active-account-id") || "";
  } catch {
    return "";
  }
}

export function getLoginUrl(): string {
  const redirect = getCurrentAppUrl();
  return redirect
    ? `${apiUrl("/auth/login")}?redirect=${encodeURIComponent(redirect)}`
    : apiUrl("/auth/login");
}

/** 统一 fetch 封装：自动解析 JSON、统一抛错 */
export async function apiFetch<T = unknown>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const headers = new Headers(init?.headers);
  try {
    const accountId = getActiveAccountId();
    if (accountId && !headers.has("X-LarkSync-Account-ID")) {
      headers.set("X-LarkSync-Account-ID", accountId);
    }
  } catch {
    // SSR/隐私模式下继续使用后端记录的活动账户。
  }
  const res = await fetch(apiUrl(path), { ...init, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      (body as Record<string, string>).detail || `请求失败 (${res.status})`
    );
  }
  return res.json() as Promise<T>;
}

export function apiFetchForAccount<T = unknown>(
  path: string,
  accountId: string,
  init?: RequestInit,
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (accountId) headers.set("X-LarkSync-Account-ID", accountId);
  return apiFetch<T>(path, { ...init, headers });
}
