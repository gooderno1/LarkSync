import type { SyncLogEntry, SyncTaskDiagnostics, SyncTaskOverview, Tone } from "../types";

export type SyncLogResponse = {
  total: number;
  items: SyncLogEntry[];
  warning?: string | null;
  meta?: {
    file_size_bytes?: number;
    retention_days?: number;
    warn_size_mb?: number;
  } | null;
};

export type SyncLogEntryRaw = {
  event_id?: string | null;
  task_id: string;
  task_name: string;
  timestamp: number;
  status: string;
  path: string;
  message?: string | null;
  run_id?: string | null;
};

export type SyncLogResponseRaw = {
  total: number;
  items: SyncLogEntryRaw[];
  warning?: string | null;
  meta?: {
    file_size_bytes?: number;
    retention_days?: number;
    warn_size_mb?: number;
  } | null;
};

export type SyncTaskDiagnosticsRaw = Omit<SyncTaskDiagnostics, "recent_events" | "problems"> & {
  recent_events: SyncLogEntryRaw[];
  problems: SyncLogEntryRaw[];
};

export function mapSyncLogEntry(item: SyncLogEntryRaw): SyncLogEntry {
  return {
    eventId: item.event_id ?? null,
    taskId: item.task_id,
    taskName: item.task_name,
    timestamp: item.timestamp,
    status: item.status,
    path: item.path,
    message: item.message ?? null,
    runId: item.run_id ?? null,
  };
}

export function mapSyncLogResponse(raw: SyncLogResponseRaw): SyncLogResponse {
  return {
    total: raw.total,
    items: raw.items.map(mapSyncLogEntry),
    warning: raw.warning ?? null,
    meta: raw.meta ?? null,
  };
}

export function mapSyncTaskDiagnostics(raw: SyncTaskDiagnosticsRaw): SyncTaskDiagnostics {
  return {
    overview: raw.overview,
    selected_run: raw.selected_run ?? null,
    recent_runs: raw.recent_runs ?? [],
    recent_events: raw.recent_events.map(mapSyncLogEntry),
    problems: raw.problems.map(mapSyncLogEntry),
  };
}

export function statusTone(
  status: string,
  dangerStatuses: ReadonlySet<string>,
  warningStatuses: ReadonlySet<string>,
): Tone {
  if (dangerStatuses.has(status)) return "danger";
  if (warningStatuses.has(status)) return "warning";
  if (status === "started" || status === "queued") return "info";
  return "success";
}

export function shortPath(value: string, maxChars = 72): string {
  const text = value.trim();
  if (!text) return "-";
  if (text.length <= maxChars) return text;
  const segments = text.split(/[\\/]+/).filter(Boolean);
  if (segments.length >= 4) {
    const tail = segments.slice(-4).join("/");
    return tail.length <= maxChars ? `.../${tail}` : `...${text.slice(-maxChars)}`;
  }
  return `...${text.slice(-maxChars)}`;
}

export function diagnosticActivityTime(overview: SyncTaskOverview): number {
  return (
    overview.last_event_at ??
    overview.status.finished_at ??
    overview.status.started_at ??
    overview.task.last_run_at ??
    overview.task.updated_at ??
    overview.task.created_at
  );
}

export function formatDuration(
  startedAt?: number | null,
  finishedAt?: number | null,
  fallbackAt?: number | null,
): string {
  if (!startedAt) return "暂无";
  const end = finishedAt ?? fallbackAt;
  if (!end || end <= startedAt) return "进行中";
  const totalSeconds = Math.max(1, Math.round(end - startedAt));
  if (totalSeconds < 60) return `${totalSeconds} 秒`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes < 60) return seconds ? `${minutes} 分 ${seconds} 秒` : `${minutes} 分`;
  const hours = Math.floor(minutes / 60);
  const remainMinutes = minutes % 60;
  return `${hours} 小时 ${remainMinutes} 分`;
}

export function compactRunId(runId?: string | null): string {
  if (!runId) return "暂无";
  if (runId.length <= 18) return runId;
  return `${runId.slice(0, 8)}...${runId.slice(-6)}`;
}
