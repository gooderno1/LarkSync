export function shouldUseRemainingPagesShowcase(search: string, isDevelopment: boolean): boolean {
  if (!isDevelopment) return false;
  return new URLSearchParams(search).get("ui-data") !== "live";
}

export function useRemainingPagesShowcase(): boolean {
  const search = typeof window === "undefined" ? "?ui-data=live" : window.location.search;
  return shouldUseRemainingPagesShowcase(search, import.meta.env.DEV);
}
