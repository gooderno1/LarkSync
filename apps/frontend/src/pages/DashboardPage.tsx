/* ------------------------------------------------------------------ */
/*  仪表盘页面                                                          */
/* ------------------------------------------------------------------ */

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../hooks/useAuth";
import { useTasks } from "../hooks/useTasks";
import { useConflicts } from "../hooks/useConflicts";
import { useWebSocketLog } from "../hooks/useWebSocketLog";
import { apiFetch } from "../lib/api";
import { formatTimestamp, formatShortTime, isSameDay } from "../lib/formatters";
import { shortPath } from "../lib/logCenter";
import { modeLabels, updateModeLabels, stateLabels, stateTones, statusLabelMap } from "../lib/constants";
import { computeTaskProgress } from "../lib/progress";
import { StatCard } from "../components/StatCard";
import { StatusPill } from "../components/StatusPill";
import { ModeIcon, IconRefresh, IconTasks, IconArrowRightLeft, IconConflicts, IconActivity } from "../components/Icons";
import type { SyncLogEntry, NavKey, SyncTask, SyncTaskStatus, Tone } from "../types";

type SyncLogResponse = {
  total: number;
  items: SyncLogEntry[];
};

type SyncLogEntryRaw = {
  task_id: string;
  task_name: string;
  timestamp: number;
  status: string;
  path: string;
  message?: string | null;
};

type SyncLogResponseRaw = {
  total: number;
  items: SyncLogEntryRaw[];
};

type Props = { onNavigate: (tab: NavKey) => void };

const FAILURE_STATUSES = new Set(["failed", "delete_failed", "cancelled"]);
const CONFLICT_STATUSES = new Set(["conflict"]);
const ATTENTION_STATUSES = new Set([...FAILURE_STATUSES, ...CONFLICT_STATUSES]);
const DELETE_PENDING_STATUSES = new Set(["delete_pending"]);
const QUEUED_SYNC_STATUSES = new Set(["queued", "creating", "created", "reimporting"]);
const SUCCESS_STATUSES = new Set(["success", "uploaded", "downloaded", "mirrored", "deleted", "linked", "bootstrapped"]);

function getStatusActivityTime(status?: SyncTaskStatus | null): number | null {
  return status?.finished_at ?? status?.started_at ?? null;
}

function getTaskActivityTime(
  task: SyncTask,
  status: SyncTaskStatus | undefined,
  latestLogTime?: number
): number {
  return (
    getStatusActivityTime(status) ??
    task.last_run_at ??
    latestLogTime ??
    task.updated_at ??
    task.created_at
  );
}

function getDashboardEventTone(status: string): Tone {
  if (FAILURE_STATUSES.has(status)) return "danger";
  if (CONFLICT_STATUSES.has(status) || DELETE_PENDING_STATUSES.has(status)) return "warning";
  if (QUEUED_SYNC_STATUSES.has(status)) return "info";
  if (SUCCESS_STATUSES.has(status)) return "success";
  return "neutral";
}

function getDashboardEventHint(entry: SyncLogEntry): string | null {
  if (entry.status === "delete_pending") {
    return "安全删除宽限队列，到期后自动执行；如非预期，请在源端恢复文件或调整删除策略。";
  }
  if (entry.status === "delete_failed") {
    return "删除动作失败，需要检查权限、文件占用或路径状态。";
  }
  if (entry.status === "conflict") {
    return "本地与云端同时变化，需要到事件管理中选择保留版本。";
  }
  return null;
}

function getTaskPendingHint(status?: SyncTaskStatus): string | null {
  if (!status) return null;
  const parts: string[] = [];
  if (status.delete_pending_files > 0) parts.push(`待删除 ${status.delete_pending_files}：安全宽限队列，到期后自动执行`);
  if (status.delete_failed_files > 0) parts.push(`删除失败 ${status.delete_failed_files}：检查权限、占用或路径状态`);
  if (status.failed_files > 0) parts.push(`失败 ${status.failed_files}：查看错误信息后重试`);
  if (status.conflict_files > 0) parts.push(`冲突 ${status.conflict_files}：到事件管理选择保留版本`);
  return parts.length > 0 ? parts.join("；") : null;
}

