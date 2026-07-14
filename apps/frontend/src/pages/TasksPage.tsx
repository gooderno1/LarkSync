/* ------------------------------------------------------------------ */
/*  同步任务管理页面                                                     */
/* ------------------------------------------------------------------ */

import { Fragment, useMemo, useState } from "react";
import { useTasks } from "../hooks/useTasks";
import { useConflicts } from "../hooks/useConflicts";
import { NewTaskModal } from "../components/NewTaskModal";
import { TasksEmptyState } from "../components/tasks/TasksEmptyState";
import { TasksPageHeader } from "../components/tasks/TasksPageHeader";
import { StatusPill } from "../components/StatusPill";
import {
  IconFolder,
  IconMoreHorizontal,
  IconPlay,
  IconTrash,
  ModeIcon,
} from "../components/Icons";
import {
  mdSyncModeLabels,
  modeLabels,
  stateLabels,
  stateTones,
  syncModeSupportsUpload,
} from "../lib/constants";
import { computeTaskProgress } from "../lib/progress";
import {
  deletePolicyLabel,
  deriveTaskHealth,
  parseDeleteGraceMinutes,
  summarizePath,
} from "../lib/taskManagement";
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
    updateSyncMode,
    updateMode,
    updateMdSyncMode,
    updateDeletePolicy,
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
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [localSyncModeMap, setLocalSyncModeMap] = useState<Record<string, string>>({});
  const [localUpdateModeMap, setLocalUpdateModeMap] = useState<Record<string, string>>({});
  const [localMdSyncModeMap, setLocalMdSyncModeMap] = useState<Record<string, string>>({});
  const [localDeletePolicyMap, setLocalDeletePolicyMap] = useState<Record<string, "off" | "safe" | "strict">>({});
  const [localDeleteGraceMap, setLocalDeleteGraceMap] = useState<Record<string, string>>({});
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

  const handleDelete = async (task: SyncTask) => {
    const ok = await confirm({
      title: "确认删除任务",
      description: `即将删除任务「${task.name || task.local_path}」，此操作不可恢复。`,
      confirmLabel: "删除",
      tone: "danger",
    });
    if (ok) {
      deleteTask(task);
      toast("任务已删除", "danger");
    }
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
                    const isExpanded = Boolean(expanded[task.id]);
                    const effectiveSyncMode = localSyncModeMap[task.id] || task.sync_mode;
                    const effectiveUpdateMode = localUpdateModeMap[task.id] || task.update_mode || "auto";
                    const effectiveMdSyncMode = (localMdSyncModeMap[task.id] ||
                      task.md_sync_mode ||
                      "enhanced") as "enhanced" | "download_only" | "doc_only";
                    const effectiveDeletePolicy = (localDeletePolicyMap[task.id] ||
                      (task.delete_policy as "off" | "safe" | "strict") ||
                      "safe") as "off" | "safe" | "strict";
                    const effectiveDeleteGrace = localDeleteGraceMap[task.id] ?? String(task.delete_grace_minutes ?? 30);
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
                    const taskUploadEnabled = syncModeSupportsUpload(effectiveSyncMode);

                    return (
                      <Fragment key={task.id}>
                        <tr className="align-middle text-[#334762] transition hover:bg-[#f8fbff]">
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
                              <ModeIcon mode={effectiveSyncMode} className="h-3.5 w-3.5" />
                              {modeLabels[effectiveSyncMode] || effectiveSyncMode}
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
                                aria-expanded={isExpanded}
                                aria-label={isExpanded ? "收起任务设置" : "展开任务设置"}
                                className={`inline-flex h-[30px] w-[30px] items-center justify-center rounded-lg border transition ${isExpanded ? "border-[#3370ff] bg-[#eef5ff] text-[#3370ff]" : "border-[#c9d8ec] text-[#52657A] hover:bg-[#f6faff] hover:text-[#3370ff]"}`}
                                onClick={() => setExpanded((prev) => ({ ...prev, [task.id]: !prev[task.id] }))}
                                type="button"
                                title={isExpanded ? "收起任务设置" : "展开任务设置"}
                              >
                                <IconMoreHorizontal className="h-4 w-4" />
                              </button>
                            </div>
                          </td>
                        </tr>

                        {isExpanded ? (
                          <tr>
                            <td colSpan={11} className="bg-[#f8fbff] px-4 py-4">
                              <div className="grid grid-cols-4 gap-4">
                                <div className="rounded-xl border border-[#d7e4f5] bg-white p-4">
                                  <p className="text-xs font-semibold uppercase tracking-widest text-[#6b7f96]">同步模式</p>
                                  <div className="mt-3 flex flex-wrap items-center gap-2">
                                    <select
                                      className="rounded-lg border border-[#c9d8ec] bg-white px-3 py-2 text-xs text-[#334762] outline-none focus:border-[#3370ff]"
                                      value={effectiveSyncMode}
                                      onChange={(e) => setLocalSyncModeMap((prev) => ({ ...prev, [task.id]: e.target.value }))}
                                    >
                                      <option value="bidirectional">双向同步</option>
                                      <option value="download_only">仅下载</option>
                                      <option value="upload_only">仅上传</option>
                                    </select>
                                    <button
                                      className="rounded-lg border border-[#c9d8ec] px-3 py-2 text-xs font-medium text-[#3370ff] hover:bg-[#eef5ff]"
                                      onClick={() => {
                                        updateSyncMode({ id: task.id, sync_mode: effectiveSyncMode });
                                        toast("同步模式已更新", "success");
                                      }}
                                      type="button"
                                    >
                                      应用
                                    </button>
                                  </div>
                                </div>

                                <div className="rounded-xl border border-[#d7e4f5] bg-white p-4">
                                  <p className="text-xs font-semibold uppercase tracking-widest text-[#6b7f96]">更新模式</p>
                                  <div className="mt-3 flex flex-wrap items-center gap-2">
                                    <select
                                      className="rounded-lg border border-[#c9d8ec] bg-white px-3 py-2 text-xs text-[#334762] outline-none focus:border-[#3370ff]"
                                      value={effectiveUpdateMode}
                                      onChange={(e) => setLocalUpdateModeMap((prev) => ({ ...prev, [task.id]: e.target.value }))}
                                    >
                                      <option value="auto">自动</option>
                                      <option value="partial">局部</option>
                                      <option value="full">全量</option>
                                    </select>
                                    <button
                                      className="rounded-lg border border-[#c9d8ec] px-3 py-2 text-xs font-medium text-[#3370ff] hover:bg-[#eef5ff]"
                                      onClick={() => {
                                        updateMode({ id: task.id, update_mode: effectiveUpdateMode });
                                        toast("更新模式已更新", "success");
                                      }}
                                      type="button"
                                    >
                                      应用
                                    </button>
                                  </div>
                                </div>

                                <div className="rounded-xl border border-[#d7e4f5] bg-white p-4">
                                  <p className="text-xs font-semibold uppercase tracking-widest text-[#6b7f96]">MD 上传模式</p>
                                  {taskUploadEnabled ? (
                                    <div className="mt-3 flex flex-wrap items-center gap-2">
                                      <select
                                        className="rounded-lg border border-[#c9d8ec] bg-white px-3 py-2 text-xs text-[#334762] outline-none focus:border-[#3370ff]"
                                        value={effectiveMdSyncMode}
                                        onChange={(e) =>
                                          setLocalMdSyncModeMap((prev) => ({ ...prev, [task.id]: e.target.value }))
                                        }
                                      >
                                        <option value="enhanced">增强 MD 上传</option>
                                        <option value="download_only">MD 仅下载</option>
                                        <option value="doc_only">仅云文档上传</option>
                                      </select>
                                      <button
                                        className="rounded-lg border border-[#c9d8ec] px-3 py-2 text-xs font-medium text-[#3370ff] hover:bg-[#eef5ff]"
                                        onClick={() => {
                                          updateMdSyncMode({ id: task.id, md_sync_mode: effectiveMdSyncMode });
                                          toast("MD 上传模式已更新", "success");
                                        }}
                                        type="button"
                                      >
                                        应用
                                      </button>
                                    </div>
                                  ) : (
                                    <p className="mt-3 text-xs leading-5 text-[#6b7f96]">当前模式不执行本地 Markdown 上行。</p>
                                  )}
                                  <p className="mt-2 text-[11px] leading-5 text-[#6b7f96]">
                                    {taskUploadEnabled ? mdSyncModeLabels[effectiveMdSyncMode] : "仅下载任务无需配置 MD 上传。"}
                                  </p>
                                </div>

                                <div className="rounded-xl border border-[#d7e4f5] bg-white p-4">
                                  <p className="text-xs font-semibold uppercase tracking-widest text-[#6b7f96]">删除策略</p>
                                  <div className="mt-3 flex flex-wrap items-center gap-2">
                                    <select
                                      className="rounded-lg border border-[#c9d8ec] bg-white px-3 py-2 text-xs text-[#334762] outline-none focus:border-[#3370ff]"
                                      value={effectiveDeletePolicy}
                                      onChange={(e) =>
                                        setLocalDeletePolicyMap((prev) => ({
                                          ...prev,
                                          [task.id]: e.target.value as "off" | "safe" | "strict",
                                        }))
                                      }
                                    >
                                      <option value="off">关闭</option>
                                      <option value="safe">安全</option>
                                      <option value="strict">严格</option>
                                    </select>
                                    <input
                                      className="w-20 rounded-lg border border-[#c9d8ec] bg-white px-3 py-2 text-xs text-[#334762] outline-none disabled:bg-[#edf3fb] disabled:text-[#9fb2c8] focus:border-[#3370ff]"
                                      type="number"
                                      min="0"
                                      step="1"
                                      value={effectiveDeleteGrace}
                                      onChange={(e) => setLocalDeleteGraceMap((prev) => ({ ...prev, [task.id]: e.target.value }))}
                                      disabled={effectiveDeletePolicy === "strict"}
                                    />
                                    <button
                                      className="rounded-lg border border-[#c9d8ec] px-3 py-2 text-xs font-medium text-[#3370ff] hover:bg-[#eef5ff]"
                                      onClick={() => {
                                        updateDeletePolicy({
                                          id: task.id,
                                          delete_policy: effectiveDeletePolicy,
                                          delete_grace_minutes: parseDeleteGraceMinutes(
                                            effectiveDeletePolicy,
                                            effectiveDeleteGrace,
                                            task.delete_grace_minutes ?? 30
                                          ),
                                        });
                                        toast("删除策略已更新", "success");
                                      }}
                                      type="button"
                                    >
                                      应用
                                    </button>
                                  </div>
                                  <p className="mt-2 text-[11px] leading-5 text-[#6b7f96]">{deletePolicyLabel(effectiveDeletePolicy)}</p>
                                </div>

                                <div className="col-span-4 rounded-xl border border-[#d7e4f5] bg-white p-4">
                                  <div className="flex flex-wrap items-center justify-between gap-3">
                                    <div className="min-w-0 text-xs text-[#52657A]">
                                      <p className="font-semibold text-[#102033]">高级信息</p>
                                      <p className="mt-1 break-all font-mono">base_path：{task.base_path || "默认同本地目录"}</p>
                                      {st ? (
                                        <p className="mt-1">
                                          处理 {progressState.processed}/{progressState.effectiveTotal}，完成 {st.completed_files}，跳过 {st.skipped_files}，删除 {st.deleted_files}
                                        </p>
                                      ) : null}
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                      <button
                                        className="rounded-lg border border-[#f43f5e]/40 px-3 py-2 text-xs font-semibold text-[#be123c] hover:bg-[#fff1f2]"
                                        onClick={() => handleDelete(task)}
                                        type="button"
                                      >
                                        <IconTrash className="mr-1 inline h-3.5 w-3.5" />
                                        删除任务
                                      </button>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </td>
                          </tr>
                        ) : null}
                      </Fragment>
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
    </section>
  );
}
