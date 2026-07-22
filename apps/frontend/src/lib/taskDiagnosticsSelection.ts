import type { SyncTaskOverview, SyncTaskRunSummary } from "../types";

const ACTION_RESULT_STATES = new Set(["failed", "cancelled"]);
const ACTIVE_FILE_STATUSES = new Set([
  "uploaded",
  "downloaded",
  "deleted",
  "delete_pending",
  "delete_failed",
  "failed",
  "conflict",
  "queued",
  "creating",
  "created",
  "reimporting",
]);

export function getTaskOverviewActionCount(overview: SyncTaskOverview): number {
  const counts = overview.counts;
  const status = overview.status;
  return (
    Math.max(counts.uploaded ?? 0, status.uploaded_files ?? 0) +
    Math.max(counts.downloaded ?? 0, status.downloaded_files ?? 0) +
    Math.max(counts.deleted ?? 0, status.deleted_files ?? 0) +
    Math.max(counts.delete_pending ?? 0, status.delete_pending_files ?? 0) +
    Math.max(counts.delete_failed ?? 0, status.delete_failed_files ?? 0) +
    Math.max(counts.failed ?? 0, status.failed_files ?? 0) +
    Math.max(counts.conflicts ?? 0, status.conflict_files ?? 0)
  );
}

export function hasFocusedTaskActivity(overview: SyncTaskOverview): boolean {
  if (overview.status.state === "running") return true;
  if ((overview.problem_count ?? 0) > 0) return true;
  if (getTaskOverviewActionCount(overview) > 0) return true;
  if (overview.last_result && ACTION_RESULT_STATES.has(overview.last_result)) return true;
  if (overview.status.last_error) return true;
  if (overview.current_file?.status && ACTIVE_FILE_STATUSES.has(overview.current_file.status)) return true;
  return false;
}

export function getFocusedTaskOverviews(sortedOverviews: SyncTaskOverview[]): SyncTaskOverview[] {
  return sortedOverviews.filter(hasFocusedTaskActivity);
}

export function resolveSelectedTaskId(
  sortedOverviews: SyncTaskOverview[],
  selectedTaskId: string | null,
): string | null {
  if (sortedOverviews.length === 0) return null;
  if (selectedTaskId && sortedOverviews.some((overview) => overview.task.id === selectedTaskId)) {
    return selectedTaskId;
  }
  return sortedOverviews[0]?.task.id ?? null;
}

export function filterTaskPickerOptions(
  sortedOverviews: SyncTaskOverview[],
  taskPickerQuery: string,
): SyncTaskOverview[] {
  const search = taskPickerQuery.trim().toLowerCase();
  if (!search) return sortedOverviews;
  return sortedOverviews.filter((overview) =>
    [overview.task.name, overview.task.local_path, overview.task.cloud_folder_name, overview.task.cloud_folder_token]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(search)),
  );
}

export function resolveActiveRunSelection(options: {
  recentRuns: SyncTaskRunSummary[];
  selectedRunId: string | null;
  diagnosticsSelectedRunId?: string | null;
}) {
  const latestActivityRun = options.recentRuns.find(hasRunActivity);
  const diagnosticsRun = options.recentRuns.find(
    (run) => run.run_id === options.diagnosticsSelectedRunId,
  );
  const activeRunId = options.selectedRunId && options.recentRuns.some((run) => run.run_id === options.selectedRunId)
    ? options.selectedRunId
    : (
      latestActivityRun?.run_id
      ?? (diagnosticsRun && hasRunActivity(diagnosticsRun) ? diagnosticsRun.run_id : null)
      ?? options.recentRuns[0]?.run_id
      ?? null
    );
  const activeRunSummary = options.recentRuns.find((run) => run.run_id === activeRunId) || null;
  return {
    activeRunId,
    activeRunSummary,
  };
}

export function hasRunActivity(run: SyncTaskRunSummary): boolean {
  if (run.state === "running" || run.state === "failed" || run.state === "cancelled") return true;
  if ((run.problem_count ?? 0) > 0) return true;
  const counts = run.counts;
  // Older/partial DTOs do not expose counts. Preserve their explicit server selection
  // instead of guessing that the run was empty.
  if (!counts) return true;
  return (
    (counts.uploaded ?? 0)
    + (counts.downloaded ?? 0)
    + (counts.deleted ?? 0)
    + (counts.failed ?? 0)
    + (counts.conflicts ?? 0)
    + (counts.delete_pending ?? 0)
    + (counts.delete_failed ?? 0)
  ) > 0;
}

export function getRunActivityTimestamp(run: SyncTaskRunSummary): number {
  return run.last_event_at ?? run.finished_at ?? run.started_at ?? 0;
}
