/* ------------------------------------------------------------------ */
/*  日志中心页面：任务诊断 + 系统日志 + 冲突管理                         */
/* ------------------------------------------------------------------ */

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useConflicts } from "../hooks/useConflicts";
import { useLogCenterTaskDiagnostics, type DetailTab } from "../hooks/useLogCenterTaskDiagnostics";
import { formatTimestamp, formatShortTime } from "../lib/formatters";
import { modeLabels, stateLabels, stateTones, statusLabelMap } from "../lib/constants";
import { apiFetch } from "../lib/api";
import {
  DANGER_STATUSES,
  EVENT_FILTERS,
  WARNING_STATUSES,
} from "../lib/eventFilters";
import {
  compactRunId,
  formatDuration,
  shortPath,
  statusTone,
  diagnosticActivityTime,
} from "../lib/logCenter";
import { StatusPill } from "../components/StatusPill";
import { Pagination } from "../components/Pagination";
import { IconRefresh, IconTasks, IconActivity } from "../components/Icons";
import { useToast } from "../components/ui/toast";
import { cn } from "../lib/utils";
import { ThemeToggle } from "../components/ThemeToggle";
import { SystemLogPanel } from "../components/log-center/SystemLogPanel";
import { ConflictManagementPanel } from "../components/log-center/ConflictManagementPanel";
import type {
  ConflictResolutionAction,
} from "../types";

type FileLogEntry = {
  timestamp: string;
  level: string;
  message: string;
};

type FileLogResponse = {
  total: number;
  items: FileLogEntry[];
};

type ConflictResolutionState = "queued" | "running" | "waiting" | "success" | "error";
type ConflictResolutionQueueItem = {
  id: string;
  action: ConflictResolutionAction;
  successMessage: string;
};
type ConflictResolutionStatus = {
  action: ConflictResolutionAction;
  state: ConflictResolutionState;
  message?: string | null;
  attempt?: number;
};

const CONFLICT_BUSY_RETRY_DELAY_MS = 5_000;
const CONFLICT_BUSY_RETRY_LIMIT = 24;
const CONFLICT_ACTION_LABELS: Record<ConflictResolutionAction, string> = {
  use_local: "使用本地",
  use_cloud: "使用云端",
};

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    globalThis.setTimeout(resolve, ms);
  });
}

function isTaskBusyConflictError(message?: string | null): boolean {
  const text = (message || "").trim();
  if (!text) return false;
  return (
    text.includes("任务运行中") ||
    text.includes("请稍后再试") ||
    text.includes("正在同步")
  );
}