export function DashboardPage({ onNavigate }: Props) {
  const { connected } = useAuth();
  const { tasks, taskLoading, statusMap, refreshTasks, refreshStatus } = useTasks();
  const { conflicts } = useConflicts();
  const { entries: wsEntries, status: wsStatus } = useWebSocketLog(connected);


  const syncLogsQuery = useQuery<SyncLogResponse>({
    queryKey: ["sync-logs-dashboard"],
    queryFn: async () => {
      const raw = await apiFetch<SyncLogResponseRaw>("/sync/logs/sync?limit=200&order=desc");
      return {
        total: raw.total,
        items: raw.items.map((item) => ({
          taskId: item.task_id,
          taskName: item.task_name,
          timestamp: item.timestamp,
          status: item.status,
          path: item.path,
          message: item.message ?? null,
        })),
      };
    },
    staleTime: 5_000,
  });
  const historyEntries = syncLogsQuery.data?.items || [];

  // Merge polling logs with WebSocket real-time entries
  const pollingEntries: SyncLogEntry[] = useMemo(() => {
    return Object.values(statusMap)
      .flatMap((st) =>
        (st.last_files || []).map((f) => ({
          taskId: st.task_id,
          taskName: tasks.find((t) => t.id === st.task_id)?.name || "未命名任务",
          timestamp: f.timestamp ?? st.finished_at ?? st.started_at ?? Math.floor(Date.now() / 1000),
          status: f.status,
          path: f.path,
          message: f.message,
        }))
      )
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, 200);
  }, [statusMap, tasks]);

  // Prefer WS entries when available, fallback to polling
  const baseEntries = historyEntries.length > 0 ? historyEntries : pollingEntries;
  const syncLogEntries = wsEntries.length > 0 ? wsEntries : baseEntries;
  const latestLogTimeByTask = useMemo(() => {
    const mapped: Record<string, number> = {};
    for (const entry of syncLogEntries) {
      mapped[entry.taskId] = Math.max(mapped[entry.taskId] ?? 0, entry.timestamp);
    }
    return mapped;
  }, [syncLogEntries]);

  const today = new Date();
  const enabledTasks = tasks.filter((t) => t.enabled).length;
  const runningTasks = tasks.filter((t) => statusMap[t.id]?.state === "running").length;
  const unresolvedConflicts = conflicts.filter((c) => !c.resolved).length;
  const todayEventCount = syncLogEntries.filter((e) => isSameDay(e.timestamp, today)).length;
  const failedEventCount = syncLogEntries.filter((e) => FAILURE_STATUSES.has(e.status)).length;
  const conflictEventCount = syncLogEntries.filter((e) => CONFLICT_STATUSES.has(e.status)).length;
  const deletePendingCount = syncLogEntries.filter((e) => DELETE_PENDING_STATUSES.has(e.status)).length;
  const queuedSyncCount = syncLogEntries.filter((e) => QUEUED_SYNC_STATUSES.has(e.status)).length;
  const pendingEventCount = deletePendingCount + queuedSyncCount;
  const attentionCount = failedEventCount + conflictEventCount + unresolvedConflicts;
  const lastSuccess = syncLogEntries.find((e) => SUCCESS_STATUSES.has(e.status));
  const healthTone: Tone =
    failedEventCount > 0 ? "danger" :
      unresolvedConflicts > 0 || conflictEventCount > 0 || pendingEventCount > 0 ? "warning" :
        runningTasks > 0 ? "info" :
          enabledTasks > 0 ? "success" : "neutral";
  const healthLabel =
    failedEventCount > 0 ? "有失败" :
      unresolvedConflicts > 0 || conflictEventCount > 0 ? "有冲突" :
        deletePendingCount > 0 ? "待删除" :
          queuedSyncCount > 0 ? "有队列" :
          runningTasks > 0 ? "同步中" :
            enabledTasks > 0 ? "已一致" : "未启用";
  const healthHint =
    failedEventCount > 0 ? `${failedEventCount} 条失败或取消事件需要排查` :
      unresolvedConflicts > 0 || conflictEventCount > 0 ? `${unresolvedConflicts + conflictEventCount} 个冲突需要处理` :
        deletePendingCount > 0 ? `待删除 ${deletePendingCount} 项，处于安全宽限队列` :
          queuedSyncCount > 0 ? `队列中 ${queuedSyncCount} 项等待执行` :
          runningTasks > 0 ? `正在同步 ${runningTasks} 个任务` :
            enabledTasks > 0 ? "暂无待处理问题" : "请先启用同步任务";
  const attentionEntries = syncLogEntries.filter((entry) => ATTENTION_STATUSES.has(entry.status));
  const deletePendingEntries = syncLogEntries.filter((entry) => DELETE_PENDING_STATUSES.has(entry.status));
  const queuedEntries = syncLogEntries.filter((entry) => QUEUED_SYNC_STATUSES.has(entry.status));
  const focusEntries = attentionEntries.length > 0 ? attentionEntries : deletePendingEntries.length > 0 ? deletePendingEntries : queuedEntries;
  const runningTaskList = useMemo(
    () => tasks.filter((task) => statusMap[task.id]?.state === "running"),
    [tasks, statusMap]
  );
  const recentTaskList = useMemo(
    () =>
      [...tasks]
        .filter((task) => statusMap[task.id]?.state !== "running")
        .sort(
          (a, b) =>
            getTaskActivityTime(b, statusMap[b.id], latestLogTimeByTask[b.id]) -
            getTaskActivityTime(a, statusMap[a.id], latestLogTimeByTask[a.id])
        )
        .slice(0, runningTaskList.length > 0 ? 2 : 3),
    [tasks, statusMap, latestLogTimeByTask, runningTaskList.length]
  );

  const renderTaskCard = (task: SyncTask) => {
    const st = statusMap[task.id];
    const stateKey = !task.enabled ? "paused" : st?.state || "idle";
    const progressState = computeTaskProgress(st);
    const progress = progressState.progress;
    const activityTime = getTaskActivityTime(task, st, latestLogTimeByTask[task.id]);
    const pendingHint = getTaskPendingHint(st);
    return (
      <div key={task.id} className="min-w-0 rounded-xl border border-zinc-800 bg-zinc-950/50 p-3.5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <p className="break-words text-sm font-semibold text-zinc-100">{task.name || task.local_path}</p>
            <p className="break-words text-xs text-zinc-400" title={task.local_path}>本地：{shortPath(task.local_path, 72)}</p>
            <p className="break-words text-xs text-zinc-500" title={task.cloud_folder_token}>云端：{shortPath(task.cloud_folder_name || task.cloud_folder_token, 72)}</p>
          </div>
          <StatusPill label={stateLabels[stateKey] || stateKey} tone={stateTones[stateKey] || "neutral"} />
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-zinc-300">
          <span className="inline-flex items-center gap-2">
            <ModeIcon mode={task.sync_mode} className="h-3.5 w-3.5" />
            {modeLabels[task.sync_mode] || task.sync_mode}
          </span>
          <span className="text-zinc-600">|</span>
          <span>更新：{updateModeLabels[task.update_mode || "auto"]}</span>
          <span className="text-zinc-600">|</span>
          <span>最近活动：{formatShortTime(activityTime)}</span>
        </div>
        {progress !== null ? (
          <div className="mt-3">
            <div className="flex items-center justify-between text-xs text-zinc-400">
              <span>进度 {progress}%</span>
              <span>已处理 {progressState.processed}/{progressState.effectiveTotal}</span>
            </div>
            <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
              <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>
        ) : null}
        {st ? (
          <p className="mt-2 text-xs text-zinc-500">
            完成 {st.completed_files}，删除 {st.deleted_files}，待删 {st.delete_pending_files}，删失败 {st.delete_failed_files}，失败 {st.failed_files}，冲突 {st.conflict_files}
          </p>
        ) : null}
        {pendingHint ? <p className="mt-1 text-xs leading-5 text-zinc-500">待处理来源：{pendingHint}</p> : null}
        {st?.last_error ? <p className="mt-2 text-xs text-rose-400">错误：{st.last_error}</p> : null}
      </div>
    );
  };

  return (
    <section className="space-y-5 animate-fade-up">
      {/* 防御性提示：正常流程不应到达此处（App.tsx 已门控未连接状态） */}
      {!connected ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-950/25 p-4 text-center text-sm text-rose-200">
          飞书账号未连接，请刷新页面以完成授权引导。
        </div>
      ) : null}

      {/* Stat cards */}
      <div className="grid gap-4 sm:grid-cols-2 min-[1500px]:grid-cols-4">
        <StatCard label="同步健康" value={healthLabel} hint={healthHint} tone={healthTone} icon={<IconActivity className="h-4 w-4" />} />
        <StatCard label="待处理事件" value={`${pendingEventCount}`} hint={`待删除 ${deletePendingCount}，队列 ${queuedSyncCount}`} tone={pendingEventCount > 0 ? "warning" : "success"} icon={<IconArrowRightLeft className="h-4 w-4" />} />
        <StatCard label="问题处理" value={`${attentionCount}`} hint={`失败/取消 ${failedEventCount}，冲突 ${unresolvedConflicts + conflictEventCount}`} tone={attentionCount > 0 ? "danger" : "success"} icon={<IconConflicts className="h-4 w-4" />} />
        <StatCard label="最近成功" value={lastSuccess ? formatShortTime(lastSuccess.timestamp) : "暂无"} hint={lastSuccess ? lastSuccess.taskName : `今日日志事件 ${todayEventCount} 条`} tone="neutral" icon={<IconRefresh className="h-4 w-4" />} />
      </div>

      {/* Two-column: tasks + logs */}
      <div className="grid items-start gap-5 min-[1760px]:grid-cols-[minmax(0,1.08fr)_minmax(360px,0.92fr)]">
        {/* Task overview */}
        <div className="flex max-h-[560px] min-h-0 flex-col rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-zinc-50">任务概览</h2>
              <p className="mt-1 text-xs text-zinc-400">分开展示当前运行任务和最近同步任务。</p>
            </div>
            <div className="flex gap-2">
              <button className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800" onClick={refreshTasks} type="button">
                <IconRefresh className="h-3.5 w-3.5" /> 刷新
              </button>
              <button className="inline-flex items-center gap-2 rounded-lg bg-[#3370FF] px-4 py-2 text-xs font-semibold text-white hover:bg-[#3370FF]/80" onClick={() => onNavigate("tasks")} type="button">
                <IconTasks className="h-3.5 w-3.5" /> 管理任务
              </button>
            </div>
          </div>
          <div className="mt-4 min-h-0 flex-1 space-y-3 overflow-y-auto pr-1 log-scroll-area">
            {taskLoading ? (
              <div className="space-y-3">{[1, 2, 3].map((i) => <div key={i} className="h-20 animate-pulse rounded-xl bg-zinc-800/50" />)}</div>
            ) : tasks.length === 0 ? (
              <div className="py-8 text-center">
                <IconTasks className="mx-auto h-10 w-10 text-zinc-700" />
                <p className="mt-3 text-sm text-zinc-500">暂无同步任务，请先创建。</p>
              </div>
            ) : (
              <>
                <div>
                  <div className="mb-2 flex items-center justify-between text-xs">
                    <span className="font-semibold text-zinc-300">当前运行</span>
                    <span className="text-zinc-500">{runningTaskList.length ? `${runningTaskList.length} 个任务` : "无运行任务"}</span>
                  </div>
                  {runningTaskList.length > 0 ? (
                    <div className="space-y-3">{runningTaskList.map(renderTaskCard)}</div>
                  ) : (
                    <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 px-4 py-5 text-center text-sm text-zinc-500">
                      当前无运行任务。
                    </div>
                  )}
                </div>
                <div>
                  <div className="mb-2 flex items-center justify-between text-xs">
                    <span className="font-semibold text-zinc-300">最近同步</span>
                    <span className="text-zinc-500">按最近活动排序</span>
                  </div>
                  <div className="space-y-3">{recentTaskList.map(renderTaskCard)}</div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Attention summary */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-zinc-50">需要关注</h2>
              <p className="mt-1 text-xs text-zinc-400">
                优先展示失败、冲突、待删除和同步队列摘要。
              </p>
            </div>
            <div className="flex items-center gap-2">
              {wsStatus === "connected" ? (
                <span className="inline-flex items-center gap-1.5 text-xs text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  实时
                </span>
              ) : null}
              <button className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800" onClick={refreshStatus} type="button">
                <IconRefresh className="h-3.5 w-3.5" /> 刷新
              </button>
            </div>
          </div>
          <div className="mt-4 max-h-[390px] space-y-3 overflow-auto pr-2 log-scroll-area">
            {focusEntries.length === 0 ? (
              <div className="py-8 text-center">
                <IconActivity className="mx-auto h-10 w-10 text-emerald-500/70" />
                <p className="mt-3 text-sm font-medium text-zinc-300">当前没有需要处理的问题。</p>
                <p className="mt-1 text-xs text-zinc-500">
                  {lastSuccess ? `最近成功：${lastSuccess.taskName}，${formatShortTime(lastSuccess.timestamp)}` : "等待下一次同步完成。"}
                </p>
              </div>
            ) : (
              focusEntries.slice(0, 5).map((entry, i) => (
                <div key={`${entry.taskId}-${entry.timestamp}-${i}`} className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="space-y-1">
                      <p className="text-xs text-zinc-500">{formatTimestamp(entry.timestamp)}</p>
                      <p className="text-sm text-zinc-200">{entry.taskName}</p>
                    </div>
                    <StatusPill label={statusLabelMap[entry.status] || entry.status} tone={getDashboardEventTone(entry.status)} />
                  </div>
                  <p className="mt-2 break-words text-xs text-zinc-500">{entry.path}</p>
                  {entry.message ? <p className="mt-1 break-words text-xs text-zinc-600">{entry.message}</p> : null}
                  {getDashboardEventHint(entry) ? (
                    <p className="mt-1 text-xs text-zinc-500">{getDashboardEventHint(entry)}</p>
                  ) : null}
                </div>
              ))
            )}
          </div>
          {/* 查看全部链接 */}
          {syncLogEntries.length > 0 ? (
            <div className="mt-3 flex justify-center">
              <button
                className="inline-flex items-center gap-1.5 text-xs font-medium text-[#3370FF] transition hover:text-[#3370FF]/80"
                onClick={() => onNavigate("logcenter")}
                type="button"
              >
                前往日志中心查看全部 {syncLogEntries.length} 条事件 →
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
