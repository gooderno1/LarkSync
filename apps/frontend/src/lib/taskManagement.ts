import type { SyncFileEvent, Tone } from "../types";

export const pendingRealtimeStatuses = new Set([
  "queued",
  "creating",
  "created",
  "reimporting",
  "delete_pending",
]);

export function summarizePath(
  value: string,
  keepSegments = 3,
  maxTailChars = 48
): string {
  const text = value.trim();
  if (!text) return "-";
  if (text.length <= maxTailChars) return text;
  const segments = text.split(/[\\/]+/).filter(Boolean);
  if (segments.length >= keepSegments) {
    return `.../${segments.slice(-keepSegments).join("/")}`;
  }
  return `...${text.slice(-maxTailChars)}`;
}

export function deletePolicyLabel(value?: string | null): string {
  if (value === "off") return "关闭删除联动";
  if (value === "strict") return "严格删除";
  return "安全删除";
}

type DeriveTaskHealthInput = {
  enabled: boolean;
  state?: string | null;
  lastFiles?: SyncFileEvent[] | null;
  conflictCount: number;
  lastError?: string | null;
  failedFiles?: number | null;
  deleteFailedFiles?: number | null;
};

export type TaskHealthMeta = {
  tone: Tone;
  label: string;
  isRunning: boolean;
  hasFailure: boolean;
  pendingRealtimeCount: number;
};

export function deriveTaskHealth({
  enabled,
  state,
  lastFiles,
  conflictCount,
  lastError,
  failedFiles,
  deleteFailedFiles,
}: DeriveTaskHealthInput): TaskHealthMeta {
  const isRunning = state === "running";
  const pendingRealtimeCount = (lastFiles || []).filter((item) =>
    pendingRealtimeStatuses.has(item.status)
  ).length;
  const hasFailure = Boolean(
    lastError || (failedFiles ?? 0) > 0 || (deleteFailedFiles ?? 0) > 0 || state === "failed"
  );

  if (hasFailure) {
    return {
      tone: "danger",
      label: "需要排查",
      isRunning,
      hasFailure,
      pendingRealtimeCount,
    };
  }

  if (conflictCount > 0) {
    return {
      tone: "warning",
      label: "有冲突",
      isRunning,
      hasFailure,
      pendingRealtimeCount,
    };
  }

  if (pendingRealtimeCount > 0) {
    return {
      tone: "warning",
      label: "待处理",
      isRunning,
      hasFailure,
      pendingRealtimeCount,
    };
  }

  if (isRunning) {
    return {
      tone: "info",
      label: "同步中",
      isRunning,
      hasFailure,
      pendingRealtimeCount,
    };
  }

  return {
    tone: enabled ? "success" : "neutral",
    label: enabled ? "已同步" : "已停用",
    isRunning,
    hasFailure,
    pendingRealtimeCount,
  };
}

export function parseDeleteGraceMinutes(
  policy: "off" | "safe" | "strict",
  value: string,
  fallback = 30
): number {
  if (policy === "strict") return 0;
  return Math.max(0, Number.parseInt(value || String(fallback), 10) || 0);
}
