import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTasks } from "../hooks/useTasks";
import { useConflicts } from "../hooks/useConflicts";
import { apiFetch } from "../lib/api";
import { buildTaskDiagnosticsQueryPath } from "../lib/taskDiagnosticsQuery";
import { computeTaskProgress } from "../lib/progress";
import { formatShortTime, formatTimestamp } from "../lib/formatters";
import { shortPath } from "../lib/logCenter";
import {
  deletePolicyLabel,
  deriveTaskHealth,
  summarizePath,
} from "../lib/taskManagement";
import {
  mdSyncModeLabels,
  modeLabels,
  stateLabels,
  stateTones,
  updateModeLabels,
} from "../lib/constants";
import { confirm } from "../components/ui/confirm-dialog";
import { useToast } from "../components/ui/toast";
import { StatusPill } from "../components/StatusPill";
import {
  IconChevronLeft,
  IconCloud,
  IconCopy,
  IconFolder,
  IconPlay,
  IconRefresh,
  IconTrash,
  ModeIcon,
} from "../components/Icons";
import type { SyncLogEntry, SyncTask, SyncTaskDiagnostics, SyncTaskRunSummary, SyncTaskStatus, Tone } from "../types";

type TaskDetailPageProps = {
  taskId: string;
  onBack: () => void;
};

const queueStatuses = new Set(["queued", "creating", "created", "reimporting"]);

function countLastFileStatus(status: SyncTaskStatus | undefined, matcher: (value: string) => boolean): number {
  return (status?.last_files || []).filter((item) => matcher(item.status)).length;
}

function runTone(state?: string | null): Tone {
  if (state === "running") return "info";
  if (state === "success" || state === "idle") return "success";
  if (state === "failed" || state === "cancelled") return "danger";
  return "neutral";
}

function buildProblemSummary(status: SyncTaskStatus | undefined, conflictCount: number, problems: SyncLogEntry[]) {
  const queueCount = countLastFileStatus(status, (value) => queueStatuses.has(value));
  const failed = status?.failed_files ?? 0;
  const deleteFailed = status?.delete_failed_files ?? 0;
  const deletePending = Math.max(
    status?.delete_pending_files ?? 0,
    countLastFileStatus(status, (value) => value === "delete_pending")
  );
  const total = queueCount + failed + deleteFailed + deletePending + conflictCount + problems.length;
  return {
    total,
    rows: [
      { label: "队列", value: queueCount, tone: "warning" as Tone },
      { label: "失败", value: failed + deleteFailed, tone: "danger" as Tone },
      { label: "冲突", value: conflictCount, tone: "danger" as Tone },
      { label: "待删", value: deletePending, tone: "warning" as Tone },
    ],
  };
}

function RunMetric({ label, value, hint, tone = "info" }: { label: string; value: number; hint?: string; tone?: Tone }) {
  const color =
    tone === "success" ? "text-[#047857]" :
      tone === "warning" ? "text-[#b45309]" :
        tone === "danger" ? "text-[#be123c]" : "text-[#1d4ed8]";
  return (
    <div className="min-w-0 border-l border-[#d7e4f5] px-4 first:border-l-0 first:pl-0">
      <p className="text-xs text-[#6b7f96]">{label}</p>
      <p className={`mt-1 text-lg font-semibold ${color}`}>{value}</p>
      {hint ? <p className="mt-1 text-xs text-[#6b7f96]">{hint}</p> : null}
    </div>
  );
}

export function getRunPanelHeading(state: string | null | undefined, hasRun: boolean): string {
  if (state === "running") return "当前运行";
  if (hasRun) return "最近一次运行";
  return "运行状态";
}

