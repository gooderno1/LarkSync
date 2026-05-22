import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { computeTaskProgress } from "../lib/progress";
import { apiFetch } from "../lib/api";
import { buildStatusParams, type EventFilter } from "../lib/eventFilters";
import {
  mapSyncLogResponse,
  mapSyncTaskDiagnostics,
  diagnosticActivityTime,
  type SyncLogResponse,
  type SyncLogResponseRaw,
  type SyncTaskDiagnosticsRaw,
} from "../lib/logCenter";
import type { SyncTaskDiagnostics, SyncTaskOverview } from "../types";

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
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [taskPickerQuery, setTaskPickerQuery] = useState("");
  const [taskPickerOpen, setTaskPickerOpen] = useState(false);
  const [detailTab, setDetailTab] = useState<DetailTab>("overview");
  const [eventFilter, setEventFilter] = useState<EventFilter>("all");
  const [eventSearch, setEventSearch] = useState("");
  const [eventPage, setEventPage] = useState(1);
  const [eventPageSize, setEventPageSize] = useState(30);

  const selectTask = (taskId: string) => {
    setSelectedTaskId(taskId);
    setDetailTab("overview");
    setEventPage(1);
  };

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

  useEffect(() => {
    if (sortedOverviews.length === 0) {
      setSelectedTaskId(null);
      setSelectedRunId(null);
      setDetailTab("overview");
      return;
    }
    if (!selectedTaskId || !sortedOverviews.some((overview) => overview.task.id === selectedTaskId)) {
      setSelectedTaskId(sortedOverviews[0].task.id);
      setDetailTab("overview");
      setEventPage(1);
    }
  }, [selectedTaskId, sortedOverviews]);

  const filteredOverviews = useMemo(() => {
    const search = taskPickerQuery.trim().toLowerCase();
    if (!search) return sortedOverviews;
    return sortedOverviews.filter((overview) =>
      [overview.task.name, overview.task.local_path, overview.task.cloud_folder_name, overview.task.cloud_folder_token]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(search)),
    );
  }, [sortedOverviews, taskPickerQuery]);

  const selectedOverview = sortedOverviews.find((overview) => overview.task.id === selectedTaskId) || null;
  const taskPickerOptions = filteredOverviews;

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
  const activeRunId = selectedRunId && recentRuns.some((run) => run.run_id === selectedRunId)
    ? selectedRunId
    : (diagnosticsQuery.data?.selected_run?.run_id ?? recentRuns[0]?.run_id ?? null);
  const activeRunSummary = recentRuns.find((run) => run.run_id === activeRunId) || null;

  const selectedEventsQuery = useQuery<SyncLogResponse>({
    queryKey: ["sync-log-task-events", selectedTaskId, activeRunId, detailTab, eventFilter, eventSearch, eventPage, eventPageSize],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("limit", String(eventPageSize));
      params.set("offset", String((eventPage - 1) * eventPageSize));
      params.set("order", "desc");
      if (selectedTaskId) params.append("task_ids", selectedTaskId);
      if (activeRunId) params.append("run_ids", activeRunId);
      for (const status of buildStatusParams(eventFilter)) {
        params.append("statuses", status);
      }
      if (eventSearch.trim()) params.set("search", eventSearch.trim());
      const raw = await apiFetch<SyncLogResponseRaw>(`/sync/logs/sync?${params.toString()}`);
      return mapSyncLogResponse(raw);
    },
    enabled: enabled && detailTab === "events" && Boolean(selectedTaskId) && Boolean(activeRunId),
    placeholderData: (previousData) => previousData ?? { total: 0, items: [] },
    staleTime: 5_000,
    refetchInterval:
      enabled && detailTab === "events" && activeRunSummary?.state === "running"
        ? 5_000
        : false,
  });

  const selectedRun = diagnosticsQuery.data?.selected_run ?? activeRunSummary;
  const selectedTimelineEntries = selectedEventsQuery.data?.items || [];
  const selectedTimelineTotal = selectedEventsQuery.data?.total || 0;
  const selectedProblems = diagnosticsQuery.data?.problems || [];

  useEffect(() => {
    setEventPage(1);
  }, [activeRunId]);

  useEffect(() => {
    if (!taskPickerOpen) {
      setTaskPickerQuery("");
    }
  }, [taskPickerOpen]);

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

  const resetEventPage = () => setEventPage(1);

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
