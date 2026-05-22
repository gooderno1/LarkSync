import type { SyncTaskOverview, SyncTaskRunSummary } from "../types";

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
  const activeRunId = options.selectedRunId && options.recentRuns.some((run) => run.run_id === options.selectedRunId)
    ? options.selectedRunId
    : (options.diagnosticsSelectedRunId ?? options.recentRuns[0]?.run_id ?? null);
  const activeRunSummary = options.recentRuns.find((run) => run.run_id === activeRunId) || null;
  return {
    activeRunId,
    activeRunSummary,
  };
}
