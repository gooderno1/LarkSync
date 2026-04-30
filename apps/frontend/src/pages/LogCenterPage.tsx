/* ------------------------------------------------------------------ */
/*  日志中心页面：任务诊断 + 系统日志 + 冲突管理                         */
/* ------------------------------------------------------------------ */

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useConflicts } from "../hooks/useConflicts";
import { formatTimestamp, formatShortTime } from "../lib/formatters";
import { modeLabels, stateLabels, stateTones, statusLabelMap } from "../lib/constants";
import { computeTaskProgress } from "../lib/progress";
import { apiFetch } from "../lib/api";
import { StatusPill } from "../components/StatusPill";
import { Pagination } from "../components/Pagination";
import { IconRefresh, IconConflicts, IconCopy, IconTasks, IconActivity } from "../components/Icons";
import { useToast } from "../components/ui/toast";
import { cn } from "../lib/utils";
import { ThemeToggle } from "../components/ThemeToggle";
import type { SyncLogEntry, SyncTaskDiagnostics, SyncTaskOverview, Tone } from "../types";

type FileLogEntry = {
  timestamp: string;
  level: string;
  message: string;
};

type FileLogResponse = {
  total: number;
  items: FileLogEntry[];
};

type SyncLogResponse = {
  total: number;
  items: SyncLogEntry[];
  warning?: string | null;
  meta?: {
    file_size_bytes?: number;
    retention_days?: number;
    warn_size_mb?: number;
  } | null;
};

type SyncLogEntryRaw = {
  task_id: string;
  task_name: string;
  timestamp: number;
  status: string;
  path: string;
  message?: string | null;
  run_id?: string | null;
};

type SyncLogResponseRaw = {
  total: number;
  items: SyncLogEntryRaw[];
  warning?: string | null;
  meta?: {
    file_size_bytes?: number;
    retention_days?: number;
    warn_size_mb?: number;
  } | null;
};

type SyncTaskDiagnosticsRaw = Omit<SyncTaskDiagnostics, "recent_events" | "problems"> & {
  recent_events: SyncLogEntryRaw[];
  problems: SyncLogEntryRaw[];
};

type EventFilter = "all" | "problems" | "changes" | "skipped";
type DetailTab = "overview" | "problems" | "events";

const PROBLEM_STATUSES = new Set(["failed", "delete_failed", "conflict", "cancelled"]);
const WARNING_STATUSES = new Set(["skipped", "delete_pending", "cancelled", "queued"]);
const DANGER_STATUSES = new Set(["failed", "delete_failed", "conflict"]);
const CHANGE_STATUSES = new Set(["uploaded", "downloaded", "deleted", "mirrored", "delete_pending", "conflict"]);

const EVENT_FILTERS: Array<{ value: EventFilter; label: string }> = [
  { value: "all", label: "全部事件" },
  { value: "problems", label: "问题优先" },
  { value: "changes", label: "实际变更" },
  { value: "skipped", label: "跳过记录" },
];

function mapSyncLogEntry(item: SyncLogEntryRaw): SyncLogEntry {
  return {
    taskId: item.task_id,
    taskName: item.task_name,
    timestamp: item.timestamp,
    status: item.status,
    path: item.path,
    message: item.message ?? null,
    runId: item.run_id ?? null,
  };
}

function mapSyncLogResponse(raw: SyncLogResponseRaw): SyncLogResponse {
  return {
    total: raw.total,
    items: raw.items.map(mapSyncLogEntry),
    warning: raw.warning ?? null,
    meta: raw.meta ?? null,
  };
}

function mapSyncTaskDiagnostics(raw: SyncTaskDiagnosticsRaw): SyncTaskDiagnostics {
  return {
    overview: raw.overview,
    selected_run: raw.selected_run ?? null,
    recent_runs: raw.recent_runs ?? [],
    recent_events: raw.recent_events.map(mapSyncLogEntry),
    problems: raw.problems.map(mapSyncLogEntry),
  };
}

function statusTone(status: string): Tone {
  if (DANGER_STATUSES.has(status)) return "danger";
  if (WARNING_STATUSES.has(status)) return "warning";
  if (status === "started" || status === "queued") return "info";
  return "success";
}

function levelColor(level: string) {
  switch (level) {
    case "ERROR": return "text-rose-400";
    case "WARNING": return "text-amber-400";
    case "INFO": return "text-zinc-400";
    case "DEBUG": return "text-zinc-600";
    default: return "text-zinc-400";
  }
}

function shortPath(value: string, maxChars = 72): string {
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

function diagnosticActivityTime(overview: SyncTaskOverview): number {
  return (
    overview.last_event_at ??
    overview.status.finished_at ??
    overview.status.started_at ??
    overview.task.last_run_at ??
    overview.task.updated_at ??
    overview.task.created_at
  );
}

function buildStatusParams(filter: EventFilter): string[] {
  if (filter === "problems") return [...PROBLEM_STATUSES];
  if (filter === "changes") return [...CHANGE_STATUSES];
  if (filter === "skipped") return ["skipped"];
  return [];
}

function formatDuration(startedAt?: number | null, finishedAt?: number | null, fallbackAt?: number | null): string {
  if (!startedAt) return "暂无";
  const end = finishedAt ?? fallbackAt;
  if (!end || end <= startedAt) return "进行中";
  const totalSeconds = Math.max(1, Math.round((end - startedAt) / 1000));
  if (totalSeconds < 60) return `${totalSeconds} 秒`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes < 60) return seconds ? `${minutes} 分 ${seconds} 秒` : `${minutes} 分`;
  const hours = Math.floor(minutes / 60);
  const remainMinutes = minutes % 60;
  return remainMinutes ? `${hours} 小时 ${remainMinutes} 分` : `${hours} 小时`;
}

