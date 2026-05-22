import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { computeTaskProgress } from "../lib/progress";
import { apiFetch } from "../lib/api";
import { resolveActiveRunSelection } from "../lib/taskDiagnosticsSelection";
import {
  mapSyncTaskDiagnostics,
  diagnosticActivityTime,
  type SyncTaskDiagnosticsRaw,
} from "../lib/logCenter";
import type { SyncTaskDiagnostics, SyncTaskOverview } from "../types";
import { useTaskDiagnosticsSelection } from "./useTaskDiagnosticsSelection";
import { useTaskEventTimeline } from "./useTaskEventTimeline";

export type DetailTab = "overview" | "problems" | "events";

const EMPTY_OVERVIEWS: SyncTaskOverview[] = [];

function getRunAlertMeta(message?: string | null): { label: string; className: string; message: string } | null {
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

export function useLogCenterTaskDiagnostics(enabled: boolean) {
  const [detailTab, setDetailTab] = useState<DetailTab>("overview");

  const overviewQuery = useQuery<SyncTaskOverview[]>({
    queryKey: ["sync-task-overview"],
    queryFn: () => apiFetch<SyncTaskOverview[]>("/sync/tasks/overview"),
    enabled,
    staleTime: 5_000,
    refetchInterval: enabled ? 10_000 : false,
    placeholderData: [],
  });

  const overviewItems = overviewQuery.data ?? EMPTY_OVERVIEWS;

  const sortedOverviews = useMemo(
    () => [...overviewItems].sort((a, b) => diagnosticActivityTime(b) - diagnosticActivityTime(a)),
    [overviewItems],
  );

  const {
    selectedTaskId,
    setSelectedTaskId,
    selectedRunId,
    setSelectedRunId,
    taskPickerQuery,
    setTaskPickerQuery,
    taskPickerOpen,
    setTaskPickerOpen,
    selectedOverview,
    taskPickerOptions,
    selectTask,
  } = useTaskDiagnosticsSelection({
    sortedOverviews,
  });

  const diagnosticsQuery = useQuery<SyncTaskDiagnostics>({
    queryKey: ["sync-task-diagnostics", selectedTaskId, selectedRunId, detailTab === "problems"],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("limit", "200");
      params.set("include_events", "false");
      params.set("include_problems", detailTab === "problems" ? "true" : "false");
      if (selectedRunId) params.set("run_id", selectedRunId);
      const raw = await apiFetch<SyncTaskDiagnosticsRaw>(`/sync/tasks/${selectedTaskId}/diagnostics?${params.toString()}`);
      return mapSyncTaskDiagnostics(raw);
    },
    enabled: enabled && Boolean(selectedTaskId),
    placeholderData: (previousData) => previousData,
    staleTime: 5_000,
    refetchInterval:
      enabled && selectedOverview?.status.state === "running"
        ? 5_000
        : enabled && Boolean(selectedTaskId)
          ? 10_000
          : false,
  });

  const activeOverview = diagnosticsQuery.data?.overview ?? selectedOverview;
  const selectedTask = activeOverview?.task ?? null;
  const selectedStatus = activeOverview?.status ?? null;
  const recentRuns = diagnosticsQuery.data?.recent_runs || [];
  const { activeRunId, activeRunSummary } = resolveActiveRunSelection({
    recentRuns,
    selectedRunId,
    diagnosticsSelectedRunId: diagnosticsQuery.data?.selected_run?.run_id ?? null,
  });
  const {
    eventFilter,
    setEventFilter,
    eventSearch,
    setEventSearch,
    eventPage,
    setEventPage,
    eventPageSize,
    setEventPageSize,
    selectedEventsQuery,
    selectedTimelineEntries,
    selectedTimelineTotal,
    resetEventPage,
  } = useTaskEventTimeline({
    enabled,
    detailTab,
    selectedTaskId,
    activeRunId,
    activeRunState: activeRunSummary?.state ?? null,
  });

  const selectedRun = diagnosticsQuery.data?.selected_run ?? activeRunSummary;
  const selectedProblems = diagnosticsQuery.data?.problems || [];

  useEffect(() => {
    setDetailTab("overview");
  }, [selectedTaskId]);

  const progress = computeTaskProgress(selectedStatus);
  const currentFile = selectedRun?.current_file ?? activeOverview?.current_file ?? null;
  const diagnosticCounts = selectedRun?.counts ?? activeOverview?.counts;
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

  const refreshDiagnostics = () => {
    overviewQuery.refetch();
    diagnosticsQuery.refetch();
    if (detailTab === "events") {
      selectedEventsQuery.refetch();
    }
  };

  return {
    selectedTaskId,
    setSelectedTaskId,
    selectedRunId,
    setSelectedRunId,
    taskPickerQuery,
    setTaskPickerQuery,
    taskPickerOpen,
    setTaskPickerOpen,
    detailTab,
    setDetailTab,
    eventFilter,
    setEventFilter,
    eventSearch,
    setEventSearch,
    eventPage,
    setEventPage,
    eventPageSize,
    setEventPageSize,
    selectTask,
    overviewQuery,
    sortedOverviews,
    selectedOverview,
    taskPickerOptions,
    diagnosticsQuery,
    selectedTask,
    selectedStatus,
    recentRuns,
    activeRunId,
    activeRunSummary,
    selectedEventsQuery,
    selectedRun,
    selectedTimelineEntries,
    selectedTimelineTotal,
    selectedProblems,
    progress,
    currentFile,
    diagnosticCounts,
    lastActivityAt,
    selectedStateKey,
    runAlert,
    resetEventPage,
    refreshDiagnostics,
  };
}