function RunHistoryTable({ runs }: { runs: SyncTaskRunSummary[] }) {
  if (runs.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-[#c9d8ec] px-5 py-8 text-center text-sm text-[#6b7f96]">
        暂无运行历史。
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-[#d7e4f5]">
      <table className="w-full min-w-[720px] table-fixed text-left text-sm">
        <thead className="bg-[#f6faff] text-xs text-[#52657a]">
          <tr>
            <th className="w-[24%] px-4 py-3 font-medium">开始时间</th>
            <th className="w-[28%] px-4 py-3 font-medium">运行 ID</th>
            <th className="w-[14%] px-4 py-3 font-medium">状态</th>
            <th className="w-[14%] px-4 py-3 font-medium">上传/下载</th>
            <th className="w-[12%] px-4 py-3 font-medium">问题</th>
            <th className="w-[8%] px-4 py-3 font-medium">结果</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#edf3fb] bg-white">
          {runs.slice(0, 6).map((run) => (
            <tr key={run.run_id} className="text-[#334762]">
              <td className="px-4 py-3">{formatTimestamp(run.started_at)}</td>
              <td className="truncate px-4 py-3 font-mono text-xs" title={run.run_id}>{run.run_id}</td>
              <td className="px-4 py-3">
                <StatusPill label={stateLabels[run.state] || run.state} tone={runTone(run.state)} />
              </td>
              <td className="px-4 py-3">{run.counts.uploaded} / {run.counts.downloaded}</td>
              <td className="px-4 py-3">{run.problem_count}</td>
              <td className="px-4 py-3 text-[#047857]">{run.state === "success" ? "成功" : "--"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CurrentRunPanel({
  task,
  status,
  diagnostics,
}: {
  task: SyncTask;
  status?: SyncTaskStatus;
  diagnostics?: SyncTaskDiagnostics;
}) {
  const progressState = computeTaskProgress(status);
  const progress = progressState.progress ?? (status?.state === "success" ? 100 : 0);
  const activeRun = diagnostics?.selected_run ?? diagnostics?.recent_runs?.[0] ?? null;
  const hasRun = Boolean(activeRun || status?.current_run_id || task.last_run_at);
  const runId = status?.current_run_id || activeRun?.run_id || "暂无运行 ID";
  const stateKey = status?.state || activeRun?.state || "idle";
  const startedAt = status?.started_at ?? activeRun?.started_at ?? task.last_run_at ?? null;

  return (
    <section className="min-w-0 rounded-lg border border-[#d7e4f5] bg-white p-4 shadow-[0_10px_28px_rgba(51,112,255,0.05)]">
      <div className="flex min-w-0 items-center justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-[#102033]">{getRunPanelHeading(stateKey, hasRun)}</h2>
          <p className="mt-1 truncate text-xs text-[#6b7f96]" title={runId}>运行 ID：<span className="font-mono">{runId}</span></p>
        </div>
        <div className="shrink-0">
          <StatusPill label={stateLabels[stateKey] || stateKey} tone={stateTones[stateKey] || runTone(stateKey)} dot={stateKey === "running"} />
        </div>
      </div>

      {hasRun ? <div className="mt-4 grid min-w-0 grid-cols-[88px_minmax(0,1fr)] items-center gap-4">
        <div
          className="grid h-[88px] w-[88px] shrink-0 place-items-center rounded-full"
          style={{ background: `conic-gradient(#3370ff ${progress * 3.6}deg, #e5eef9 0deg)` }}
        >
          <div className="grid h-[68px] w-[68px] place-items-center rounded-full bg-white text-center">
            <div>
              <p className="text-xl font-semibold text-[#102033]">{progress}%</p>
              <p className="text-xs text-[#6b7f96]">{stateLabels[stateKey] || stateKey}</p>
            </div>
          </div>
        </div>

        <div className="min-w-0 flex-1">
          <div className="grid grid-cols-2 gap-2 text-sm text-[#52657a]">
            <p>开始时间：{formatTimestamp(startedAt)}</p>
            <p>最近活动：{formatShortTime(status?.finished_at ?? status?.started_at ?? task.last_run_at)}</p>
            <p>已处理：{progressState.processed}/{progressState.effectiveTotal}</p>
            <p>当前速度：--</p>
          </div>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-[#dce8f8]">
            <div className="h-full rounded-full bg-[#3370ff]" style={{ width: `${progress}%` }} />
          </div>
        </div>
      </div> : (
        <div className="mt-4 rounded-lg border border-dashed border-[#c9d8ec] bg-[#f8fbff] px-4 py-6 text-center">
          <p className="text-sm font-medium text-[#334762]">尚未运行</p>
          <p className="mt-1 text-xs text-[#6b7f96]">执行首次同步后，这里会显示进度与处理结果。</p>
        </div>
      )}

      <div data-run-metrics="true" className="mt-4 grid min-w-0 grid-cols-4 border-t border-[#edf3fb] pt-4">
        <RunMetric label="上传文件" value={status?.uploaded_files ?? activeRun?.counts.uploaded ?? 0} hint="本地到云端" tone="success" />
        <RunMetric label="下载文件" value={status?.downloaded_files ?? activeRun?.counts.downloaded ?? 0} hint="云端到本地" tone="info" />
        <RunMetric label="跳过文件" value={status?.skipped_files ?? activeRun?.counts.skipped ?? 0} hint="规则过滤" tone="warning" />
        <RunMetric label="错误文件" value={status?.failed_files ?? activeRun?.counts.failed ?? 0} hint="需排查" tone="danger" />
      </div>
    </section>
  );
}

export function TaskDetailPage({ taskId, onBack }: TaskDetailPageProps) {
  const {
    tasks,
    statusMap,
    taskLoading,
    refreshTasks,
    refreshStatus,
    runTask,
    toggleTask,
    deleteTask,
    resetLinks,
    resettingLinks,
  } = useTasks();
  const { conflicts } = useConflicts();
  const { toast } = useToast();
  const task = tasks.find((item) => item.id === taskId) || null;
  const status = statusMap[taskId];
  const taskConflicts = useMemo(
    () => (task ? conflicts.filter((conflict) => !conflict.resolved && conflict.local_path.startsWith(task.local_path)) : []),
    [conflicts, task]
  );

  const diagnosticsQuery = useQuery<SyncTaskDiagnostics>({
    queryKey: ["task-detail-diagnostics", taskId],
    queryFn: () =>
      apiFetch<SyncTaskDiagnostics>(
        buildTaskDiagnosticsQueryPath({
          selectedTaskId: taskId,
          selectedRunId: null,
          includeProblems: true,
          limit: 120,
        })
      ),
    enabled: Boolean(taskId),
    refetchInterval: status?.state === "running" ? 5_000 : 10_000,
  });

  if (taskLoading && !task) {
    return (
      <section className="animate-fade-up rounded-xl border border-[#d7e4f5] bg-white p-8 text-center text-sm text-[#6b7f96]">
        正在加载任务详情...
      </section>
    );
  }

  if (!task) {
    return (
      <section className="animate-fade-up rounded-xl border border-[#d7e4f5] bg-white p-8 text-center">
        <p className="text-base font-semibold text-[#102033]">未找到任务</p>
        <p className="mt-2 text-sm text-[#6b7f96]">任务可能已被删除或尚未同步到本地状态。</p>
        <button
          className="mt-5 rounded-lg bg-[#3370ff] px-4 py-2 text-sm font-semibold text-white"
          onClick={onBack}
          type="button"
        >
          返回同步任务
        </button>
      </section>
    );
  }

  const diagnostics = diagnosticsQuery.data;
  const cloudPath = task.cloud_folder_name || task.cloud_folder_token || "-";
  const health = deriveTaskHealth({
    enabled: task.enabled,
    state: status?.state,
    lastFiles: status?.last_files,
    conflictCount: taskConflicts.length,
    lastError: status?.last_error,
    failedFiles: status?.failed_files,
    deleteFailedFiles: status?.delete_failed_files,
  });
  const problems = diagnostics?.problems ?? [];
  const problemSummary = buildProblemSummary(status, taskConflicts.length, problems);
  const ignoredSubpaths = task.ignored_subpaths?.length ? task.ignored_subpaths : [".git/", "node_modules/", "__pycache__/", ".DS_Store"];

  const handleRunTask = () => {
    runTask(task);
    toast("同步已触发", "info");
  };

  const handleToggleTask = () => {
    toggleTask(task);
    toast(task.enabled ? "已停用" : "已启用", "info");
  };

  const handleCopyLocalPath = async () => {
    try {
      await navigator.clipboard.writeText(task.local_path);
      toast("本地路径已复制", "success");
    } catch {
      toast("复制路径失败", "danger");
    }
  };

  const handleDeleteTask = async () => {
    const ok = await confirm({
      title: "确认删除任务",
      description: `即将删除任务「${task.name || task.local_path}」，此操作不可恢复。`,
      confirmLabel: "删除",
      tone: "danger",
    });
    if (!ok) return;
    deleteTask(task);
    toast("任务已删除", "danger");
    onBack();
  };

  const handleResetLinks = async () => {
    const ok = await confirm({
      title: "重置同步映射",
      description: `任务：${task.name || task.id}\n\n此操作会清除该任务的 SyncLink 映射，下次同步将重新建立本地文件与飞书文件的对应关系。\n\n不会删除本地文件，也不会删除飞书文件。`,
      confirmLabel: "重置映射",
      tone: "warning",
    });
    if (!ok) return;
    try {
      const result = await resetLinks(task.id);
      toast(`已清除 ${result.deleted_links} 条同步映射`, "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "重置失败", "danger");
    }
  };

  const activeProblemRows = problemSummary.rows.filter((row) => row.value > 0);

  return (
    <section className="tasks-clarity animate-fade-up min-w-0">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-[#d7e4f5] bg-white px-5 py-4 shadow-[0_12px_34px_rgba(51,112,255,0.06)]">
        <div className="flex min-w-0 items-center gap-3">
          <button aria-label="返回同步任务" className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-[#c9d8ec] text-[#3370ff] hover:bg-[#eef5ff]" onClick={onBack} type="button">
            <IconChevronLeft className="h-4 w-4" />
          </button>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="truncate text-xl font-semibold text-[#102033]">{task.name || "未命名任务"}</h1>
              <StatusPill label={health.label} tone={health.tone} dot={health.isRunning} />
            </div>
            <p className="mt-1 truncate text-xs text-[#52657a]">任务 ID：<span className="font-mono">{task.id}</span> · 创建于 {formatTimestamp(task.created_at)}</p>
          </div>
        </div>
        <button className="inline-flex items-center gap-2 rounded-lg border border-[#c9d8ec] bg-white px-4 py-2 text-xs font-semibold text-[#334762] hover:bg-[#f6faff]" onClick={() => { refreshTasks(); refreshStatus(); void diagnosticsQuery.refetch(); }} type="button">
          <IconRefresh className="h-3.5 w-3.5" />刷新
        </button>
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)_300px] items-start gap-5">
        <div className="min-w-0 space-y-4">
          <section className="rounded-xl border border-[#d7e4f5] bg-white p-5 shadow-[0_12px_34px_rgba(51,112,255,0.05)]">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-[#102033]">同步关系</h2>
                <p className="mt-1 text-xs text-[#52657a]">本地目录与飞书目录之间的内容流向。</p>
              </div>
              <span className="rounded-full bg-[#ecfdf5] px-3 py-1 text-xs font-medium text-[#047857]">映射正常</span>
            </div>
            <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-4 rounded-xl border border-[#edf3fb] bg-[#f8fbff] p-4">
              <div className="min-w-0">
                <p className="flex items-center gap-2 text-xs font-semibold text-[#52657a]"><IconFolder className="h-4 w-4 text-[#3370ff]" />本地目录</p>
                <p className="mt-2 truncate font-mono text-sm font-medium text-[#102033]" title={task.local_path}>{shortPath(task.local_path, 76)}</p>
                <button className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-[#3370ff]" onClick={handleCopyLocalPath} type="button"><IconCopy className="h-3.5 w-3.5" />复制路径</button>
              </div>
              <div className="flex min-w-[116px] flex-col items-center gap-1 text-center text-[#3370ff]">
                <ModeIcon mode={task.sync_mode} className="h-8 w-8" />
                <span className="text-xs font-semibold text-[#102033]">{modeLabels[task.sync_mode] || task.sync_mode}</span>
              </div>
              <div className="min-w-0 text-right">
                <p className="flex items-center justify-end gap-2 text-xs font-semibold text-[#52657a]"><IconCloud className="h-4 w-4 text-[#3370ff]" />云端目录</p>
                <p className="mt-2 truncate text-sm font-medium text-[#102033]" title={cloudPath}>{shortPath(cloudPath, 76)}</p>
                <p className="mt-2 truncate font-mono text-xs text-[#6b7f96]" title={task.cloud_folder_token}>{shortPath(task.cloud_folder_token, 32)}</p>
              </div>
            </div>
          </section>

          <CurrentRunPanel task={task} status={status} diagnostics={diagnostics} />

          <section className="rounded-xl border border-[#d7e4f5] bg-white p-5 shadow-[0_12px_34px_rgba(51,112,255,0.05)]">
            <div className="mb-4 flex items-center justify-between gap-4">
              <div><h2 className="text-base font-semibold text-[#102033]">运行历史</h2><p className="mt-1 text-xs text-[#52657a]">最近运行记录与处理结果。</p></div>
              {diagnosticsQuery.isLoading ? <span className="text-xs text-[#52657a]">加载中...</span> : null}
            </div>
            <div className="min-w-0 overflow-x-auto"><RunHistoryTable runs={diagnostics?.recent_runs ?? []} /></div>
          </section>
        </div>

        <aside data-task-detail-inspector="true" className="min-w-0 w-[300px] overflow-hidden rounded-xl border border-[#d7e4f5] bg-white shadow-[0_12px_34px_rgba(51,112,255,0.05)]">
          <section className="p-4">
            <h2 className="text-sm font-semibold text-[#102033]">任务控制</h2>
            <button className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#3370ff] px-3 py-2.5 text-xs font-semibold text-white hover:bg-[#1d4ed8] disabled:opacity-50" disabled={health.isRunning} onClick={handleRunTask} type="button"><IconPlay className="h-3.5 w-3.5" />立即同步</button>
            <div className="mt-3 flex items-center justify-between rounded-lg bg-[#f8fbff] px-3 py-2.5">
              <div><p className="text-xs font-medium text-[#334762]">任务启用</p><p className="mt-0.5 text-[11px] text-[#6b7f96]">关闭后停止自动执行</p></div>
              <button aria-checked={task.enabled} aria-label="切换任务启用状态" className={`h-6 w-11 rounded-full p-0.5 transition ${task.enabled ? "bg-[#3370ff]" : "bg-[#c9d8ec]"}`} onClick={handleToggleTask} role="switch" type="button"><span className={`block h-5 w-5 rounded-full bg-white transition ${task.enabled ? "translate-x-5" : ""}`} /></button>
            </div>
            <button className="mt-2 w-full rounded-lg px-3 py-2 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]" onClick={onBack} type="button">返回列表管理策略</button>
          </section>

          <section className="border-t border-[#edf3fb] p-4">
            <div className="flex items-center justify-between"><h2 className="text-sm font-semibold text-[#102033]">需要关注</h2><span className={`text-lg font-semibold ${problemSummary.total > 0 ? "text-[#be123c]" : "text-[#047857]"}`}>{problemSummary.total}</span></div>
            {problemSummary.total === 0 ? (
              <div className="mt-3 rounded-lg border border-[#10b981]/25 bg-[#ecfdf5] p-3 text-xs leading-5 text-[#047857]">当前没有待处理问题，任务状态健康。</div>
            ) : (
              <div className="mt-3 space-y-2">{activeProblemRows.map((row) => <div key={row.label} className="flex items-center justify-between text-xs"><span className="text-[#52657a]">{row.label}</span><span className="font-semibold text-[#be123c]">{row.value}</span></div>)}</div>
            )}
            {status?.last_error ? <p className="mt-3 text-xs leading-5 text-[#be123c]">{status.last_error}</p> : null}
          </section>

          <section className="border-t border-[#edf3fb] p-4">
            <h2 className="text-sm font-semibold text-[#102033]">同步策略</h2>
            <dl className="mt-3 space-y-2 text-xs">
              {[
                ["同步模式", modeLabels[task.sync_mode] || task.sync_mode],
                ["更新策略", updateModeLabels[task.update_mode || "auto"]],
                ["删除策略", deletePolicyLabel(task.delete_policy)],
                ["MD 模式", task.sync_mode === "download_only" ? "不适用" : mdSyncModeLabels[task.md_sync_mode || "enhanced"]],
              ].map(([label, value]) => <div key={label} className="flex justify-between gap-3"><dt className="text-[#6b7f96]">{label}</dt><dd className="text-right font-medium text-[#102033]">{value}</dd></div>)}
            </dl>
            <p className="mt-4 text-xs font-medium text-[#52657a]">忽略目录 ({ignoredSubpaths.length})</p>
            <div className="mt-2 flex flex-wrap gap-1.5">{ignoredSubpaths.slice(0, 8).map((path) => <span key={path} className="rounded-md bg-[#eef5ff] px-2 py-1 font-mono text-[11px] text-[#52657a]">{summarizePath(path, 1, 18)}</span>)}</div>
          </section>

          <details className="border-t border-[#edf3fb] p-4">
            <summary className="cursor-pointer text-sm font-semibold text-[#52657a]">维护操作</summary>
            <div className="mt-3 space-y-2">
              <button className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-[#f59e0b]/40 px-3 py-2 text-xs font-semibold text-[#b45309] hover:bg-[#fffbeb] disabled:opacity-50" disabled={resettingLinks} onClick={handleResetLinks} type="button"><IconRefresh className="h-3.5 w-3.5" />{resettingLinks ? "重置中..." : "重置映射"}</button>
              <button className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-[#f43f5e]/40 px-3 py-2 text-xs font-semibold text-[#be123c] hover:bg-[#fff1f2]" onClick={handleDeleteTask} type="button"><IconTrash className="h-3.5 w-3.5" />删除任务</button>
              <p className="text-[11px] leading-5 text-[#6b7f96]">重置映射不会删除文件；删除任务会移除本地任务配置。</p>
            </div>
          </details>
        </aside>
      </div>
    </section>
  );
}