function compactRunId(runId?: string | null): string {
  if (!runId) return "暂无";
  if (runId.length <= 18) return runId;
  return `${runId.slice(0, 8)}...${runId.slice(-6)}`;
}

export function LogCenterPage() {
  const { conflicts, conflictLoading, conflictError, refreshConflicts, resolveConflict } = useConflicts();
  const { toast } = useToast();
  const taskPickerRef = useRef<HTMLDivElement | null>(null);

  const [logTab, setLogTab] = useState<"tasks" | "file-logs" | "conflicts">("tasks");
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [resolvedDiagnostics, setResolvedDiagnostics] = useState<SyncTaskDiagnostics | null>(null);
  const [taskPickerQuery, setTaskPickerQuery] = useState("");
  const [taskPickerOpen, setTaskPickerOpen] = useState(false);
  const [detailTab, setDetailTab] = useState<DetailTab>("events");
  const [eventFilter, setEventFilter] = useState<EventFilter>("all");
  const [eventSearch, setEventSearch] = useState("");
  const [eventPage, setEventPage] = useState(1);
  const [eventPageSize, setEventPageSize] = useState(30);

  const [fileLogLevel, setFileLogLevel] = useState("");
  const [fileLogSearch, setFileLogSearch] = useState("");
  const [fileLogPage, setFileLogPage] = useState(1);
  const [fileLogPageSize, setFileLogPageSize] = useState(50);
  const [fileLogOrder, setFileLogOrder] = useState<"asc" | "desc">("desc");

  const overviewQuery = useQuery<SyncTaskOverview[]>({
    queryKey: ["sync-task-overview"],
    queryFn: () => apiFetch<SyncTaskOverview[]>("/sync/tasks/overview"),
    enabled: logTab === "tasks",
    staleTime: 5_000,
    refetchInterval: logTab === "tasks" ? 10_000 : false,
    placeholderData: [],
  });

  const overviewItems = overviewQuery.data || [];

  const sortedOverviews = useMemo(
    () => [...overviewItems].sort((a, b) => diagnosticActivityTime(b) - diagnosticActivityTime(a)),
    [overviewItems]
  );

  useEffect(() => {
    if (sortedOverviews.length === 0) {
      setSelectedTaskId(null);
      setSelectedRunId(null);
      setActiveTaskId(null);
      setResolvedDiagnostics(null);
      return;
    }
    if (!selectedTaskId || !sortedOverviews.some((overview) => overview.task.id === selectedTaskId)) {
      setSelectedTaskId(sortedOverviews[0].task.id);
    }
  }, [selectedTaskId, sortedOverviews]);

  const filteredOverviews = useMemo(() => {
    const search = taskPickerQuery.trim().toLowerCase();
    if (!search) return sortedOverviews;
    return sortedOverviews.filter((overview) =>
      [overview.task.name, overview.task.local_path, overview.task.cloud_folder_name, overview.task.cloud_folder_token]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(search))
    );
  }, [sortedOverviews, taskPickerQuery]);

  const selectedOverview = sortedOverviews.find((overview) => overview.task.id === selectedTaskId) || null;
  const activeOverviewFallback = sortedOverviews.find((overview) => overview.task.id === activeTaskId) || null;
  const taskPickerOptions = filteredOverviews;

  const taskDiagnosticsQuery = useQuery<SyncTaskDiagnostics>({
    queryKey: ["sync-task-diagnostics-base", selectedTaskId],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("limit", "200");
      const raw = await apiFetch<SyncTaskDiagnosticsRaw>(`/sync/tasks/${selectedTaskId}/diagnostics?${params.toString()}`);
      return mapSyncTaskDiagnostics(raw);
    },
    enabled: logTab === "tasks" && Boolean(selectedTaskId),
    staleTime: 5_000,
    refetchInterval:
      logTab === "tasks" && selectedOverview?.status.state === "running"
        ? 5_000
        : logTab === "tasks" && Boolean(selectedTaskId)
          ? 10_000
          : false,
  });

  useEffect(() => {
    if (!selectedTaskId || !taskDiagnosticsQuery.data) {
      return;
    }
    const runs = taskDiagnosticsQuery.data.recent_runs || [];
    setResolvedDiagnostics(taskDiagnosticsQuery.data);
    setActiveTaskId(selectedTaskId);
    setSelectedRunId((current) => {
      if (current && runs.some((run) => run.run_id === current)) return current;
      return runs[0]?.run_id ?? null;
    });
  }, [selectedTaskId, taskDiagnosticsQuery.data]);

  const activeOverview = resolvedDiagnostics?.overview ?? activeOverviewFallback ?? selectedOverview;
  const selectedTask = activeOverview?.task ?? null;
  const selectedStatus = activeOverview?.status ?? null;
  const recentRuns = resolvedDiagnostics?.recent_runs || [];
  const activeRunId = selectedRunId && recentRuns.some((run) => run.run_id === selectedRunId)
    ? selectedRunId
    : recentRuns[0]?.run_id ?? null;
  const activeRunSummary = recentRuns.find((run) => run.run_id === activeRunId) || null;
  const taskSwitching = Boolean(selectedTaskId && activeTaskId && selectedTaskId !== activeTaskId);

  const selectedRunQuery = useQuery<SyncTaskDiagnostics>({
    queryKey: ["sync-task-diagnostics-run", activeTaskId, activeRunId],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("limit", "800");
      if (activeRunId) params.set("run_id", activeRunId);
      const raw = await apiFetch<SyncTaskDiagnosticsRaw>(`/sync/tasks/${activeTaskId}/diagnostics?${params.toString()}`);
      return mapSyncTaskDiagnostics(raw);
    },
    enabled: logTab === "tasks" && Boolean(activeTaskId) && Boolean(activeRunId),
    staleTime: 5_000,
    refetchInterval:
      logTab === "tasks" && !taskSwitching && activeRunSummary?.state === "running"
        ? 5_000
        : false,
    placeholderData: (previousData) => previousData,
  });

  const selectedEventsQuery = useQuery<SyncLogResponse>({
    queryKey: ["sync-log-task-events", activeTaskId, activeRunId, eventFilter, eventSearch, eventPage, eventPageSize],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("limit", String(eventPageSize));
      params.set("offset", String((eventPage - 1) * eventPageSize));
      params.set("order", "desc");
      if (activeTaskId) params.append("task_ids", activeTaskId);
      if (activeRunId) params.append("run_ids", activeRunId);
      for (const status of buildStatusParams(eventFilter)) {
        params.append("statuses", status);
      }
      if (eventSearch.trim()) params.set("search", eventSearch.trim());
      const raw = await apiFetch<SyncLogResponseRaw>(`/sync/logs/sync?${params.toString()}`);
      return mapSyncLogResponse(raw);
    },
    enabled: logTab === "tasks" && Boolean(activeTaskId) && Boolean(activeRunId),
    staleTime: 5_000,
    refetchInterval:
      logTab === "tasks" && !taskSwitching && activeRunSummary?.state === "running"
        ? 5_000
        : false,
    placeholderData: { total: 0, items: [] },
  });

  const selectedRun = selectedRunQuery.data?.selected_run ?? activeRunSummary;
  const selectedTimelineEntries = selectedEventsQuery.data?.items || [];
  const selectedTimelineTotal = selectedEventsQuery.data?.total || 0;
  const selectedProblems = selectedRunQuery.data?.problems || [];

  useEffect(() => {
    setEventPage(1);
  }, [activeRunId]);

  useEffect(() => {
    if (!taskPickerOpen) {
      setTaskPickerQuery("");
    }
  }, [taskPickerOpen]);

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (!taskPickerRef.current) return;
      if (!taskPickerRef.current.contains(event.target as Node)) {
        setTaskPickerOpen(false);
      }
    };
    window.addEventListener("mousedown", handlePointerDown);
    return () => window.removeEventListener("mousedown", handlePointerDown);
  }, []);

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

  const fileLogsQuery = useQuery<FileLogResponse>({
    queryKey: ["file-logs", fileLogLevel, fileLogSearch, fileLogOrder, fileLogPage, fileLogPageSize],
    queryFn: () => {
      const params = new URLSearchParams();
      params.set("limit", String(fileLogPageSize));
      params.set("offset", String((fileLogPage - 1) * fileLogPageSize));
      if (fileLogLevel) params.set("level", fileLogLevel);
      if (fileLogSearch) params.set("search", fileLogSearch);
      params.set("order", fileLogOrder);
      return apiFetch<FileLogResponse>(`/sync/logs/file?${params.toString()}`);
    },
    enabled: logTab === "file-logs",
    staleTime: 5_000,
    refetchInterval: logTab === "file-logs" ? 5_000 : false,
    refetchOnWindowFocus: logTab === "file-logs",
    placeholderData: { total: 0, items: [] },
  });

  const fileLogs = fileLogsQuery.data?.items || [];
  const fileLogTotal = fileLogsQuery.data?.total || 0;

  const resetEventPage = () => setEventPage(1);
  const resetFileLogPage = () => setFileLogPage(1);

  const refreshDiagnostics = () => {
    overviewQuery.refetch();
    taskDiagnosticsQuery.refetch();
    selectedRunQuery.refetch();
    selectedEventsQuery.refetch();
  };

  return (
    <section
      className={cn(
        "animate-fade-up",
        logTab === "tasks"
          ? "flex min-h-0 flex-col gap-6 lg:h-[calc(100vh-2.5rem)]"
          : "space-y-6"
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-50">日志中心</h2>
          <p className="mt-1 text-xs text-zinc-400">按任务查看当前同步情况、问题事件与系统日志。</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            className={cn("rounded-lg border px-4 py-2 text-xs font-medium transition", logTab === "tasks" ? "border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]" : "border-zinc-700 text-zinc-300 hover:bg-zinc-800")}
            onClick={() => setLogTab("tasks")}
            type="button"
          >
            任务诊断
          </button>
          <button
            className={cn("rounded-lg border px-4 py-2 text-xs font-medium transition", logTab === "file-logs" ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-zinc-700 text-zinc-300 hover:bg-zinc-800")}
            onClick={() => setLogTab("file-logs")}
            type="button"
          >
            系统日志
          </button>
          <button
            className={cn("rounded-lg border px-4 py-2 text-xs font-medium transition", logTab === "conflicts" ? "border-amber-500/40 bg-amber-500/10 text-amber-300" : "border-zinc-700 text-zinc-300 hover:bg-zinc-800")}
            onClick={() => setLogTab("conflicts")}
            type="button"
          >
            冲突管理 {conflicts.filter((c) => !c.resolved).length > 0 ? `(${conflicts.filter((c) => !c.resolved).length})` : ""}
          </button>
          <ThemeToggle />
        </div>
      </div>

      {logTab === "tasks" ? (
        <div className="grid min-h-0 flex-1 gap-5 xl:grid-rows-[auto_minmax(0,1fr)]">
          <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-3.5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-zinc-50">任务选择</h3>
              </div>
              <div className="flex items-center gap-2">
                {selectedTask ? (
                  <StatusPill
                    label={stateLabels[selectedStateKey] || selectedStateKey}
                    tone={stateTones[selectedStateKey] || "neutral"}
                    dot={selectedStatus?.state === "running"}
                  />
                ) : null}
                <button
                  className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-3 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
                  onClick={refreshDiagnostics}
                  type="button"
                >
                  <IconRefresh className="h-3.5 w-3.5" /> 刷新
                </button>
              </div>
            </div>

            <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(420px,1fr)_minmax(0,1fr)_auto]">
              <div className="space-y-1.5" ref={taskPickerRef}>
                <label className="text-[11px] text-zinc-500">当前任务</label>
                <div className="relative">
                  <button
                    className="flex w-full items-center justify-between rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-left text-sm text-zinc-200 outline-none transition hover:border-zinc-600"
                    onClick={() => setTaskPickerOpen((value) => !value)}
                    type="button"
                  >
                    <span className="truncate">{selectedTask?.name || "请选择任务"}</span>
                    <span className="text-xs text-zinc-500">{taskPickerOpen ? "收起" : "选择"}</span>
                  </button>
                  {taskPickerOpen ? (
                    <div className="absolute left-0 right-0 top-[calc(100%+8px)] z-20 rounded-xl border border-zinc-800 bg-zinc-950 p-2 shadow-xl">
                      <input
                        autoFocus
                        className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
                        placeholder="搜索任务名"
                        value={taskPickerQuery}
                        onChange={(event) => setTaskPickerQuery(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Escape") setTaskPickerOpen(false);
                        }}
                      />
                      <div className="mt-2 max-h-64 space-y-1 overflow-y-auto pr-1 log-scroll-area">
                        {taskPickerOptions.length === 0 ? (
                          <div className="rounded-lg px-3 py-5 text-center text-xs text-zinc-500">没有匹配的任务</div>
                        ) : (
                          taskPickerOptions.map((overview) => {
                            const task = overview.task;
                            const stateKey = !task.enabled ? "paused" : overview.status?.state || "idle";
                            return (
                              <button
                                key={task.id}
                                className={cn(
                                  "w-full rounded-lg border px-3 py-2 text-left transition",
                                  selectedTaskId === task.id
                                    ? "border-[#3370FF]/50 bg-[#3370FF]/10"
                                    : "border-zinc-800 bg-zinc-900/60 hover:border-zinc-700 hover:bg-zinc-900"
                                )}
                                onClick={() => {
                                  setSelectedTaskId(task.id);
                                  setTaskPickerOpen(false);
                                  resetEventPage();
                                }}
                                type="button"
                              >
                                <div className="flex items-center justify-between gap-3">
                                  <span className="truncate text-sm font-medium text-zinc-100">{task.name || "未命名任务"}</span>
                                  <StatusPill label={stateLabels[stateKey] || stateKey} tone={stateTones[stateKey] || "neutral"} />
                                </div>
                                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-zinc-500">
                                  <span>{modeLabels[task.sync_mode] || task.sync_mode}</span>
                                  <span>{formatShortTime(diagnosticActivityTime(overview))}</span>
                                </div>
                              </button>
                            );
                          })
                        )}
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] text-zinc-500">当前任务信息</label>
                <div className="flex min-h-[40px] flex-wrap items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-950/40 px-3 py-2 text-[11px] text-zinc-500">
                  {selectedTask ? (
                    <>
                      <span>{modeLabels[selectedTask.sync_mode] || selectedTask.sync_mode}</span>
                      {lastActivityAt ? (
                        <>
                          <span className="text-zinc-700">|</span>
                          <span>最近活动 {formatShortTime(lastActivityAt)}</span>
                        </>
                      ) : null}
                      <span className="text-zinc-700">|</span>
                      <span className="truncate">{shortPath(selectedTask.local_path, 84)}</span>
                    </>
                  ) : (
                    <span>暂无任务</span>
                  )}
                </div>
              </div>

              <div className="flex items-end justify-end text-[11px] text-zinc-500">
                {overviewQuery.isFetching || taskDiagnosticsQuery.isFetching ? (
                  <span className="shrink-0">正在刷新…</span>
                ) : null}
              </div>
            </div>
          </section>

          <div className="grid min-h-[560px] gap-4 xl:min-h-0 xl:grid-cols-[minmax(340px,0.82fr)_minmax(0,1.18fr)]">
            <section className="flex min-h-0 flex-col rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-base font-semibold text-zinc-50">运行记录</h3>
                </div>
                <div className="flex items-center gap-2">
                  {taskSwitching ? (
                    <span className="text-xs text-zinc-500">正在切换到新任务…</span>
                  ) : null}
                  <StatusPill label="最近 20 次" tone="info" />
                </div>
              </div>

              {!selectedTask ? (
                <div className="flex flex-1 items-center justify-center text-center">
                  <div>
                    <IconTasks className="mx-auto h-10 w-10 text-zinc-700" />
                    <p className="mt-3 text-sm text-zinc-500">请选择一个任务查看运行记录。</p>
                  </div>
                </div>
              ) : (
                <>
                  <div className="mt-4 flex-1 min-h-0 space-y-2 overflow-y-auto pr-1 log-scroll-area">
                    {taskDiagnosticsQuery.isLoading && recentRuns.length === 0 ? (
                      [1, 2, 3].map((item) => <div key={item} className="h-24 animate-pulse rounded-xl bg-zinc-800/50" />)
                    ) : recentRuns.length === 0 ? (
                      <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 px-4 py-5 text-center text-sm text-zinc-500">
                        暂无运行记录。
                      </div>
                    ) : (
                      recentRuns.map((run) => (
                        <button
                          key={run.run_id}
                          className={cn(
                            "w-full rounded-xl border px-3 py-2 text-left transition",
                            activeRunId === run.run_id
                              ? "border-[#3370FF]/50 bg-[#3370FF]/10"
                              : "border-zinc-800 bg-zinc-950/40 hover:border-zinc-700 hover:bg-zinc-900"
                          )}
                          onClick={() => {
                            setSelectedRunId(run.run_id);
                            resetEventPage();
                          }}
                          type="button"
                        >
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="truncate text-sm font-semibold text-zinc-100">{compactRunId(run.run_id)}</p>
                              <p className="mt-1 text-[11px] text-zinc-500">
                                {run.started_at ? formatTimestamp(run.started_at) : "开始时间未知"}
                              </p>
                            </div>
                            <StatusPill
                              label={stateLabels[run.state] || run.state}
                              tone={stateTones[run.state] || "neutral"}
                              dot={run.state === "running"}
                            />
                          </div>
                          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-zinc-500">
                            <span>上 {run.counts.uploaded}</span>
                            <span>下 {run.counts.downloaded}</span>
                            <span>失败 {run.counts.failed}</span>
                            <span>冲突 {run.counts.conflicts}</span>
                            <span>耗时 {formatDuration(run.started_at, run.finished_at, run.last_event_at)}</span>
                          </div>
                          {run.last_error ? (
                            <p className="mt-1.5 truncate text-[11px] text-rose-300">{run.last_error}</p>
                          ) : null}
                        </button>
                      ))
                    )}
                  </div>
                </>
              )}
            </section>

            <section className="flex min-h-0 flex-col rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
              {!selectedTask ? (
                <div className="flex flex-1 items-center justify-center text-center">
                  <div>
                    <IconActivity className="mx-auto h-10 w-10 text-zinc-700" />
                    <p className="mt-3 text-sm text-zinc-500">请选择一个任务查看运行详情。</p>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-3">
                        <StatusPill
                          label={stateLabels[selectedRun?.state || selectedStateKey] || selectedRun?.state || selectedStateKey}
                          tone={stateTones[selectedRun?.state || selectedStateKey] || "neutral"}
                          dot={selectedRun?.state === "running"}
                        />
                        <h3 className="truncate text-base font-semibold text-zinc-50">
                          {selectedTask.name || "未命名任务"}
                        </h3>
                        {lastActivityAt ? <span className="text-[11px] text-zinc-500">最近活动 {formatTimestamp(lastActivityAt)}</span> : null}
                      </div>
                      <p className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-zinc-500">
                        <span>运行 {compactRunId(selectedRun?.run_id || activeRunId || selectedStatus?.current_run_id || null)}</span>
                        <span>{shortPath(selectedTask.local_path, 92)}</span>
                      </p>
                    </div>
                    <button
                      className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
                      onClick={refreshDiagnostics}
                      type="button"
                    >
                      <IconRefresh className="h-3.5 w-3.5" /> 刷新诊断
                    </button>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    {[
                      ["overview", "概览"],
                      ["problems", "问题"],
                      ["events", "事件"],
                    ].map(([value, label]) => (
                      <button
                        key={value}
                        className={cn(
                          "rounded-lg border px-3 py-1.5 text-xs transition",
                          detailTab === value
                            ? "border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]"
                            : "border-zinc-700 text-zinc-400 hover:bg-zinc-800"
                        )}
                        onClick={() => setDetailTab(value as DetailTab)}
                        type="button"
                      >
                        {label}
                      </button>
                    ))}
                    {taskSwitching ? <span className="ml-auto text-xs text-zinc-500">正在更新当前详情…</span> : null}
                  </div>

                  <div className="mt-4 flex-1 min-h-0 overflow-y-auto pr-1 log-scroll-area">
                    {detailTab === "overview" ? (
                      <div className="space-y-4">
                        <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 px-4 py-3">
                          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] text-zinc-400">
                            <span>开始 {selectedRun?.started_at ? formatTimestamp(selectedRun.started_at) : "暂无"}</span>
                            <span>耗时 {formatDuration(selectedRun?.started_at, selectedRun?.finished_at, selectedRun?.last_event_at)}</span>
                            <span>进度 {progress.progress === null ? "暂无" : `${progress.progress}%`}</span>
                            <span>阶段 {selectedRun?.state === "running" ? "同步进行中" : "本轮已结束"}</span>
                          </div>
                          <div className="mt-2.5 flex flex-wrap gap-2">
                            <StatusPill label={`上传 ${diagnosticCounts?.uploaded ?? 0}`} tone="info" />
                            <StatusPill label={`下载 ${diagnosticCounts?.downloaded ?? 0}`} tone="info" />
                            <StatusPill label={`跳过 ${diagnosticCounts?.skipped ?? 0}`} tone="warning" />
                            <StatusPill label={`失败 ${diagnosticCounts?.failed ?? 0}`} tone={(diagnosticCounts?.failed ?? 0) > 0 ? "danger" : "success"} />
                            <StatusPill label={`冲突 ${diagnosticCounts?.conflicts ?? 0}`} tone={(diagnosticCounts?.conflicts ?? 0) > 0 ? "warning" : "success"} />
                            <StatusPill label={`总数 ${diagnosticCounts?.total ?? 0}`} tone="neutral" />
                          </div>
                          {currentFile ? (
                            <div className="mt-2 space-y-1">
                              <p className="truncate text-[11px] text-zinc-500">当前处理：{shortPath(currentFile.path, 110)}</p>
                              {currentFile.message ? (
                                <p className="truncate text-[11px] text-zinc-600">{currentFile.message}</p>
                              ) : null}
                            </div>
                          ) : null}
                        </div>

                        {(selectedRun?.last_error || selectedStatus?.last_error) ? (
                          <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-2.5 text-sm text-rose-200">
                            最近错误：{selectedRun?.last_error || selectedStatus?.last_error}
                          </div>
                        ) : null}

                        <div className="grid gap-3 lg:grid-cols-2">
                          <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-4">
                            <p className="text-xs text-zinc-500">同步目标</p>
                            <p className="mt-2 text-[11px] text-zinc-500">本地目录</p>
                            <p className="mt-1 break-all text-sm text-zinc-200">{shortPath(selectedTask.local_path, 120)}</p>
                            <p className="mt-3 text-[11px] text-zinc-500">云端目录</p>
                            <p className="mt-1 break-all text-sm text-zinc-200">
                              {selectedTask.cloud_folder_name || selectedTask.cloud_folder_token || "未配置"}
                            </p>
                          </div>
                          <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-4">
                            <p className="text-xs text-zinc-500">最近活动</p>
                            <p className="mt-2 text-sm font-semibold text-zinc-100">
                              {lastActivityAt ? formatTimestamp(lastActivityAt) : "暂无"}
                            </p>
                            <p className="mt-2 text-xs text-zinc-500">
                              云端：{selectedTask.cloud_folder_name || selectedTask.cloud_folder_token}
                            </p>
                          </div>
                        </div>
                        <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-4">
                          <p className="text-xs text-zinc-500">运行判断</p>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <StatusPill label={diagnosticCounts?.failed ? `失败 ${diagnosticCounts.failed}` : "无失败"} tone={diagnosticCounts?.failed ? "danger" : "success"} />
                            <StatusPill label={diagnosticCounts?.conflicts ? `冲突 ${diagnosticCounts.conflicts}` : "无冲突"} tone={diagnosticCounts?.conflicts ? "warning" : "success"} />
                            <StatusPill label={diagnosticCounts?.skipped ? `跳过 ${diagnosticCounts.skipped}` : "无跳过"} tone={diagnosticCounts?.skipped ? "warning" : "success"} />
                            <StatusPill label={selectedStatus?.state === "running" ? "同步进行中" : "本轮已结束"} tone={selectedStatus?.state === "running" ? "info" : "neutral"} />
                          </div>
                        </div>
                      </div>
                    ) : null}

                    {detailTab === "problems" ? (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-xs text-zinc-500">只显示当前运行的失败、冲突、删除失败和取消事件。</p>
                          <StatusPill label={`${selectedProblems.length} 条`} tone={selectedProblems.length ? "danger" : "success"} />
                        </div>
                        {selectedProblems.length === 0 ? (
                          <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 px-4 py-6 text-center text-sm text-zinc-500">
                            最近未发现问题事件。
                          </div>
                        ) : (
                          selectedProblems.map((entry, index) => (
                            <div key={`${entry.timestamp}-${index}`} className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-3">
                              <div className="flex flex-wrap items-center justify-between gap-3">
                                <p className="text-xs text-zinc-500">
                                  {formatTimestamp(entry.timestamp)}
                                  {entry.runId ? <span className="ml-2 text-zinc-700">运行 {entry.runId}</span> : null}
                                </p>
                                <StatusPill label={statusLabelMap[entry.status] || entry.status} tone="danger" />
                              </div>
                              <p className="mt-2 break-all text-xs text-zinc-300">{entry.path}</p>
                              {entry.message ? <p className="mt-1 text-xs text-rose-300">{entry.message}</p> : null}
                            </div>
                          ))
                        )}
                      </div>
                    ) : null}

                    {detailTab === "events" ? (
                      <div className="space-y-4">
                        <div className="flex flex-wrap items-center gap-2">
                          {EVENT_FILTERS.map((filter) => (
                            <button
                              key={filter.value}
                              className={cn(
                                "rounded-lg border px-3 py-1.5 text-xs transition",
                                eventFilter === filter.value
                                  ? "border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]"
                                  : "border-zinc-700 text-zinc-400 hover:bg-zinc-800"
                              )}
                              onClick={() => {
                                setEventFilter(filter.value);
                                resetEventPage();
                              }}
                              type="button"
                            >
                              {filter.label}
                            </button>
                          ))}
                        </div>
                        <input
                          className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
                          placeholder="搜索当前运行的文件路径或错误信息"
                          value={eventSearch}
                          onChange={(event) => {
                            setEventSearch(event.target.value);
                            resetEventPage();
                          }}
                        />
                        <div className="space-y-3">
                          {selectedEventsQuery.isLoading && selectedTimelineEntries.length === 0 ? (
                            [1, 2, 3, 4].map((item) => <div key={item} className="h-16 animate-pulse rounded-xl bg-zinc-800/50" />)
                          ) : selectedTimelineEntries.length === 0 ? (
                            <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 py-8 text-center">
                              <IconActivity className="mx-auto h-10 w-10 text-zinc-700" />
                              <p className="mt-3 text-sm text-zinc-500">暂无匹配事件。</p>
                            </div>
                          ) : (
                            selectedTimelineEntries.map((entry, index) => (
                              <div key={`${entry.timestamp}-${index}`} className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
                                <div className="flex flex-wrap items-start justify-between gap-3">
                                  <div className="min-w-0 space-y-1">
                                    <p className="text-xs text-zinc-500">{formatTimestamp(entry.timestamp)}</p>
                                    {entry.runId ? <p className="text-[11px] text-zinc-700">运行 {entry.runId}</p> : null}
                                    <p className="break-all text-xs text-zinc-400">{entry.path}</p>
                                  </div>
                                  <StatusPill label={statusLabelMap[entry.status] || entry.status} tone={statusTone(entry.status)} />
                                </div>
                                {entry.message ? <p className="mt-2 text-xs text-zinc-600">{entry.message}</p> : null}
                              </div>
                            ))
                          )}
                        </div>
                        {(selectedTimelineTotal > 0 || selectedTimelineEntries.length > 0) ? (
                          <div className="border-t border-zinc-800 pt-4">
                            <Pagination
                              page={eventPage}
                              pageSize={eventPageSize}
                              total={selectedTimelineTotal}
                              onPageChange={setEventPage}
                              onPageSizeChange={(size) => {
                                setEventPageSize(size);
                                resetEventPage();
                              }}
                              pageSizeOptions={[20, 30, 50, 100]}
                            />
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                </>
              )}
            </section>
          </div>
        </div>
      ) : null}

      {logTab === "file-logs" ? (
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-zinc-50">系统日志</h3>
              <p className="mt-1 text-xs text-zinc-400">来自 loguru 日志文件，适合查看底层异常和 API 调用错误。</p>
            </div>
            <button className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800" onClick={() => fileLogsQuery.refetch()} type="button">
              <IconRefresh className="h-3.5 w-3.5" /> 刷新
            </button>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-[1.2fr_0.5fr_0.6fr_0.6fr]">
            <input
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
              placeholder="搜索日志内容（如 error、token、频率限制）"
              value={fileLogSearch}
              onChange={(e) => { setFileLogSearch(e.target.value); resetFileLogPage(); }}
            />
            <select
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-200 outline-none"
              value={fileLogOrder}
              onChange={(e) => { setFileLogOrder(e.target.value as "asc" | "desc"); resetFileLogPage(); }}
            >
              <option value="desc">最新优先</option>
              <option value="asc">最早优先</option>
            </select>
            <select
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-200 outline-none"
              value={fileLogLevel}
              onChange={(e) => { setFileLogLevel(e.target.value); resetFileLogPage(); }}
            >
              <option value="">全部级别</option>
              <option value="ERROR">ERROR</option>
              <option value="WARNING">WARNING</option>
              <option value="INFO">INFO</option>
            </select>
            <button className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-800" onClick={() => { setFileLogLevel(""); setFileLogSearch(""); setFileLogOrder("desc"); resetFileLogPage(); }} type="button">
              重置
            </button>
          </div>

          {fileLogsQuery.error ? (
            <div className="mt-4 rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-xs text-rose-200">
              系统日志加载失败：{fileLogsQuery.error.message}
            </div>
          ) : null}
          <div className="mt-5 max-h-[620px] space-y-2 overflow-auto pr-1 log-scroll-area">
            {fileLogsQuery.isLoading ? (
              [1, 2, 3, 4, 5].map((item) => <div key={item} className="h-10 animate-pulse rounded-lg bg-zinc-800/50" />)
            ) : fileLogs.length === 0 ? (
              <div className="py-8 text-center">
                <IconConflicts className="mx-auto h-10 w-10 text-zinc-700" />
                <p className="mt-3 text-sm text-zinc-500">暂无匹配的系统日志。</p>
              </div>
            ) : (
              fileLogs.map((entry, i) => (
                <div key={`${entry.timestamp}-${i}`} className="rounded-lg border border-zinc-800 bg-zinc-950/50 px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="shrink-0 text-[11px] font-mono text-zinc-500">{entry.timestamp}</span>
                    <span className={cn("shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold", levelColor(entry.level),
                      entry.level === "ERROR" ? "bg-rose-500/15" : entry.level === "WARNING" ? "bg-amber-500/15" : "bg-zinc-800/50"
                    )}>
                      {entry.level}
                    </span>
                  </div>
                  <p className="mt-1 whitespace-pre-wrap break-all font-mono text-xs text-zinc-300">{entry.message}</p>
                </div>
              ))
            )}
          </div>

          {(fileLogTotal > 0 || fileLogs.length > 0) ? (
            <div className="mt-4 border-t border-zinc-800 pt-4">
              <Pagination
                page={fileLogPage}
                pageSize={fileLogPageSize}
                total={fileLogTotal}
                onPageChange={setFileLogPage}
                onPageSizeChange={(size) => { setFileLogPageSize(size); resetFileLogPage(); }}
                pageSizeOptions={[20, 50, 100, 200]}
              />
            </div>
          ) : null}
        </div>
      ) : null}

      {logTab === "conflicts" ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
            <div>
              <h3 className="text-lg font-semibold text-zinc-50">冲突管理</h3>
              <p className="mt-1 text-xs text-zinc-400">处理云端与本地同时修改产生的冲突。</p>
            </div>
            <button className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800" onClick={refreshConflicts} disabled={conflictLoading} type="button">
              <IconRefresh className="h-3.5 w-3.5" /> {conflictLoading ? "加载中..." : "刷新"}
            </button>
          </div>
          {conflictError ? <p className="text-sm text-rose-400">加载失败：{conflictError}</p> : null}
          {conflicts.length === 0 ? (
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 py-16 text-center">
              <IconConflicts className="mx-auto h-12 w-12 text-zinc-700" />
              <p className="mt-4 text-sm text-zinc-500">暂无冲突记录。</p>
            </div>
          ) : (
            conflicts.map((c) => (
              <div key={c.id} className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="space-y-1">
                    <p className="text-xs uppercase tracking-widest text-zinc-500">本地路径</p>
                    <p className="text-sm text-zinc-200">{c.local_path}</p>
                    <p className="text-xs text-zinc-500">云端 token：{c.cloud_token}</p>
                    <p className="text-xs text-zinc-600">哈希：{c.local_hash.slice(0, 8)} / {c.db_hash.slice(0, 8)}</p>
                  </div>
                  <StatusPill label={c.resolved ? "已处理" : "待处理"} tone={c.resolved ? "success" : "warning"} />
                </div>
                <div className="mt-4 grid gap-4 lg:grid-cols-2">
                  <div>
                    <p className="text-xs uppercase tracking-widest text-zinc-500">本地版本</p>
                    <pre className="mt-2 max-h-56 overflow-auto rounded-lg border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs text-zinc-300">
                      {c.local_preview || "暂无本地预览。"}
                    </pre>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-widest text-zinc-500">云端版本</p>
                    <pre className="mt-2 max-h-56 overflow-auto rounded-lg border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs text-zinc-300">
                      {c.cloud_preview || "暂无云端预览。"}
                    </pre>
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-3">
                  <button
                    className="rounded-lg bg-emerald-500/20 px-4 py-2 text-xs font-semibold text-emerald-300 transition hover:bg-emerald-500/30 disabled:opacity-50"
                    disabled={c.resolved}
                    onClick={() => { resolveConflict({ id: c.id, action: "use_local" }); toast("已采用本地版本", "success"); }}
                    type="button"
                  >
                    使用本地
                  </button>
                  <button
                    className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 transition hover:bg-zinc-800 disabled:opacity-50"
                    disabled={c.resolved}
                    onClick={() => { resolveConflict({ id: c.id, action: "use_cloud" }); toast("已采用云端版本", "success"); }}
                    type="button"
                  >
                    使用云端
                  </button>
                  <button
                    className="rounded-lg border border-[#3370FF]/40 bg-[#3370FF]/10 px-4 py-2 text-xs font-medium text-[#3370FF] transition hover:bg-[#3370FF]/20 disabled:opacity-50"
                    disabled={c.resolved}
                    onClick={() => { resolveConflict({ id: c.id, action: "keep_both" }); toast("已保留双方版本", "info"); }}
                    type="button"
                  >
                    <span className="inline-flex items-center gap-1.5"><IconCopy className="h-3 w-3" />保留双方</span>
                  </button>
                  {c.resolved ? (
                    <span className="self-center text-xs text-zinc-500">已处理：{c.resolved_action}</span>
                  ) : null}
                </div>
              </div>
            ))
          )}
        </div>
      ) : null}
    </section>
  );
}
