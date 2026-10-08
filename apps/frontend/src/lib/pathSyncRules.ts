import type { PathSyncRule } from "../types";

export function normalizeRulePath(value: string): string {
  const raw = value.trim().replace(/\\/g, "/");
  const parts = raw.split("/").filter((part) => part && part !== ".");
  if (raw.startsWith("/") || /[:*?]/.test(raw) || raw.includes(String.fromCharCode(0)) || !parts.length || parts.includes("..")) {
    throw new Error("请输入任务目录内的固定相对路径，不能使用绝对路径、通配符或父目录跳转。");
  }
  return parts.join("/");
}

export function rulesEqual(left: PathSyncRule[], right: PathSyncRule[]): boolean {
  const serialize = (rules: PathSyncRule[]) => JSON.stringify(
    rules.map(({ path, kind, sync_mode }) => [path, kind, sync_mode]).sort((a, b) => a[0].localeCompare(b[0])),
  );
  return serialize(left) === serialize(right);
}

export function effectivePathSyncMode(defaultMode: string, rules: PathSyncRule[], path: string): string {
  let best = -1;
  let mode = defaultMode;
  for (const rule of rules) {
    if (path !== rule.path && !(rule.kind === "folder" && path.startsWith(`${rule.path}/`))) continue;
    const rank = rule.path.split("/").length * 2 + Number(rule.kind === "file");
    if (rank > best) { best = rank; mode = rule.sync_mode; }
  }
  return mode;
}
