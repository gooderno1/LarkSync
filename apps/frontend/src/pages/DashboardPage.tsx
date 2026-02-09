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
import { modeLabels, updateModeLabels, stateLabels, stateTones, statusLabelMap } from "../lib/constants";
import { StatCard } from "../components/StatCard";
import { StatusPill } from "../components/StatusPill";
import { StatCardSkeleton } from "../components/Skeleton";
import { EmptyState } from "../components/EmptyState";
import { ModeIcon, IconRefresh, IconTasks, IconArrowRightLeft, IconConflicts, IconActivity } from "../components/Icons";
import type { SyncLogEntry, NavKey } from "../types";

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

  const today = new Date();
  const todayCount = syncLogEntries.filter((e) => isSameDay(e.timestamp, today)).length;
  const lastSync = syncLogEntries[0];
  const enabledTasks = tasks.filter((t) => t.enabled).length;
  const runningTasks = tasks.filter((t) => statusMap[t.id]?.state === "running").length;
  const unresolvedConflicts = conflicts.filter((c) => !c.resolved).length;

  return (
    <section className="space-y-6 animate-fade-up">
      {/* 防御性提示：正常流程不应到达此处（App.tsx 已门控未连接状态） */}
      {!connected ? (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4 text-center text-sm text-amber-300">
          飞书账号未连接，请刷新页面以完成授权引导。
        </div>
      ) : null}

      {/* Stat cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="今日同步" value={`${todayCount}`} hint="按日志统计" tone="success" icon={<IconRefresh className="h-4 w-4" />} />
        <StatCard label="启用任务" value={`${enabledTasks}`} hint={runningTasks ? `运行中 ${runningTasks} 个` : "当前无运行任务"} tone="info" icon={<IconTasks className="h-4 w-4" />} />
        <StatCard label="最近同步" value={lastSync ? formatShortTime(lastSync.timestamp) : "暂无"} hint={lastSync ? lastSync.taskName : "等待任务触发"} tone="neutral" icon={<IconArrowRightLeft className="h-4 w-4" />} />
        <StatCard label="待处理冲突" value={`${unresolvedConflicts}`} hint={unresolvedConflicts ? "请尽快处理" : "暂无冲突"} tone={unresolvedConflicts ? "warning" : "neutral"} icon={<IconConflicts className="h-4 w-4" />} />
      </div>

      {/* Two-column: tasks + logs */}
      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        {/* Active tasks */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-zinc-50">活跃任务</h2>
              <p className="mt-1 text-xs text-zinc-400">展示最近活跃的同步任务与状态摘要。</p>
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
          <div className="mt-5 space-y-4">
            {taskLoading ? (
              <div className="space-y-3">{[1, 2, 3].map((i) => <div key={i} className="h-20 animate-pulse rounded-xl bg-zinc-800/50" />)}</div>
            ) : tasks.length === 0 ? (
              <div className="py-8 text-center">
                <IconTasks className="mx-auto h-10 w-10 text-zinc-700" />
                <p className="mt-3 text-sm text-zinc-500">暂无同步任务，请先创建。</p>
              </div>
            ) : (
              tasks.slice(0, 4).map((task) => {
                const st = statusMap[task.id];
                const stateKey = !task.enabled ? "paused" : st?.state || "idle";
                const progress = st && st.total_files > 0 ? Math.round((st.completed_files / st.total_files) * 100) : null;
                return (
                  <div key={task.id} className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="space-y-1">
                        <p className="text-sm font-semibold text-zinc-100">{task.name || task.local_path}</p>
                        <p className="text-xs text-zinc-400">本地：{task.local_path}</p>
                        <p className="text-xs text-zinc-500" title={task.cloud_folder_token}>云端：{task.cloud_folder_name || task.cloud_folder_token}</p>
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
                    </div>
                    {progress !== null ? (
                      <div className="mt-3">
                        <div className="flex items-center justify-between text-xs text-zinc-400">
                          <span>进度 {progress}%</span>
                          <span>{st?.completed_files ?? 0}/{st?.total_files ?? 0}</span>
                        </div>
                        <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
                          <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${progress}%` }} />
                        </div>
                      </div>
                    ) : null}
                    {st?.last_error ? <p className="mt-2 text-xs text-rose-400">错误：{st.last_error}</p> : null}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Sync logs */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-zinc-50">同步日志</h2>
              <p className="mt-1 text-xs text-zinc-400">
                实时记录任务与文件动作。
                {syncLogEntries.length > 0 ? (
                  <span className="ml-1 text-zinc-600">共 {syncLogEntries.length} 条</span>
                ) : null}
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
          <div className="mt-5 max-h-[480px] space-y-3 overflow-auto pr-2 log-scroll-area">
            {syncLogEntries.length === 0 ? (
              <div className="py-8 text-center">
                <IconConflicts className="mx-auto h-10 w-10 text-zinc-700" />
                <p className="mt-3 text-sm text-zinc-500">暂无同步日志。</p>
              </div>
            ) : (
              syncLogEntries.slice(0, 20).map((entry, i) => (
                <div key={`${entry.taskId}-${entry.timestamp}-${i}`} className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="space-y-1">
                      <p className="text-xs text-zinc-500">{formatTimestamp(entry.timestamp)}</p>
                      <p className="text-sm text-zinc-200">{entry.taskName}</p>
                    </div>
                    <StatusPill label={statusLabelMap[entry.status] || entry.status} tone={entry.status === "failed" ? "danger" : entry.status === "skipped" ? "warning" : "success"} />
                  </div>
                  <p className="mt-2 break-all text-xs text-zinc-500">{entry.path}</p>
                  {entry.message ? <p className="mt-1 text-xs text-zinc-600">{entry.message}</p> : null}
                </div>
              ))
            )}
          </div>
          {/* 查看全部链接 */}
          {syncLogEntries.length > 20 ? (
            <div className="mt-3 flex justify-center">
              <button
                className="inline-flex items-center gap-1.5 text-xs font-medium text-[#3370FF] transition hover:text-[#3370FF]/80"
                onClick={() => onNavigate("logcenter")}
                type="button"
              >
                查看全部 {syncLogEntries.length} 条日志 →
              </button>
            </div>
          ) : syncLogEntries.length > 0 ? (
            <div className="mt-3 flex justify-center">
              <button
                className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-500 transition hover:text-zinc-300"
                onClick={() => onNavigate("logcenter")}
                type="button"
              >
                前往日志中心 →
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
