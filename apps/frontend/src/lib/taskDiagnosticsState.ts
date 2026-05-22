import { diagnosticActivityTime } from "./logCenter";
import type {
  SyncFileEvent,
  SyncTask,
  SyncTaskDiagnosticCounts,
  SyncTaskOverview,
  SyncTaskRunSummary,
  SyncTaskStatus,
} from "../types";

export type RunAlertMeta = {
  label: string;
  className: string;
  message: string;
};

export function sortTaskOverviewsByActivity(overviewItems: SyncTaskOverview[]): SyncTaskOverview[] {
  return [...overviewItems].sort((a, b) => diagnosticActivityTime(b) - diagnosticActivityTime(a));
}

export function getRunAlertMeta(message?: string | null): RunAlertMeta | null {
  const trimmed = message?.trim();
  if (!trimmed) return null;
  if (
    trimmed.includes("运行被中断") ||
    trimmed.includes("partial 模式不支持超限表格文档，请改用 auto/full")
  ) {
    return {
      label: trimmed.includes("运行被中断") ? "最近中断" : "最近提示",
      className: "border-amber-500/40 bg-amber-500/10 text-amber-300",
      message: trimmed,
    };
  }
  return {
    label: "最近错误",
    className: "border-rose-500/40 bg-rose-500/10 text-rose-300",
    message: trimmed,
  };
}

type DeriveTaskDiagnosticsStateOptions = {
  selectedTask: SyncTask | null;
  selectedStatus: SyncTaskStatus | null;
  selectedRun: SyncTaskRunSummary | null;
  activeOverview: SyncTaskOverview | null;
};

export function deriveTaskDiagnosticsState({
  selectedTask,
  selectedStatus,
  selectedRun,
  activeOverview,
}: DeriveTaskDiagnosticsStateOptions): {
  currentFile: SyncFileEvent | null;
  diagnosticCounts: SyncTaskDiagnosticCounts | null;
  lastActivityAt: number | null;
  selectedStateKey: string;
  runAlert: RunAlertMeta | null;
} {
  const currentFile = selectedRun?.current_file ?? activeOverview?.current_file ?? null;
  const diagnosticCounts = selectedRun?.counts ?? activeOverview?.counts ?? null;
  const lastActivityAt =
    selectedRun?.last_event_at ??
    selectedStatus?.finished_at ??
    selectedStatus?.started_at ??
    selectedTask?.last_run_at ??
    activeOverview?.last_event_at ??
    null;
  const selectedStateKey = selectedTask
    ? (!selectedTask.enabled ? "paused" : selectedStatus?.state || "idle")
    : "idle";
  const runAlert = getRunAlertMeta(selectedRun?.last_error || selectedStatus?.last_error);

  return {
    currentFile,
    diagnosticCounts,
    lastActivityAt,
    selectedStateKey,
    runAlert,
  };
}
