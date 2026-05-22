/* ------------------------------------------------------------------ */
/*  同步任务管理页面                                                     */
/* ------------------------------------------------------------------ */

import { useMemo, useState } from "react";
import { useTasks } from "../hooks/useTasks";
import { useConflicts } from "../hooks/useConflicts";
import { NewTaskModal } from "../components/NewTaskModal";
import { TaskCard } from "../components/tasks/TaskCard";
import { TasksEmptyState } from "../components/tasks/TasksEmptyState";
import { TasksPageHeader } from "../components/tasks/TasksPageHeader";
import { parseDeleteGraceMinutes } from "../lib/taskManagement";
import { confirm } from "../components/ui/confirm-dialog";
import { useToast } from "../components/ui/toast";
import type { SyncTask } from "../types";

export function TasksPage() {
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
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [localSyncModeMap, setLocalSyncModeMap] = useState<Record<string, string>>({});
  const [localUpdateModeMap, setLocalUpdateModeMap] = useState<Record<string, string>>({});
  const [localMdSyncModeMap, setLocalMdSyncModeMap] = useState<Record<string, string>>({});
  const [localDeletePolicyMap, setLocalDeletePolicyMap] = useState<Record<string, "off" | "safe" | "strict">>({});
  const [localDeleteGraceMap, setLocalDeleteGraceMap] = useState<Record<string, string>>({});
  const [expandedPaths, setExpandedPaths] = useState<Record<string, boolean>>({});
  const isDevMode = import.meta.env.DEV;
  const testTaskCount = tasks.filter((task) => Boolean(task.is_test)).length;
  const showTestToggle = isDevMode && testTaskCount > 0;
  const displayTasks = hideTestTasks ? tasks.filter((task) => !task.is_test) : tasks;
  const pathKey = (taskId: string, side: "local" | "cloud") => `${taskId}:${side}`;
  const unresolvedConflictCountByTask = useMemo(() => {
    const mapped: Record<string, number> = {};
    for (const task of tasks) {
      mapped[task.id] = conflicts.filter(
        (conflict) => !conflict.resolved && conflict.local_path.startsWith(task.local_path)
      ).length;
    }
    return mapped;
  }, [conflicts, tasks]);

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
    <section className="space-y-6 animate-fade-up">
      <TasksPageHeader
        showTestToggle={showTestToggle}
        hideTestTasks={hideTestTasks}
        onToggleTestTasks={() => setHideTestTasks((prev) => !prev)}
        onRefresh={refreshTasks}
        onCreate={() => setShowModal(true)}
      />

      {taskError ? <p className="text-sm text-rose-400">错误：{taskError}</p> : null}

      {/* Task list */}
      <div className="space-y-4">
        {taskLoading ? (
          <div className="space-y-4">{[1, 2, 3].map((i) => <div key={i} className="h-48 animate-pulse rounded-2xl bg-zinc-800/30" />)}</div>
        ) : displayTasks.length === 0 ? (
          <TasksEmptyState
            hasAnyTasks={tasks.length > 0}
            hideTestTasks={hideTestTasks}
            testTaskCount={testTaskCount}
          />
        ) : (
          displayTasks.map((task) => {
            const st = statusMap[task.id];
            const conflictCount = Math.max(unresolvedConflictCountByTask[task.id] || 0, st?.conflict_files ?? 0);
            const isExpanded = Boolean(expanded[task.id]);
            const effectiveSyncMode = localSyncModeMap[task.id] || task.sync_mode;
            const effectiveMdSyncMode = (localMdSyncModeMap[task.id] ||
              task.md_sync_mode ||
              "enhanced") as "enhanced" | "download_only" | "doc_only";
            const effectiveDeletePolicy = (localDeletePolicyMap[task.id] ||
              (task.delete_policy as "off" | "safe" | "strict") ||
              "safe") as "off" | "safe" | "strict";
            const effectiveDeleteGrace = localDeleteGraceMap[task.id] ?? String(task.delete_grace_minutes ?? 30);

            return (
              <TaskCard
                key={task.id}
                task={task}
                status={st}
                conflictCount={conflictCount}
                expanded={isExpanded}
                onToggleExpanded={() => setExpanded((prev) => ({ ...prev, [task.id]: !prev[task.id] }))}
                localPathExpanded={Boolean(expandedPaths[pathKey(task.id, "local")])}
                cloudPathExpanded={Boolean(expandedPaths[pathKey(task.id, "cloud")])}
                onTogglePath={(side) =>
                  setExpandedPaths((prev) => ({
                    ...prev,
                    [pathKey(task.id, side)]: !prev[pathKey(task.id, side)],
                  }))
                }
                syncModeValue={effectiveSyncMode}
                updateModeValue={localUpdateModeMap[task.id] || task.update_mode || "auto"}
                mdSyncModeValue={effectiveMdSyncMode}
                deletePolicyValue={effectiveDeletePolicy}
                deleteGraceValue={effectiveDeleteGrace}
                onSyncModeChange={(value) =>
                  setLocalSyncModeMap((prev) => ({ ...prev, [task.id]: value }))
                }
                onUpdateModeChange={(value) =>
                  setLocalUpdateModeMap((prev) => ({ ...prev, [task.id]: value }))
                }
                onMdSyncModeChange={(value) =>
                  setLocalMdSyncModeMap((prev) => ({ ...prev, [task.id]: value }))
                }
                onDeletePolicyChange={(value) =>
                  setLocalDeletePolicyMap((prev) => ({ ...prev, [task.id]: value }))
                }
                onDeleteGraceChange={(value) =>
                  setLocalDeleteGraceMap((prev) => ({ ...prev, [task.id]: value }))
                }
                onApplySyncMode={() => {
                  updateSyncMode({ id: task.id, sync_mode: effectiveSyncMode });
                  toast("同步模式已更新", "success");
                }}
                onApplyUpdateMode={() => {
                  updateMode({
                    id: task.id,
                    update_mode: localUpdateModeMap[task.id] || task.update_mode || "auto",
                  });
                  toast("更新模式已更新", "success");
                }}
                onApplyMdSyncMode={() => {
                  updateMdSyncMode({
                    id: task.id,
                    md_sync_mode: effectiveMdSyncMode,
                  });
                  toast("MD 上传模式已更新", "success");
                }}
                onApplyDeletePolicy={() => {
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
                onRun={() => {
                  runTask(task);
                  toast("同步已触发", "info");
                }}
                onToggleEnabled={() => {
                  toggleTask(task);
                  toast(task.enabled ? "已停用" : "已启用", "info");
                }}
                onDelete={() => handleDelete(task)}
              />
            );
          })
        )}
      </div>

      <NewTaskModal open={showModal} onClose={() => setShowModal(false)} onCreated={refreshTasks} />
    </section>
  );
}
