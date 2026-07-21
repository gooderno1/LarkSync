/* ------------------------------------------------------------------ */
/*  同步任务管理页面                                                     */
/* ------------------------------------------------------------------ */

import { useMemo, useState } from "react";
import { useTasks } from "../hooks/useTasks";
import { useConflicts } from "../hooks/useConflicts";
import { NewTaskModal } from "../components/NewTaskModal";
import { TasksEmptyState } from "../components/tasks/TasksEmptyState";
import { TasksPageHeader } from "../components/tasks/TasksPageHeader";
import { TaskSettingsModal } from "../components/tasks/TaskSettingsModal";
import {
  IconFolder,
  IconMoreHorizontal,
  IconPlay,
  ModeIcon,
} from "../components/Icons";
import { modeLabels, stateLabels } from "../lib/constants";
import { computeTaskProgress } from "../lib/progress";
import { deriveTaskHealth, summarizePath } from "../lib/taskManagement";
import { formatTimestamp } from "../lib/formatters";
import { confirm } from "../components/ui/confirm-dialog";
import { useToast } from "../components/ui/toast";
import type { SyncTask, SyncTaskStatus } from "../types";
import {
  TASK_PAGE_SHOWCASE_COUNTS,
  TASK_PAGE_SHOWCASE_DURATIONS,
  TASK_PAGE_SHOWCASE_STATUS,
  TASK_PAGE_SHOWCASE_TASKS,
  useTaskPageShowcase,
} from "../lib/taskPageShowcase";

type TasksPageProps = {
  onOpenTaskDetail?: (taskId: string) => void;
  showcase?: boolean;
};

const TASK_TABLE_QUEUE_STATUSES = new Set(["queued", "creating", "created", "reimporting"]);

function countLastFileStatus(status: SyncTaskStatus | undefined, matcher: (value: string) => boolean): number {
  return (status?.last_files || []).filter((item) => matcher(item.status)).length;
}

function taskPendingCounts(status: SyncTaskStatus | undefined, conflictCount: number) {
  const queued = countLastFileStatus(status, (value) => TASK_TABLE_QUEUE_STATUSES.has(value));
  const deletePending = Math.max(
    status?.delete_pending_files ?? 0,
    countLastFileStatus(status, (value) => value === "delete_pending")
  );
  const deleteFailed = status?.delete_failed_files ?? 0;
  const failed = status?.failed_files ?? 0;
  return {
    queued,
    deleteTotal: deletePending + deleteFailed,
    failed,
    conflict: conflictCount,
  };
}

function taskStateKey(task: SyncTask, status?: SyncTaskStatus): string {
  return !task.enabled ? "paused" : status?.state || "idle";
}

function TaskCountCell({ value, tone = "neutral" }: { value: number; tone?: "neutral" | "warning" | "danger" }) {
  const cls =
    tone === "danger"
      ? "text-[#be123c]"
      : tone === "warning"
        ? "text-[#b45309]"
        : "text-[#334762]";
  return <span className={`tabular-nums ${cls}`}>{value}</span>;
}

const folderAccentClasses = [
  "bg-[#eaf2ff] text-[#3370ff]",
  "bg-[#fff7df] text-[#e6a700]",
  "bg-[#f1edff] text-[#7c5ce7]",
  "bg-[#e9fbf1] text-[#10b981]",
  "bg-[#eaf2ff] text-[#3370ff]",
  "bg-[#fff0eb] text-[#f15a38]",
  "bg-[#e8f9fb] text-[#20a9c7]",
  "bg-[#eef3f9] text-[#8aa0bb]",
];

function modeToneClass(mode: string): string {
  if (mode === "upload_only") return "border-[#a7e3c4] bg-[#effbf4] text-[#058757]";
  if (mode === "download_only") return "border-[#d5c8ff] bg-[#f5f2ff] text-[#7250d8]";
  return "border-[#b7d2ff] bg-[#eef5ff] text-[#2563eb]";
}

function stateTextClass(state: string): string {
  if (state === "failed") return "text-[#e11d48]";
  if (state === "running" || state === "success") return "text-[#059669]";
  return "text-[#52657a]";
}

function healthDotClass(tone: string): string {
  if (tone === "danger") return "bg-[#f43f5e]";
  if (tone === "warning") return "bg-[#f59e0b]";
  if (tone === "info") return "bg-[#3370ff]";
  return "bg-[#10b981]";
}

