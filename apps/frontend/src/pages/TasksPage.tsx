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
import { StatusPill } from "../components/StatusPill";
import {
  IconFolder,
  IconMoreHorizontal,
  IconPlay,
  ModeIcon,
} from "../components/Icons";
import { modeLabels, stateLabels, stateTones } from "../lib/constants";
import { computeTaskProgress } from "../lib/progress";
import { deriveTaskHealth, summarizePath } from "../lib/taskManagement";
import { formatTimestamp } from "../lib/formatters";
import { confirm } from "../components/ui/confirm-dialog";
import { useToast } from "../components/ui/toast";
import type { SyncTask, SyncTaskStatus } from "../types";

type TasksPageProps = {
  onOpenTaskDetail?: (taskId: string) => void;
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

export function TasksPage({ onOpenTaskDetail }: TasksPageProps) {
  const {
    tasks,
    taskLoading,
    taskError,
    statusMap,
    refreshTasks,
    toggleTask,
    updateTaskSettings,
    runTask,
    deleteTask,
  } = useTasks();
  const { conflicts } = useConflicts();
  const { toast } = useToast();
  const [showModal, setShowModal] = useState(false);
  const [hideTestTasks, setHideTestTasks] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [stateFilter, setStateFilter] = useState("all");
  const [syncModeFilter, setSyncModeFilter] = useState("all");
  const [healthFilter, setHealthFilter] = useState("all");
  const [settingsTaskId, setSettingsTaskId] = useState<string | null>(null);
  const isDevMode = import.meta.env.DEV;
  const testTaskCount = tasks.filter((task) => Boolean(task.is_test)).length;
  const showTestToggle = isDevMode && testTaskCount > 0;
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
    deleteTask(task);
    toast("任务已删除", "danger");
    return true;
  };

  return (
    <section className="tasks-clarity animate-fade-up min-w-0 space-y-4">
      <TasksPageHeader
        showTestToggle={showTestToggle}
        hideTestTasks={hideTestTasks}
        onToggleTestTasks={() => setHideTestTasks((prev) => !prev)}
        onRefresh={refreshTasks}
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
      <div className="min-w-0">
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
          <div className="overflow-hidden rounded-lg border border-[#d7e4f5] bg-white shadow-[0_10px_28px_rgba(51,112,255,0.05)]">
            <div className="min-w-0 overflow-x-auto">
              <table className="w-full min-w-[1120px] table-fixed text-left text-sm">
                <thead className="border-b border-[#d7e4f5] bg-[#f8fbff] text-xs text-[#52657a]">
                  <tr>
                    <th className="w-[14%] px-4 py-3 font-medium">任务名称</th>
                    <th className="w-[13%] px-4 py-3 font-medium">本地目录</th>
                    <th className="w-[13%] px-4 py-3 font-medium">云端目录</th>
                    <th className="w-[9%] px-3 py-3 font-medium">同步模式</th>
                    <th className="w-[10%] px-4 py-3 font-medium">状态 / 健康</th>
                    <th className="w-[11%] px-4 py-3 font-medium">最近运行</th>
                    <th className="w-[4%] px-3 py-3 text-center font-medium">队列</th>
                    <th className="w-[4%] px-3 py-3 text-center font-medium">删除</th>
                    <th className="w-[4%] px-3 py-3 text-center font-medium">失败</th>
                    <th className="w-[4%] px-3 py-3 text-center font-medium">冲突</th>
                    <th className="w-[14%] px-4 py-3 text-right font-medium">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#edf3fb]">
                  {displayTasks.map((task) => {
                    const st = statusMap[task.id];
                    const conflictCount = Math.max(unresolvedConflictCountByTask[task.id] || 0, st?.conflict_files ?? 0);
                    const stateKey = taskStateKey(task, st);
                    const stateLabel = stateLabels[stateKey] || stateKey;
                    const health = deriveTaskHealth({
                      enabled: task.enabled,
                      state: st?.state,
                      lastFiles: st?.last_files,
                      conflictCount,
                      lastError: st?.last_error,
                      failedFiles: st?.failed_files,
                      deleteFailedFiles: st?.delete_failed_files,
                    });
                    const counts = taskPendingCounts(st, conflictCount);
                    const cloudPath = task.cloud_folder_name || task.cloud_folder_token || "-";
                    const progressState = computeTaskProgress(st);
                    const progress = progressState.progress;
                    const lastSyncTime = st?.finished_at ?? st?.started_at ?? task.last_run_at ?? null;

                    return (
                      <tr key={task.id} className="align-middle text-[#334762] transition hover:bg-[#f8fbff]">
                          <td className="px-4 py-3">
                            <div className="flex min-w-0 items-center gap-3">
                              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#eaf2ff] text-[#3370ff]">
                                <IconFolder className="h-4 w-4" />
                              </span>
                              <div className="min-w-0">
                                <p className="truncate font-semibold text-[#102033]" title={task.name || task.local_path}>
                                  {task.name || "未命名任务"}
                                </p>
                                <p className="mt-0.5 truncate font-mono text-[11px] text-[#6b7f96]" title={task.id}>
                                  ID: {summarizePath(task.id, 1, 20)}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="truncate px-4 py-3 font-mono text-xs" title={task.local_path}>
                            {summarizePath(task.local_path, 3, 54)}
                          </td>
                          <td className="truncate px-4 py-3 text-xs" title={task.cloud_folder_token}>
                            {summarizePath(cloudPath, 3, 44)}
                          </td>
                          <td className="px-3 py-3">
                            <span className="inline-flex whitespace-nowrap items-center gap-1 rounded-md border border-[#bfd8ff] bg-[#eef5ff] px-1.5 py-1 text-xs font-semibold text-[#3370ff]">
                              <ModeIcon mode={task.sync_mode} className="h-3.5 w-3.5" />
                              {modeLabels[task.sync_mode] || task.sync_mode}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex flex-col items-start gap-1.5">
                              <StatusPill label={stateLabel} tone={stateTones[stateKey] || "neutral"} dot={stateKey === "running"} />
                              {health.label !== stateLabel ? (
                                <span className={`text-xs ${health.tone === "danger" ? "text-[#be123c]" : health.tone === "warning" ? "text-[#b45309]" : health.tone === "success" ? "text-[#047857]" : "text-[#52657A]"}`}>
                                  {health.label}
                                </span>
                              ) : null}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="min-w-0 text-xs">
                              <p className="truncate text-[#334762]">{lastSyncTime ? formatTimestamp(lastSyncTime) : "尚未运行"}</p>
                              {progress !== null ? (
                                <div className="mt-2 flex items-center gap-2">
                                  <span className="w-8 text-[#52657A]">{progress}%</span>
                                  <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#dce8f8]">
                                    <span className="block h-full rounded-full bg-[#3370ff]" style={{ width: `${progress}%` }} />
                                  </span>
                                </div>
                              ) : null}
                            </div>
                          </td>
                          <td className="px-3 py-3 text-center"><TaskCountCell value={counts.queued} tone={counts.queued > 0 ? "warning" : "neutral"} /></td>
                          <td className="px-3 py-3 text-center"><TaskCountCell value={counts.deleteTotal} tone={counts.deleteTotal > 0 ? "warning" : "neutral"} /></td>
                          <td className="px-3 py-3 text-center"><TaskCountCell value={counts.failed} tone={counts.failed > 0 ? "danger" : "neutral"} /></td>
                          <td className="px-3 py-3 text-center"><TaskCountCell value={counts.conflict} tone={counts.conflict > 0 ? "danger" : "neutral"} /></td>
                          <td className="px-4 py-3">
                            <div className="flex items-center justify-end gap-1">
                              {onOpenTaskDetail ? (
                                <button
                                  aria-label="查看任务详情"
                                  className="inline-flex h-[30px] w-[30px] items-center justify-center rounded-lg border border-[#c9d8ec] text-[#3370ff] hover:bg-[#eef5ff]"
                                  onClick={() => onOpenTaskDetail(task.id)}
                                  title="查看任务详情"
                                  type="button"
                                >
                                  <IconFolder className="h-3.5 w-3.5" />
                                </button>
                              ) : null}
                              <button
                                aria-label={health.isRunning ? "同步中" : "立即同步"}
                                className="inline-flex h-[30px] w-[30px] items-center justify-center rounded-full border border-[#bfd8ff] text-[#3370ff] hover:bg-[#eef5ff] disabled:opacity-50"
                                onClick={() => {
                                  runTask(task);
                                  toast("同步已触发", "info");
                                }}
                                disabled={health.isRunning}
                                type="button"
                                title={health.isRunning ? "同步中" : "立即同步"}
                              >
                                <IconPlay className="h-3.5 w-3.5" />
                              </button>
                              <button
                                aria-label={task.enabled ? "停用任务" : "启用任务"}
                                aria-checked={task.enabled}
                                className={`relative h-5 w-10 shrink-0 rounded-full border p-0.5 shadow-inner transition ${task.enabled ? "border-[#3370ff] bg-[#3370ff]" : "border-[#afc1d5] bg-[#c9d8ec]"}`}
                                onClick={() => {
                                  toggleTask(task);
                                  toast(task.enabled ? "已停用" : "已启用", "info");
                                }}
                                role="switch"
                                title={task.enabled ? "停用任务" : "启用任务"}
                                type="button"
                              >
                                <span className={`block h-3.5 w-3.5 rounded-full bg-white shadow-sm transition-transform ${task.enabled ? "translate-x-5" : "translate-x-0"}`} />
                              </button>
                              <button
                                aria-expanded={settingsTaskId === task.id}
                                aria-haspopup="dialog"
                                aria-label="打开任务设置"
                                className={`inline-flex h-[30px] w-[30px] items-center justify-center rounded-lg border transition ${settingsTaskId === task.id ? "border-[#3370ff] bg-[#eef5ff] text-[#3370ff]" : "border-[#c9d8ec] text-[#52657A] hover:bg-[#f6faff] hover:text-[#3370ff]"}`}
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
              className="flex min-w-0 items-center justify-between gap-3 border-t border-[#edf3fb] px-4 py-3 text-xs font-medium text-[#52657A]"
              data-task-table-footer="true"
            >
              <span>
                {hasActiveFilters ? `显示 ${displayTasks.length} / 共 ${visibleTasksBeforeFilters.length} 个任务` : `共 ${displayTasks.length} 个任务`}
              </span>
              {hasActiveFilters ? <span className="text-[#3370ff]">已应用筛选</span> : null}
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
              await updateTaskSettings({ id: settingsTask.id, patch });
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
