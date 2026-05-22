import type { ConflictResolutionAction, Tone } from "../types";

export type ConflictResolutionState = "queued" | "running" | "waiting" | "success" | "error";

export type ConflictResolutionStatus = {
  action: ConflictResolutionAction;
  state: ConflictResolutionState;
  message?: string | null;
  attempt?: number;
};

export type ConflictResolutionSummary = {
  queued: number;
  running: number;
  waiting: number;
  success: number;
  failed: number;
};

export const CONFLICT_ACTION_LABELS: Record<ConflictResolutionAction, string> = {
  use_local: "使用本地",
  use_cloud: "使用云端",
};

export function isTaskBusyConflictError(message?: string | null): boolean {
  const text = (message || "").trim();
  if (!text) return false;
  return (
    text.includes("任务运行中") ||
    text.includes("请稍后再试") ||
    text.includes("正在同步")
  );
}

export function summarizeConflictResolutionStates(
  states: Record<string, ConflictResolutionStatus>,
): ConflictResolutionSummary {
  return Object.values(states).reduce<ConflictResolutionSummary>(
    (summary, item) => {
      if (item.state === "queued") summary.queued += 1;
      else if (item.state === "running") summary.running += 1;
      else if (item.state === "waiting") summary.waiting += 1;
      else if (item.state === "success") summary.success += 1;
      else if (item.state === "error") summary.failed += 1;
      return summary;
    },
    { queued: 0, running: 0, waiting: 0, success: 0, failed: 0 },
  );
}

export function getConflictStatusMeta(
  resolved: boolean,
  resolvedAction: string | null | undefined,
  resolutionState: ConflictResolutionStatus | undefined,
): { label: string; tone: Tone; detail: string | null } {
  if (resolved) {
    return { label: "已处理", tone: "success", detail: resolvedAction || null };
  }
  if (!resolutionState) {
    return { label: "待处理", tone: "warning", detail: null };
  }
  if (resolutionState.state === "success") {
    return { label: "已完成", tone: "success", detail: resolutionState.message ?? null };
  }
  if (resolutionState.state === "running") {
    return { label: "处理中", tone: "info", detail: resolutionState.message ?? null };
  }
  if (resolutionState.state === "waiting") {
    return { label: "等待重试", tone: "warning", detail: resolutionState.message ?? null };
  }
  if (resolutionState.state === "queued") {
    return { label: "已排队", tone: "warning", detail: resolutionState.message ?? null };
  }
  return { label: "处理失败", tone: "danger", detail: resolutionState.message ?? null };
}
