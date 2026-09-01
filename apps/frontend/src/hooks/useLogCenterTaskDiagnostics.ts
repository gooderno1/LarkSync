import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { computeTaskProgress } from "../lib/progress";
import { apiFetchForAccount } from "../lib/api";
import {
  buildTaskDiagnosticsQueryPath,
  shouldIncludeDiagnosticProblems,
  shouldPollTaskDiagnostics,
} from "../lib/taskDiagnosticsQuery";
import { resolveActiveRunSelection } from "../lib/taskDiagnosticsSelection";
import {
  deriveTaskDiagnosticsState,
  sortTaskOverviewsByActivity,
} from "../lib/taskDiagnosticsState";
import {
  mapSyncTaskDiagnostics,
  type SyncTaskDiagnosticsRaw,
} from "../lib/logCenter";
import type { SyncTaskDiagnostics, SyncTaskOverview } from "../types";
import { useTaskDiagnosticsSelection } from "./useTaskDiagnosticsSelection";
import { useTaskEventTimeline } from "./useTaskEventTimeline";
import { useAccounts } from "./useAccounts";

export type DetailTab = "overview" | "problems" | "events";

const EMPTY_OVERVIEWS: SyncTaskOverview[] = [];

export function useLogCenterTaskDiagnostics(enabled: boolean) {
  const { activeAccountId } = useAccounts();
  const accountId = activeAccountId || "";
  const [detailTab, setDetailTab] = useState<DetailTab>("overview");

  const overviewQuery = useQuery<SyncTaskOverview[]>({
    queryKey: ["sync-task-overview", accountId],
    queryFn: ({ signal }) => apiFetchForAccount<SyncTaskOverview[]>("/sync/tasks/overview", accountId, { signal }),
    enabled: enabled && Boolean(accountId),
    staleTime: 5_000,
    refetchInterval: enabled ? 10_000 : false,
  });

  const overviewItems = overviewQuery.data ?? EMPTY_OVERVIEWS;

  const sortedOverviews = useMemo(
    () => sortTaskOverviewsByActivity(overviewItems),
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
    showAllTasks,
    setShowAllTasks,
    hiddenTaskCount,
    focusedTaskCount,
    selectedOverview,
    taskPickerOptions,
    selectTask,
  } = useTaskDiagnosticsSelection({
    sortedOverviews,
  });
  const includeProblems = shouldIncludeDiagnosticProblems(detailTab);

  const diagnosticsQuery = useQuery<SyncTaskDiagnostics>({
    queryKey: ["sync-task-diagnostics", accountId, selectedTaskId, selectedRunId, includeProblems],
    queryFn: async ({ signal }) => {
      const raw = await apiFetchForAccount<SyncTaskDiagnosticsRaw>(buildTaskDiagnosticsQueryPath({
        selectedTaskId: selectedTaskId!,
        selectedRunId,
        includeProblems,
      }), accountId, { signal });
      return mapSyncTaskDiagnostics(raw);
    },
    enabled: enabled && Boolean(accountId) && Boolean(selectedTaskId),
    staleTime: 5_000,
    refetchInterval: shouldPollTaskDiagnostics({
      enabled,
      selectedTaskId,
      selectedTaskState: selectedOverview?.status.state ?? null,
    }),
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
    eventSince,
    eventUntil,
    setEventTimeRange,
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

  const progress = computeTaskProgress(selectedStatus);
  const {
    currentFile,
    diagnosticCounts,
    lastActivityAt,
    selectedStateKey,
    runAlert,
  } = deriveTaskDiagnosticsState({
    selectedTask,
    selectedStatus,
    selectedRun,
    activeOverview,
  });

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
    showAllTasks,
    setShowAllTasks,
    hiddenTaskCount,
    focusedTaskCount,
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
    eventSince,
    eventUntil,
    setEventTimeRange,
    selectTask,
    overviewQuery,
    sortedOverviews,
    selectedOverview,
    taskPickerOptions,
    diagnosticsQuery,
    activeOverview,
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
