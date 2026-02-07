/* ------------------------------------------------------------------ */
/*  同步任务管理页面                                                     */
/* ------------------------------------------------------------------ */

import { useState } from "react";
import { useTasks } from "../hooks/useTasks";
import { formatTimestamp } from "../lib/formatters";
import { modeLabels, updateModeLabels, stateLabels, stateTones } from "../lib/constants";
import { StatusPill } from "../components/StatusPill";
import { ModeIcon, IconRefresh, IconPlus, IconPlay, IconTrash, IconFolder, IconCloud, IconChevronDown, IconChevronRight } from "../components/Icons";
import { NewTaskModal } from "../components/NewTaskModal";
import { confirm } from "../components/ui/confirm-dialog";
import { useToast } from "../components/ui/toast";
import { ThemeToggle } from "../components/ThemeToggle";

export function TasksPage() {
  const { tasks, taskLoading, taskError, statusMap, refreshTasks, toggleTask, updateSyncMode, updateMode, runTask, deleteTask } = useTasks();
  const { toast } = useToast();
  const [showModal, setShowModal] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [localSyncModeMap, setLocalSyncModeMap] = useState<Record<string, string>>({});
  const [localUpdateModeMap, setLocalUpdateModeMap] = useState<Record<string, string>>({});

  const handleDelete = async (task: typeof tasks[0]) => {
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
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
        <div>
          <h2 className="text-lg font-semibold text-zinc-50">同步任务</h2>
          <p className="mt-1 text-xs text-zinc-400">管理任务的同步模式、更新策略与执行状态。</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800" onClick={refreshTasks} type="button">
            <IconRefresh className="h-3.5 w-3.5" /> 刷新
          </button>
          <button className="inline-flex items-center gap-2 rounded-lg bg-[#3370FF] px-4 py-2 text-xs font-semibold text-white hover:bg-[#3370FF]/80" onClick={() => setShowModal(true)} type="button">
            <IconPlus className="h-3.5 w-3.5" /> 新建任务
          </button>
          <ThemeToggle />
        </div>
      </div>

      {taskError ? <p className="text-sm text-rose-400">错误：{taskError}</p> : null}

      {/* Task list */}
      <div className="space-y-4">
        {taskLoading ? (
          <div className="space-y-4">{[1, 2, 3].map((i) => <div key={i} className="h-48 animate-pulse rounded-2xl bg-zinc-800/30" />)}</div>
        ) : tasks.length === 0 ? (
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 py-16 text-center">
            <IconPlus className="mx-auto h-12 w-12 text-zinc-700" />
            <p className="mt-4 text-sm text-zinc-500">暂无同步任务，请点击「新建任务」。</p>
          </div>
        ) : (
          tasks.map((task) => {
            const st = statusMap[task.id];
            const stateKey = !task.enabled ? "paused" : st?.state || "idle";
            const progress = st && st.total_files > 0 ? Math.round((st.completed_files / st.total_files) * 100) : null;
            const isRunning = st?.state === "running";
            const isExpanded = Boolean(expanded[task.id]);
            const lastSyncTime = st?.finished_at ?? st?.started_at ?? null;

            return (
              <div key={task.id} className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
                {/* Top row */}
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-3">
                      <StatusPill label={stateLabels[stateKey] || stateKey} tone={stateTones[stateKey] || "neutral"} dot />
                      <p className="text-lg font-semibold text-zinc-50">{task.name || "未命名任务"}</p>
                    </div>
                    <p className="text-xs text-zinc-500">任务 ID：{task.id}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-400">
                    <span className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-3 py-1">
                      <ModeIcon mode={task.sync_mode} className="h-3.5 w-3.5" />
                      {modeLabels[task.sync_mode] || task.sync_mode}
                    </span>
                    <span className="rounded-lg border border-zinc-700 px-3 py-1">
                      更新：{updateModeLabels[task.update_mode || "auto"]}
                    </span>
                  </div>
                </div>

                {/* Path visualizer */}
                <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
                  <div className="grid gap-4 lg:grid-cols-[1fr_auto_1fr]">
                    <div className="flex items-center gap-3">
                      <div className="rounded-xl bg-emerald-500/20 p-2 text-emerald-300"><IconFolder className="h-4 w-4" /></div>
                      <div className="min-w-0">
                        <p className="text-[11px] uppercase tracking-widest text-zinc-500">本地目录</p>
                        <p className="mt-1 truncate font-mono text-sm text-zinc-200">{task.local_path}</p>
                      </div>
                    </div>
                    <div className="flex items-center justify-center">
                      <span className="rounded-full border border-zinc-700 bg-zinc-900 p-2 text-zinc-400">
                        <ModeIcon mode={task.sync_mode} className="h-4 w-4" />
                      </span>
                    </div>
                    <div className="flex items-center justify-end gap-3 text-right">
                      <div className="min-w-0">
                        <p className="text-[11px] uppercase tracking-widest text-zinc-500">云端目录</p>
                        <p className="mt-1 truncate text-sm text-zinc-200" title={task.cloud_folder_token}>{task.cloud_folder_name || task.cloud_folder_token}</p>
                      </div>
                      <div className="rounded-xl bg-[#3370FF]/15 p-2 text-[#3370FF]"><IconCloud className="h-4 w-4" /></div>
                    </div>
                  </div>
                  {task.base_path ? <p className="mt-3 text-xs text-zinc-500">base_path：{task.base_path}</p> : null}
                </div>

                {/* Meta */}
                <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-zinc-500">
                  <span>最近同步：{lastSyncTime ? formatTimestamp(lastSyncTime) : "暂无"}</span>
                  {st ? <span>完成 {st.completed_files}/{st.total_files}，失败 {st.failed_files}，跳过 {st.skipped_files}</span> : null}
                  {progress !== null ? <span>完成率：{progress}%</span> : null}
                </div>
                {st?.last_error ? <p className="mt-2 text-xs text-rose-400">错误：{st.last_error}</p> : null}
                {progress !== null ? (
                  <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
                    <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${progress}%` }} />
                  </div>
                ) : null}

                {/* Action buttons */}
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <button className="inline-flex items-center gap-2 rounded-lg bg-emerald-500/20 px-4 py-2 text-xs font-semibold text-emerald-300 transition hover:bg-emerald-500/30 disabled:opacity-50" onClick={() => { runTask(task); toast("同步已触发", "info"); }} disabled={isRunning} type="button">
                    <IconPlay className="h-3.5 w-3.5" /> {isRunning ? "同步中" : "立即同步"}
                  </button>
                  <button className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800" onClick={() => { toggleTask(task); toast(task.enabled ? "已停用" : "已启用", "info"); }} type="button">
                    {task.enabled ? "停用" : "启用"}
                  </button>
                  <button className="inline-flex items-center gap-2 rounded-lg border border-rose-500/40 px-4 py-2 text-xs font-medium text-rose-300 transition hover:bg-rose-500/10" onClick={() => handleDelete(task)} type="button">
                    <IconTrash className="h-3.5 w-3.5" /> 删除
                  </button>
                  <button
                    className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
                    onClick={() => setExpanded((prev) => ({ ...prev, [task.id]: !prev[task.id] }))}
                    type="button"
                  >
                    {isExpanded ? <IconChevronDown className="h-3 w-3" /> : <IconChevronRight className="h-3 w-3" />}
                    {isExpanded ? "收起管理" : "任务管理"}
                  </button>
                </div>

                {/* Expanded management */}
                {isExpanded ? (
                  <div className="mt-4 grid gap-4 lg:grid-cols-2">
                    <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
                      <p className="text-xs uppercase tracking-widest text-zinc-500">同步模式</p>
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <select
                          className="rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-xs text-zinc-200 outline-none"
                          value={localSyncModeMap[task.id] || task.sync_mode}
                          onChange={(e) => setLocalSyncModeMap((prev) => ({ ...prev, [task.id]: e.target.value }))}
                        >
                          <option value="bidirectional">双向同步</option>
                          <option value="download_only">仅下载</option>
                          <option value="upload_only">仅上传</option>
                        </select>
                        <button
                          className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
                          onClick={() => { updateSyncMode({ id: task.id, sync_mode: localSyncModeMap[task.id] || task.sync_mode }); toast("同步模式已更新", "success"); }}
                          type="button"
                        >
                          应用
                        </button>
                      </div>
                    </div>
                    <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
                      <p className="text-xs uppercase tracking-widest text-zinc-500">更新模式</p>
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <select
                          className="rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-xs text-zinc-200 outline-none"
                          value={localUpdateModeMap[task.id] || task.update_mode || "auto"}
                          onChange={(e) => setLocalUpdateModeMap((prev) => ({ ...prev, [task.id]: e.target.value }))}
                        >
                          <option value="auto">自动更新</option>
                          <option value="partial">局部更新</option>
                          <option value="full">全量覆盖</option>
                        </select>
                        <button
                          className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
                          onClick={() => { updateMode({ id: task.id, update_mode: localUpdateModeMap[task.id] || task.update_mode || "auto" }); toast("更新模式已更新", "success"); }}
                          type="button"
                        >
                          应用
                        </button>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })
        )}
      </div>

      <NewTaskModal open={showModal} onClose={() => setShowModal(false)} onCreated={refreshTasks} />
    </section>
  );
}
