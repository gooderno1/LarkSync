type DiagnosticsDetailTab = "overview" | "problems" | "events";

type BuildTaskDiagnosticsQueryPathOptions = {
  selectedTaskId: string;
  selectedRunId: string | null;
  includeProblems: boolean;
  limit?: number;
};

export function shouldIncludeDiagnosticProblems(detailTab: DiagnosticsDetailTab): boolean {
  return detailTab === "problems";
}

export function buildTaskDiagnosticsQueryPath({
  selectedTaskId,
  selectedRunId,
  includeProblems,
  limit = 200,
}: BuildTaskDiagnosticsQueryPathOptions): string {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("include_events", "false");
  params.set("include_problems", includeProblems ? "true" : "false");
  if (selectedRunId) params.set("run_id", selectedRunId);
  return `/sync/tasks/${selectedTaskId}/diagnostics?${params.toString()}`;
}

export function shouldPollTaskDiagnostics(options: {
  enabled: boolean;
  selectedTaskId: string | null;
  selectedTaskState?: string | null;
}): number | false {
  if (!options.enabled || !options.selectedTaskId) return false;
  return options.selectedTaskState === "running" ? 5_000 : 10_000;
}