function formatDuration(startedAt?: number | null, finishedAt?: number | null): string | null {
  if (!startedAt || !finishedAt || finishedAt < startedAt) return null;
  const seconds = Math.max(0, Math.round(finishedAt - startedAt));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = seconds % 60;
  return [hours, minutes, rest].map((value) => String(value).padStart(2, "0")).join(":");
}

export function TasksPage({ onOpenTaskDetail, showcase }: TasksPageProps) {
  const {
    tasks: liveTasks,
    taskLoading: liveTaskLoading,
    taskError: liveTaskError,
    statusMap: liveStatusMap,
    refreshTasks,
    toggleTask,
    updateTaskSettings,
    runTask,
    deleteTask,
  } = useTasks();
  const { conflicts: liveConflicts } = useConflicts();
  const { toast } = useToast();
  const automaticShowcase = useTaskPageShowcase();
  const showcaseMode = showcase ?? automaticShowcase;
  const [showcaseTasks, setShowcaseTasks] = useState<SyncTask[]>(() => TASK_PAGE_SHOWCASE_TASKS.map((task) => ({ ...task })));
  const [showcaseStatusMap, setShowcaseStatusMap] = useState<Record<string, SyncTaskStatus>>(() => ({ ...TASK_PAGE_SHOWCASE_STATUS }));
  const tasks = showcaseMode ? showcaseTasks : liveTasks;
  const taskLoading = showcaseMode ? false : liveTaskLoading;
  const taskError = showcaseMode ? null : liveTaskError;
  const statusMap = showcaseMode ? showcaseStatusMap : liveStatusMap;
  const conflicts = useMemo(() => (showcaseMode ? [] : liveConflicts), [liveConflicts, showcaseMode]);
  const [showModal, setShowModal] = useState(false);
  const [hideTestTasks, setHideTestTasks] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [stateFilter, setStateFilter] = useState("all");
  const [syncModeFilter, setSyncModeFilter] = useState("all");
  const [healthFilter, setHealthFilter] = useState("all");
  const [settingsTaskId, setSettingsTaskId] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const isDevMode = import.meta.env.DEV;
  const testTaskCount = tasks.filter((task) => Boolean(task.is_test)).length;
  const showTestToggle = !showcaseMode && isDevMode && testTaskCount > 0;
  const unresolvedConflictCountByTask = useMemo(() => {
    const mapped: Record<string, number> = {};
    for (const task of tasks) {
      mapped[task.id] = conflicts.filter(
        (conflict) => !conflict.resolved && conflict.local_path.startsWith(task.local_path)
      ).length;
    }
    return mapped;
  }, [conflicts, tasks]);

  const visibleTasksBeforeFilters = useMemo(
    () => (hideTestTasks ? tasks.filter((task) => !task.is_test) : tasks),
    [hideTestTasks, tasks]
  );
  const hasActiveFilters =
    searchQuery.trim().length > 0 ||
    stateFilter !== "all" ||
    syncModeFilter !== "all" ||
    healthFilter !== "all";
  const displayTasks = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return visibleTasksBeforeFilters.filter((task) => {
      const st = statusMap[task.id];
      const conflictCount = Math.max(unresolvedConflictCountByTask[task.id] || 0, st?.conflict_files ?? 0);
      const stateKey = taskStateKey(task, st);
      const health = deriveTaskHealth({
        enabled: task.enabled,
        state: st?.state,
        lastFiles: st?.last_files,
        conflictCount,
        lastError: st?.last_error,
        failedFiles: st?.failed_files,
        deleteFailedFiles: st?.delete_failed_files,
      });
      const haystack = [
        task.name,
        task.local_path,
        task.cloud_folder_name,
        task.cloud_folder_token,
        task.id,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      if (query && !haystack.includes(query)) return false;
      if (stateFilter !== "all" && stateKey !== stateFilter) return false;
      if (syncModeFilter !== "all" && task.sync_mode !== syncModeFilter) return false;
      if (healthFilter === "healthy" && health.tone !== "success") return false;
      if (healthFilter === "attention" && health.tone !== "warning") return false;
      if (healthFilter === "error" && health.tone !== "danger") return false;
      return true;
    });
  }, [
    healthFilter,
    searchQuery,
    stateFilter,
    statusMap,
    syncModeFilter,
    unresolvedConflictCountByTask,
    visibleTasksBeforeFilters,
  ]);

  const pageSize = 20;
  const totalPages = Math.max(1, Math.ceil(displayTasks.length / pageSize));
  const activePage = Math.min(currentPage, totalPages);
  const pagedTasks = displayTasks.slice((activePage - 1) * pageSize, activePage * pageSize);

  const settingsTask = tasks.find((task) => task.id === settingsTaskId) || null;
  const settingsProgress = computeTaskProgress(settingsTask ? statusMap[settingsTask.id] : undefined);

  const handleDelete = async (task: SyncTask) => {
    const ok = await confirm({
      title: "确认删除任务",
      description: `即将删除任务「${task.name || task.local_path}」，此操作不可恢复。`,
      confirmLabel: "删除",
      tone: "danger",
    });
    if (!ok) return false;
    if (showcaseMode) {
      setShowcaseTasks((current) => current.filter((item) => item.id !== task.id));
      setShowcaseStatusMap((current) => {
        const next = { ...current };
        delete next[task.id];
        return next;
      });
    } else {
      deleteTask(task);
    }
    toast("任务已删除", "danger");
    return true;
  };

  const handleRunTask = (task: SyncTask) => {
    if (showcaseMode) {
      setShowcaseStatusMap((current) => ({
        ...current,
        [task.id]: {
          ...(current[task.id] || TASK_PAGE_SHOWCASE_STATUS[task.id]),
          task_id: task.id,
          state: "running",
          started_at: Date.now() / 1000,
          finished_at: null,
          current_run_id: `showcase_${task.id}`,
        },
      }));
    } else {
      runTask(task);
    }
    toast("同步已触发", "info");
  };

  const handleToggleTask = (task: SyncTask) => {
    if (showcaseMode) {
      setShowcaseTasks((current) =>
        current.map((item) => (item.id === task.id ? { ...item, enabled: !item.enabled } : item))
      );
    } else {
      toggleTask(task);
    }
    toast(task.enabled ? "已停用" : "已启用", "info");
  };

  return (
    <section
      className="tasks-clarity animate-fade-up flex min-h-full min-w-0 flex-col gap-4"
      data-task-page-mode={showcaseMode ? "showcase" : "live"}
    >
      <TasksPageHeader
        onCreate={() => setShowModal(true)}
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        stateFilter={stateFilter}
        onStateFilterChange={setStateFilter}
        syncModeFilter={syncModeFilter}
        onSyncModeFilterChange={setSyncModeFilter}
        healthFilter={healthFilter}
        onHealthFilterChange={setHealthFilter}
      />

      {taskError ? (
        <div className="rounded-xl border border-[#f43f5e]/30 bg-[#fff1f2] px-4 py-3 text-sm text-[#be123c]">
          错误：{taskError}
        </div>
      ) : null}

      {/* Task table */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        {taskLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 animate-pulse rounded-xl border border-[#d7e4f5] bg-white/70" />
            ))}
          </div>
        ) : displayTasks.length === 0 ? (
          hasActiveFilters && visibleTasksBeforeFilters.length > 0 ? (
            <div className="rounded-xl border border-dashed border-[#c9d8ec] bg-white/72 px-6 py-14 text-center shadow-[0_16px_40px_rgba(51,112,255,0.05)]">
              <IconFolder className="mx-auto h-10 w-10 text-[#9fb2c8]" />
              <p className="mt-3 text-sm font-semibold text-[#102033]">没有匹配的任务</p>
              <p className="mt-1 text-xs text-[#6b7f96]">请调整搜索关键词或筛选条件。</p>
              <button
                className="mt-4 rounded-lg border border-[#c9d8ec] px-4 py-2 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]"
                onClick={() => {
                  setSearchQuery("");
                  setStateFilter("all");
                  setSyncModeFilter("all");
                  setHealthFilter("all");
                }}
                type="button"
              >
                清空筛选
              </button>
            </div>
          ) : (
            <TasksEmptyState
              hasAnyTasks={tasks.length > 0}
              hideTestTasks={hideTestTasks}
              testTaskCount={testTaskCount}
            />
          )
        ) : (
          <div
            className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-[#d7e4f5] bg-white shadow-[0_12px_30px_rgba(51,112,255,0.06)]"
            data-task-table="true"
          >
            <div className="min-h-0 min-w-0 flex-1 overflow-x-auto">
              <table className="h-full w-full min-w-[1000px] table-fixed text-left text-sm">
                <thead className="border-b border-[#d7e4f5] bg-[#f8fbff] text-xs text-[#52657a]">
                  <tr className="h-12">
                    <th className="w-[12%] px-3.5 font-semibold">任务名称</th>
                    <th className="w-[16%] px-3.5 font-semibold">本地目录</th>
                    <th className="w-[13%] px-3.5 font-semibold">云端目录</th>
                    <th className="w-[9%] px-3.5 font-semibold">同步模式</th>
                    <th className="w-[9%] px-3.5 font-semibold">状态 / 健康</th>
                    <th className="w-[11%] px-3.5 font-semibold">最近运行</th>
                    <th data-task-count-header="true" className="w-[4%] whitespace-nowrap px-1 text-center font-semibold">队列</th>
                    <th data-task-count-header="true" className="w-[4%] whitespace-nowrap px-1 text-center font-semibold">删除</th>
                    <th data-task-count-header="true" className="w-[4%] whitespace-nowrap px-1 text-center font-semibold">失败</th>
                    <th data-task-count-header="true" className="w-[4%] whitespace-nowrap px-1 text-center font-semibold">冲突</th>
                    <th className="w-[14%] px-3.5 text-right font-semibold">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#edf3fb]">
                  {pagedTasks.map((task, index) => {
                    const st = statusMap[task.id];
                    const conflictCount = Math.max(unresolvedConflictCountByTask[task.id] || 0, st?.conflict_files ?? 0);
                    const stateKey = taskStateKey(task, st);
                    const stateLabel = stateLabels[stateKey] || stateKey;
                    const displayStateLabel = showcaseMode && stateKey === "running" ? "运行中" : stateLabel;
                    const health = deriveTaskHealth({
                      enabled: task.enabled,
                      state: st?.state,
                      lastFiles: st?.last_files,
                      conflictCount,
                      lastError: st?.last_error,
                      failedFiles: st?.failed_files,
                      deleteFailedFiles: st?.delete_failed_files,
                    });
                    const counts = showcaseMode
                      ? TASK_PAGE_SHOWCASE_COUNTS[task.id] || taskPendingCounts(st, conflictCount)
                      : taskPendingCounts(st, conflictCount);
                    const cloudPath = task.cloud_folder_name || task.cloud_folder_token || "-";
                    const progressState = computeTaskProgress(st);
                    const progress = progressState.progress;
                    const lastSyncTime = st?.finished_at ?? st?.started_at ?? task.last_run_at ?? null;
                    const duration = formatDuration(st?.started_at, st?.finished_at);
                    const healthLabel = health.tone === "danger" ? "失败" : health.tone === "warning" ? health.label : "健康";

                    return (
                      <tr
                        key={task.id}
                        className="h-[76px] align-middle text-[#334762] transition hover:bg-[#f8fbff] max-[1450px]:h-[88px] max-[1300px]:h-[100px]"
                        data-task-row="true"
                      >
                          <td className="px-3.5 py-2">
                            <div className="flex min-w-0 items-center gap-3">
                              <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg ${folderAccentClasses[index % folderAccentClasses.length]}`}>
                                <IconFolder className="h-4 w-4" />
                              </span>
                              <div className="min-w-0">
                                {onOpenTaskDetail ? (
                                  <button
                                    aria-label={`查看项目详情：${task.name || "未命名任务"}`}
                                    className="block max-w-full truncate rounded-sm text-left text-[13px] font-semibold text-[#102033] transition-colors hover:text-[#3370ff] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3370ff]/40"
                                    data-task-detail-name-entry={task.id}
                                    onClick={() => onOpenTaskDetail(task.id)}
                                    title={task.name || task.local_path}
                                    type="button"
                                  >
                                    {task.name || "未命名任务"}
                                  </button>
                                ) : (
                                  <p className="truncate text-[13px] font-semibold text-[#102033]" title={task.name || task.local_path}>
                                    {task.name || "未命名任务"}
                                  </p>
                                )}
                                <p className="mt-0.5 truncate font-mono text-[11px] text-[#6b7f96]" title={task.id}>
                                  ID: {summarizePath(task.id, 1, 20)}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="px-3.5 py-2 font-mono text-xs" title={task.local_path}>
                            <span className="block max-h-10 overflow-hidden break-all leading-5">
                              {summarizePath(task.local_path, 4, 64)}
                            </span>
                          </td>
                          <td className="truncate px-3.5 py-2 text-xs" title={task.cloud_folder_token}>
                            {summarizePath(cloudPath, 3, 44)}
                          </td>
                          <td className="px-3.5 py-2">
                            <span
                              className={`inline-flex items-center gap-1 whitespace-nowrap rounded-md border px-1.5 py-1 text-xs font-semibold ${modeToneClass(task.sync_mode)}`}
                              data-task-mode={task.sync_mode}
                            >
                              <ModeIcon mode={task.sync_mode} className="h-3.5 w-3.5" />
                              {modeLabels[task.sync_mode] || task.sync_mode}
                            </span>
                          </td>
                          <td className="px-3.5 py-2">
                            <div className="space-y-1">
                              <p className={`text-xs font-semibold ${stateTextClass(stateKey)}`}>{displayStateLabel}</p>
                              <span className="flex items-center gap-1.5 text-[11px] text-[#6b7f96]">
                                <span className={`h-1.5 w-1.5 rounded-full ${healthDotClass(health.tone)}`} />
                                {healthLabel}
                              </span>
                            </div>
                          </td>
                          <td className="px-3.5 py-2">
                            <div className="min-w-0 text-xs">
                              <p className="truncate text-[#334762]">{lastSyncTime ? formatTimestamp(lastSyncTime) : "尚未运行"}</p>
                              {showcaseMode ? (
                                <p className="mt-1 truncate text-[11px] text-[#6b7f96]">{TASK_PAGE_SHOWCASE_DURATIONS[task.id] || "--"}</p>
                              ) : progress !== null ? (
                                <p className="mt-1 truncate text-[11px] text-[#6b7f96]">{progress}% · {duration || "进行中"}</p>
                              ) : duration ? <p className="mt-1 text-[11px] text-[#6b7f96]">用时 {duration}</p> : null}
                            </div>
                          </td>
                          <td className="px-1 py-2 text-center"><TaskCountCell value={counts.queued} tone={counts.queued > 0 ? "warning" : "neutral"} /></td>
                          <td className="px-1 py-2 text-center"><TaskCountCell value={counts.deleteTotal} tone={counts.deleteTotal > 0 ? "warning" : "neutral"} /></td>
                          <td className="px-1 py-2 text-center"><TaskCountCell value={counts.failed} tone={counts.failed > 0 ? "danger" : "neutral"} /></td>
                          <td className="px-1 py-2 text-center"><TaskCountCell value={counts.conflict} tone={counts.conflict > 0 ? "danger" : "neutral"} /></td>
                          <td className="px-3.5 py-2">
                            <div className="flex items-center justify-end gap-1">
                              <button
                                aria-label={health.isRunning ? "同步中" : "立即同步"}
                                className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-[#bfd8ff] text-[#3370ff] hover:bg-[#eef5ff] disabled:opacity-50"
                                onClick={() => handleRunTask(task)}
                                disabled={health.isRunning}
                                type="button"
                                title={health.isRunning ? "同步中" : "立即同步"}
                              >
                                <IconPlay className="h-3.5 w-3.5" />
                              </button>
                              <button
                                aria-label={task.enabled ? "停用任务" : "启用任务"}
                                aria-checked={task.enabled}
                                className={`relative h-5 w-9 shrink-0 rounded-full border p-0.5 shadow-inner transition ${task.enabled ? "border-[#3370ff] bg-[#3370ff]" : "border-[#afc1d5] bg-[#c9d8ec]"}`}
                                onClick={() => handleToggleTask(task)}
                                role="switch"
                                title={task.enabled ? "停用任务" : "启用任务"}
                                type="button"
                              >
                                <span className={`block h-3.5 w-3.5 rounded-full bg-white shadow-sm transition-transform ${task.enabled ? "translate-x-4" : "translate-x-0"}`} />
                              </button>
                              {onOpenTaskDetail ? (
                                <button
                                  aria-label="查看任务详情"
                                  className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-[#c9d8ec] text-[#3370ff] hover:bg-[#eef5ff]"
                                  onClick={() => onOpenTaskDetail(task.id)}
                                  title="查看任务详情"
                                  type="button"
                                >
                                  <IconFolder className="h-3.5 w-3.5" />
                                </button>
                              ) : null}
                              <button
                                aria-expanded={settingsTaskId === task.id}
                                aria-haspopup="dialog"
                                aria-label="打开任务设置"
                                className={`inline-flex h-7 w-7 items-center justify-center rounded-lg border transition ${settingsTaskId === task.id ? "border-[#3370ff] bg-[#eef5ff] text-[#3370ff]" : "border-[#c9d8ec] text-[#52657A] hover:bg-[#f6faff] hover:text-[#3370ff]"}`}
                                onClick={() => setSettingsTaskId(task.id)}
                                type="button"
                                title="打开任务设置"
                              >
                                <IconMoreHorizontal className="h-4 w-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div
              className="flex h-11 min-w-0 items-center justify-between gap-3 border-t border-[#edf3fb] px-3.5 text-xs font-medium text-[#52657A]"
              data-task-table-footer="true"
            >
              <span>
                {showcaseMode
                  ? `演示数据 · 共 ${displayTasks.length} 个任务`
                  : hasActiveFilters
                    ? `显示 ${displayTasks.length} / 共 ${visibleTasksBeforeFilters.length} 个任务`
                    : `共 ${displayTasks.length} 个任务`}
              </span>
              <div className="flex items-center gap-2">
                {showTestToggle ? (
                  <button
                    className="rounded-md px-2 py-1 text-[#52657a] hover:bg-[#eef5ff] hover:text-[#3370ff]"
                    onClick={() => setHideTestTasks((previous) => !previous)}
                    type="button"
                  >
                    {hideTestTasks ? `显示测试任务（${testTaskCount}）` : "隐藏测试任务"}
                  </button>
                ) : null}
                {!showcaseMode ? (
                  <button
                    className="rounded-md px-2 py-1 text-[#52657a] hover:bg-[#eef5ff] hover:text-[#3370ff]"
                    onClick={refreshTasks}
                    type="button"
                  >
                    刷新
                  </button>
                ) : null}
                <button
                  aria-label="上一页"
                  className="grid h-7 w-7 place-items-center rounded-md border border-[#d7e4f5] text-[#52657a] disabled:cursor-not-allowed disabled:opacity-40"
                  disabled={activePage <= 1}
                  onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                  type="button"
                >
                  ‹
                </button>
                <span className="grid h-7 min-w-7 place-items-center rounded-md bg-[#3370ff] px-2 font-semibold text-white">
                  {activePage}
                </span>
                <button
                  aria-label="下一页"
                  className="grid h-7 w-7 place-items-center rounded-md border border-[#d7e4f5] text-[#52657a] disabled:cursor-not-allowed disabled:opacity-40"
                  disabled={activePage >= totalPages}
                  onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                  type="button"
                >
                  ›
                </button>
                <span className="ml-1 whitespace-nowrap">20 条/页</span>
              </div>
            </div>
          </div>
        )}
      </div>

      <NewTaskModal open={showModal} onClose={() => setShowModal(false)} onCreated={refreshTasks} />
      {settingsTask ? (
        <TaskSettingsModal
          task={settingsTask}
          processed={settingsProgress.processed}
          total={settingsProgress.effectiveTotal}
          onClose={() => setSettingsTaskId(null)}
          onDelete={async () => {
            const deleted = await handleDelete(settingsTask);
            if (deleted) setSettingsTaskId(null);
          }}
          onSave={async (patch) => {
            try {
              if (showcaseMode) {
                setShowcaseTasks((current) =>
                  current.map((task) => (task.id === settingsTask.id ? { ...task, ...patch } : task))
                );
              } else {
                await updateTaskSettings({ id: settingsTask.id, patch });
              }
              toast("任务设置已保存", "success");
            } catch (error) {
              toast(error instanceof Error ? error.message : "任务设置保存失败", "danger");
              throw error;
            }
          }}
        />
      ) : null}
    </section>
  );
}
