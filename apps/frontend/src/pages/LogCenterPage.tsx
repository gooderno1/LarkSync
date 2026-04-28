/* ------------------------------------------------------------------ */
/*  日志中心页面：任务诊断 + 系统日志 + 冲突管理                         */
/* ------------------------------------------------------------------ */

import { useEffect, useMemo, useState } from "react";
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

type TaskViewFilter = "all" | "running" | "problem" | "disabled" | "recent";
type EventFilter = "all" | "problems" | "changes" | "skipped";

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

export function LogCenterPage() {
  const { conflicts, conflictLoading, conflictError, refreshConflicts, resolveConflict } = useConflicts();
  const { toast } = useToast();

  const [logTab, setLogTab] = useState<"tasks" | "file-logs" | "conflicts">("tasks");
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [taskSearch, setTaskSearch] = useState("");
  const [taskViewFilter, setTaskViewFilter] = useState<TaskViewFilter>("all");
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
    refetchInterval: logTab === "tasks" ? 5_000 : false,
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
      return;
    }
    if (!selectedTaskId || !sortedOverviews.some((overview) => overview.task.id === selectedTaskId)) {
      setSelectedTaskId(sortedOverviews[0].task.id);
    }
  }, [selectedTaskId, sortedOverviews]);

  const filteredOverviews = useMemo(() => {
    const search = taskSearch.trim().toLowerCase();
    return sortedOverviews.filter((overview) => {
      const { task, status } = overview;
      const hasProblem = Boolean(status.last_error) || overview.problem_count > 0;
      if (taskViewFilter === "running" && status?.state !== "running") return false;
      if (taskViewFilter === "problem" && !hasProblem) return false;
      if (taskViewFilter === "disabled" && task.enabled) return false;
      if (taskViewFilter === "recent" && !overview.last_event_at && !task.last_run_at && !status.started_at) return false;
      if (!search) return true;
      return [task.name, task.local_path, task.cloud_folder_name, task.cloud_folder_token]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(search));
    });
  }, [sortedOverviews, taskSearch, taskViewFilter]);

  const selectedOverview = sortedOverviews.find((overview) => overview.task.id === selectedTaskId) || null;

  const selectedDiagnosticsQuery = useQuery<SyncTaskDiagnostics>({
    queryKey: ["sync-task-diagnostics", selectedTaskId],
    queryFn: async () => {
      const raw = await apiFetch<SyncTaskDiagnosticsRaw>(`/sync/tasks/${selectedTaskId}/diagnostics?limit=800`);
      return mapSyncTaskDiagnostics(raw);
    },
    enabled: logTab === "tasks" && Boolean(selectedTaskId),
    staleTime: 5_000,
    refetchInterval: logTab === "tasks" ? 5_000 : false,
  });

  const selectedEventsQuery = useQuery<SyncLogResponse>({
    queryKey: ["sync-log-task-events", selectedTaskId, eventFilter, eventSearch, eventPage, eventPageSize],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("limit", String(eventPageSize));
      params.set("offset", String((eventPage - 1) * eventPageSize));
      params.set("order", "desc");
      if (selectedTaskId) params.append("task_ids", selectedTaskId);
      for (const status of buildStatusParams(eventFilter)) {
        params.append("statuses", status);
      }
      if (eventSearch.trim()) params.set("search", eventSearch.trim());
      const raw = await apiFetch<SyncLogResponseRaw>(`/sync/logs/sync?${params.toString()}`);
      return mapSyncLogResponse(raw);
    },
    enabled: logTab === "tasks" && Boolean(selectedTaskId),
    staleTime: 5_000,
    refetchInterval: logTab === "tasks" ? 5_000 : false,
    placeholderData: { total: 0, items: [] },
  });

  const activeOverview = selectedDiagnosticsQuery.data?.overview ?? selectedOverview;
  const selectedTask = activeOverview?.task ?? null;
  const selectedStatus = activeOverview?.status;
  const selectedSummaryEntries = selectedDiagnosticsQuery.data?.recent_events || [];
  const selectedTimelineEntries = selectedEventsQuery.data?.items || [];
  const selectedTimelineTotal = selectedEventsQuery.data?.total || 0;
  const selectedProblems = selectedDiagnosticsQuery.data?.problems || [];
  const actionCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const entry of selectedSummaryEntries) {
      counts[entry.status] = (counts[entry.status] ?? 0) + 1;
    }
    return counts;
  }, [selectedSummaryEntries]);

  const progress = computeTaskProgress(selectedStatus);
  const currentFile = activeOverview?.current_file ?? null;
  const diagnosticCounts = activeOverview?.counts;
  const lastActivityAt =
    selectedStatus?.finished_at ?? selectedStatus?.started_at ?? selectedTask?.last_run_at ?? activeOverview?.last_event_at ?? null;
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
    selectedDiagnosticsQuery.refetch();
    selectedEventsQuery.refetch();
  };

  return (
    <section className="space-y-6 animate-fade-up">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
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
        <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
          <aside className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-zinc-50">任务</h3>
                <p className="mt-1 text-xs text-zinc-500">按最近活动排序。</p>
              </div>
              <button
                className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-3 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
                onClick={refreshDiagnostics}
                type="button"
              >
                <IconRefresh className="h-3.5 w-3.5" /> 刷新
              </button>
            </div>
            <input
              className="mt-4 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
              placeholder="搜索任务名或路径"
              value={taskSearch}
              onChange={(event) => setTaskSearch(event.target.value)}
            />
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
              {[
                ["all", "全部"],
                ["running", "运行中"],
                ["problem", "有问题"],
                ["disabled", "已停用"],
                ["recent", "有活动"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  className={cn(
                    "rounded-lg border px-2.5 py-1.5 transition",
                    taskViewFilter === value
                      ? "border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]"
                      : "border-zinc-700 text-zinc-400 hover:bg-zinc-800"
                  )}
                  onClick={() => setTaskViewFilter(value as TaskViewFilter)}
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="mt-4 max-h-[660px] space-y-2 overflow-auto pr-1 log-scroll-area">
              {overviewQuery.isLoading ? (
                [1, 2, 3, 4].map((item) => <div key={item} className="h-24 animate-pulse rounded-xl bg-zinc-800/50" />)
              ) : filteredOverviews.length === 0 ? (
                <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 py-8 text-center">
                  <IconTasks className="mx-auto h-10 w-10 text-zinc-700" />
                  <p className="mt-3 text-sm text-zinc-500">暂无匹配任务。</p>
                </div>
              ) : (
                filteredOverviews.map((overview) => {
                  const { task, status } = overview;
                  const stateKey = !task.enabled ? "paused" : status?.state || "idle";
                  const hasProblem = Boolean(status?.last_error) || overview.problem_count > 0;
                  const activityTime = diagnosticActivityTime(overview);
                  return (
                    <button
                      key={task.id}
                      className={cn(
                        "w-full rounded-xl border p-3 text-left transition",
                        selectedTaskId === task.id
                          ? "border-[#3370FF]/50 bg-[#3370FF]/10"
                          : "border-zinc-800 bg-zinc-950/40 hover:border-zinc-700 hover:bg-zinc-900"
                      )}
                      onClick={() => {
                        setSelectedTaskId(task.id);
                        resetEventPage();
                      }}
                      type="button"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-zinc-100">{task.name || task.local_path}</p>
                          <p className="mt-1 truncate text-xs text-zinc-500">{shortPath(task.local_path, 44)}</p>
                        </div>
                        <StatusPill label={stateLabels[stateKey] || stateKey} tone={stateTones[stateKey] || "neutral"} />
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-zinc-500">
                        <span>{formatShortTime(activityTime)}</span>
                        <span className="text-zinc-700">|</span>
                        <span>{modeLabels[task.sync_mode] || task.sync_mode}</span>
                        {hasProblem ? (
                          <>
                            <span className="text-zinc-700">|</span>
                            <span className="text-rose-400">问题 {Math.max(overview.problem_count, 1)}</span>
                          </>
                        ) : null}
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </aside>

          <div className="space-y-5">
            {!selectedTask ? (
              <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 py-16 text-center">
                <IconTasks className="mx-auto h-12 w-12 text-zinc-700" />
                <p className="mt-4 text-sm text-zinc-500">请选择一个任务查看诊断详情。</p>
              </div>
            ) : (
              <>
                <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <div className="flex flex-wrap items-center gap-3">
                        <StatusPill label={stateLabels[selectedStateKey] || selectedStateKey} tone={stateTones[selectedStateKey] || "neutral"} dot={selectedStatus?.state === "running"} />
                        <h3 className="text-lg font-semibold text-zinc-50">{selectedTask.name || "未命名任务"}</h3>
                      </div>
                      <p className="mt-2 break-all text-xs text-zinc-500">{selectedTask.local_path}</p>
                      <p className="mt-1 break-all text-xs text-zinc-600">云端：{selectedTask.cloud_folder_name || selectedTask.cloud_folder_token}</p>
                      {selectedStatus?.current_run_id ? (
                        <p className="mt-1 break-all text-xs text-zinc-600">运行 ID：{selectedStatus.current_run_id}</p>
                      ) : null}
                    </div>
                    <button
                      className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
                      onClick={refreshDiagnostics}
                      type="button"
                    >
                      <IconRefresh className="h-3.5 w-3.5" /> 刷新诊断
                    </button>
                  </div>

                  <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
                      <p className="text-xs text-zinc-500">最近运行</p>
                      <p className="mt-2 text-sm font-semibold text-zinc-100">
                        {lastActivityAt ? formatTimestamp(lastActivityAt) : "暂无"}
                      </p>
                    </div>
                    <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
                      <p className="text-xs text-zinc-500">本次进度</p>
                      <p className="mt-2 text-sm font-semibold text-zinc-100">
                        {progress.progress === null ? "暂无运行数据" : `${progress.progress}%`}
                      </p>
                      {progress.progress !== null ? (
                        <p className="mt-1 text-xs text-zinc-500">已处理 {progress.processed}/{progress.effectiveTotal}</p>
                      ) : null}
                    </div>
                    <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
                      <p className="text-xs text-zinc-500">最近 800 条事件</p>
                      <p className="mt-2 text-sm font-semibold text-zinc-100">
                        上传 {diagnosticCounts?.uploaded ?? actionCounts.uploaded ?? 0} / 下载 {diagnosticCounts?.downloaded ?? actionCounts.downloaded ?? 0}
                      </p>
                      <p className="mt-1 text-xs text-zinc-500">
                        跳过 {diagnosticCounts?.skipped ?? actionCounts.skipped ?? 0}，失败 {diagnosticCounts?.failed ?? selectedProblems.length}
                      </p>
                    </div>
                    <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
                      <p className="text-xs text-zinc-500">当前处理</p>
                      <p className="mt-2 break-all text-xs font-medium text-zinc-200">
                        {currentFile ? shortPath(currentFile.path, 80) : selectedStatus?.state === "running" ? "等待下一条事件" : "当前未运行"}
                      </p>
                    </div>
                  </div>

                  {selectedStatus?.last_error ? (
                    <div className="mt-4 rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-200">
                      最近错误：{selectedStatus.last_error}
                    </div>
                  ) : null}
                </div>

                <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h3 className="text-base font-semibold text-zinc-50">问题摘要</h3>
                      <p className="mt-1 text-xs text-zinc-500">优先显示失败、冲突、删除失败和取消事件。</p>
                    </div>
                    <StatusPill label={`${selectedProblems.length} 条`} tone={selectedProblems.length ? "danger" : "success"} />
                  </div>
                  <div className="mt-4 space-y-2">
                    {selectedProblems.length === 0 ? (
                      <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 px-4 py-5 text-center text-sm text-zinc-500">
                        最近未发现问题事件。
                      </div>
                    ) : (
                      selectedProblems.slice(0, 6).map((entry, index) => (
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
                </div>

                <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h3 className="text-base font-semibold text-zinc-50">任务事件时间线</h3>
                      <p className="mt-1 text-xs text-zinc-500">只显示当前选中任务的同步事件。</p>
                    </div>
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
                  </div>
                  <input
                    className="mt-4 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
                    placeholder="搜索当前任务的文件路径或错误信息"
                    value={eventSearch}
                    onChange={(event) => {
                      setEventSearch(event.target.value);
                      resetEventPage();
                    }}
                  />
                  <div className="mt-4 max-h-[520px] space-y-3 overflow-auto pr-1 log-scroll-area">
                    {selectedEventsQuery.isLoading ? (
                      [1, 2, 3, 4].map((item) => <div key={item} className="h-16 animate-pulse rounded-xl bg-zinc-800/50" />)
                    ) : selectedTimelineEntries.length === 0 ? (
                      <div className="py-8 text-center">
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
                    <div className="mt-4 border-t border-zinc-800 pt-4">
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
              </>
            )}
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