export function LogCenterPage() {
  const [logTab, setLogTab] = useState<"tasks" | "file-logs" | "conflicts">("tasks");
  const { conflicts, conflictLoading, conflictError, refreshConflicts, resolveConflictAsync } = useConflicts(logTab === "conflicts");
  const { toast } = useToast();
  const taskPickerRef = useRef<HTMLDivElement | null>(null);
  const conflictQueueRef = useRef<ConflictResolutionQueueItem[]>([]);
  const conflictResolutionProcessingRef = useRef(false);
  const activeConflictResolutionIdRef = useRef<string | null>(null);

  const [fileLogLevel, setFileLogLevel] = useState("");
  const [fileLogSearch, setFileLogSearch] = useState("");
  const [fileLogPage, setFileLogPage] = useState(1);
  const [fileLogPageSize, setFileLogPageSize] = useState(50);
  const [fileLogOrder, setFileLogOrder] = useState<"asc" | "desc">("desc");
  const [conflictResolutionStates, setConflictResolutionStates] = useState<
    Record<string, ConflictResolutionStatus>
  >({});
  const {
    selectedTaskId,
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
    selectedTask,
    selectedStatus,
    taskPickerOptions,
    diagnosticsQuery,
    recentRuns,
    activeRunId,
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
  } = useLogCenterTaskDiagnostics(logTab === "tasks");

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (!taskPickerRef.current) return;
      if (!taskPickerRef.current.contains(event.target as Node)) {
        setTaskPickerOpen(false);
      }
    };
    window.addEventListener("mousedown", handlePointerDown);
    return () => window.removeEventListener("mousedown", handlePointerDown);
  }, [setTaskPickerOpen]);

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

  const resetFileLogPage = () => setFileLogPage(1);

  const processConflictResolutionQueue = async () => {
    if (conflictResolutionProcessingRef.current) {
      return;
    }
    conflictResolutionProcessingRef.current = true;
    try {
      while (conflictQueueRef.current.length > 0) {
        const [next, ...rest] = conflictQueueRef.current;
        conflictQueueRef.current = rest;
        activeConflictResolutionIdRef.current = next.id;
        const resolveWithRetry = async (attempt: number): Promise<void> => {
          setConflictResolutionStates((current) => ({
            ...current,
            [next.id]: {
              action: next.action,
              state: attempt === 0 ? "running" : "waiting",
              message:
                attempt === 0
                  ? "正在提交处理请求…"
                  : `目标任务仍在同步，${Math.ceil(CONFLICT_BUSY_RETRY_DELAY_MS / 1000)} 秒后自动重试（第 ${attempt + 1} 次）`,
              attempt,
            },
          }));
          if (attempt > 0) {
            await sleep(CONFLICT_BUSY_RETRY_DELAY_MS);
            setConflictResolutionStates((current) => ({
              ...current,
              [next.id]: {
                action: next.action,
                state: "running",
                message: `正在重试（第 ${attempt + 1} 次）…`,
                attempt,
              },
            }));
          }
          try {
            await resolveConflictAsync({ id: next.id, action: next.action });
            setConflictResolutionStates((current) => ({
              ...current,
              [next.id]: {
                action: next.action,
                state: "success",
                message: next.successMessage,
                attempt,
              },
            }));
            toast(next.successMessage, "success");
          } catch (err) {
            const message = err instanceof Error ? err.message : "冲突处理失败";
            if (isTaskBusyConflictError(message) && attempt < CONFLICT_BUSY_RETRY_LIMIT) {
              await resolveWithRetry(attempt + 1);
              return;
            }
            setConflictResolutionStates((current) => ({
              ...current,
              [next.id]: {
                action: next.action,
                state: "error",
                message,
                attempt,
              },
            }));
            toast(message, "danger");
          }
        };
        await resolveWithRetry(0);
      }
    } finally {
      activeConflictResolutionIdRef.current = null;
      conflictResolutionProcessingRef.current = false;
      if (conflictQueueRef.current.length > 0) {
        void processConflictResolutionQueue();
      }
    }
  };

  const handleResolveConflict = (
    id: string,
    action: ConflictResolutionAction,
    successMessage: string
  ) => {
    setConflictResolutionStates((current) => {
      if (current[id] && current[id].state !== "error") return current;
      return {
        ...current,
        [id]: { action, state: "queued", message: "已加入处理队列" },
      };
    });
    if (
      conflictQueueRef.current.some((item) => item.id === id) ||
      activeConflictResolutionIdRef.current === id
    ) {
      return;
    }
    const nextQueue = [...conflictQueueRef.current, { id, action, successMessage }];
    conflictQueueRef.current = nextQueue;
    void processConflictResolutionQueue();
  };

  const queuedConflictCount = useMemo(
    () => Object.values(conflictResolutionStates).filter((item) => item.state === "queued").length,
    [conflictResolutionStates]
  );
  const runningConflictCount = useMemo(
    () => Object.values(conflictResolutionStates).filter((item) => item.state === "running").length,
    [conflictResolutionStates]
  );
  const waitingConflictCount = useMemo(
    () => Object.values(conflictResolutionStates).filter((item) => item.state === "waiting").length,
    [conflictResolutionStates]
  );
  const successConflictCount = useMemo(
    () => Object.values(conflictResolutionStates).filter((item) => item.state === "success").length,
    [conflictResolutionStates]
  );
  const failedConflictCount = useMemo(
    () => Object.values(conflictResolutionStates).filter((item) => item.state === "error").length,
    [conflictResolutionStates]
  );

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
                                  selectTask(task.id);
                                  setTaskPickerOpen(false);
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
                {overviewQuery.isFetching || diagnosticsQuery.isFetching ? (
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
                <StatusPill label="最近 20 次" tone="info" />
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
                    {diagnosticsQuery.isLoading && recentRuns.length === 0 ? (
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
                            <span>删 {run.counts.deleted}</span>
                            <span>待删 {run.counts.delete_pending}</span>
                            <span>删失败 {run.counts.delete_failed}</span>
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
                    {diagnosticsQuery.isFetching ? <span className="ml-auto text-xs text-zinc-500">正在更新当前详情…</span> : null}
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
                            <StatusPill label={`删除 ${diagnosticCounts?.deleted ?? 0}`} tone="info" />
                            <StatusPill label={`待删除 ${diagnosticCounts?.delete_pending ?? 0}`} tone={(diagnosticCounts?.delete_pending ?? 0) > 0 ? "warning" : "success"} />
                            <StatusPill label={`删除失败 ${diagnosticCounts?.delete_failed ?? 0}`} tone={(diagnosticCounts?.delete_failed ?? 0) > 0 ? "danger" : "success"} />
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

                        {runAlert ? (
                          <div className={cn("rounded-xl border px-4 py-2.5 text-sm", runAlert.className)}>
                            {runAlert.label}：{runAlert.message}
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
                            <StatusPill label={diagnosticCounts?.deleted ? `删除 ${diagnosticCounts.deleted}` : "无删除"} tone={diagnosticCounts?.deleted ? "info" : "neutral"} />
                            <StatusPill label={diagnosticCounts?.delete_pending ? `待删除 ${diagnosticCounts.delete_pending}` : "无待删除"} tone={diagnosticCounts?.delete_pending ? "warning" : "success"} />
                            <StatusPill label={diagnosticCounts?.delete_failed ? `删除失败 ${diagnosticCounts.delete_failed}` : "无删除失败"} tone={diagnosticCounts?.delete_failed ? "danger" : "success"} />
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
                                  <StatusPill
                                    label={statusLabelMap[entry.status] || entry.status}
                                    tone={statusTone(entry.status, DANGER_STATUSES, WARNING_STATUSES)}
                                  />
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
        <SystemLogPanel
          query={fileLogsQuery}
          fileLogs={fileLogs}
          fileLogTotal={fileLogTotal}
          fileLogSearch={fileLogSearch}
          setFileLogSearch={setFileLogSearch}
          fileLogLevel={fileLogLevel}
          setFileLogLevel={setFileLogLevel}
          fileLogOrder={fileLogOrder}
          setFileLogOrder={setFileLogOrder}
          fileLogPage={fileLogPage}
          setFileLogPage={setFileLogPage}
          fileLogPageSize={fileLogPageSize}
          setFileLogPageSize={setFileLogPageSize}
          resetFileLogPage={resetFileLogPage}
        />
      ) : null}

      {logTab === "conflicts" ? (
        <ConflictManagementPanel
          conflicts={conflicts}
          conflictLoading={conflictLoading}
          conflictError={conflictError}
          refreshConflicts={refreshConflicts}
          queuedConflictCount={queuedConflictCount}
          runningConflictCount={runningConflictCount}
          waitingConflictCount={waitingConflictCount}
          successConflictCount={successConflictCount}
          failedConflictCount={failedConflictCount}
          conflictResolutionStates={conflictResolutionStates}
          onResolveConflict={handleResolveConflict}
          conflictActionLabels={CONFLICT_ACTION_LABELS}
        />
      ) : null}
    </section>
  );
}
