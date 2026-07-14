import { useMemo } from "react";
import type { ReactNode } from "react";
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
  IconArrowRightLeft,
  IconChevronLeft,
  IconCloud,
  IconCopy,
  IconFolder,
  IconPause,
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

function TransferMetric({ label, value, hint, tone = "info" }: { label: string; value: number; hint?: string; tone?: Tone }) {
  const color =
    tone === "success" ? "text-[#047857]" :
      tone === "warning" ? "text-[#b45309]" :
        tone === "danger" ? "text-[#be123c]" : "text-[#1d4ed8]";
  return (
    <div className="min-w-0 rounded-lg border border-[#d7e4f5] bg-[#f8fbff] px-4 py-3">
      <p className="text-xs text-[#6b7f96]">{label}</p>
      <p className={`mt-1 text-xl font-semibold ${color}`}>{value}</p>
      {hint ? <p className="mt-1 text-xs text-[#6b7f96]">{hint}</p> : null}
    </div>
  );
}

function InspectorSection({
  title,
  children,
  tone = "neutral",
}: {
  title: string;
  children: ReactNode;
  tone?: Tone;
}) {
  const border =
    tone === "danger" ? "border-[#f43f5e]/35 bg-[#fff7f8]" :
      tone === "warning" ? "border-[#f59e0b]/35 bg-[#fffbeb]" : "border-[#d7e4f5] bg-white";
  return (
    <section className={`rounded-xl border ${border} p-4`}>
      <h3 className="text-sm font-semibold text-[#102033]">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
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
  const runId = status?.current_run_id || activeRun?.run_id || "暂无运行 ID";
  const stateKey = status?.state || activeRun?.state || "idle";
  const startedAt = status?.started_at ?? activeRun?.started_at ?? task.last_run_at ?? null;

  return (
    <section className="min-w-0 rounded-lg border border-[#d7e4f5] bg-white p-4 shadow-[0_10px_28px_rgba(51,112,255,0.05)]">
      <div className="flex min-w-0 items-center justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-[#102033]">当前运行</h2>
          <p className="mt-1 truncate text-xs text-[#6b7f96]" title={runId}>运行 ID：<span className="font-mono">{runId}</span></p>
        </div>
        <div className="shrink-0">
          <StatusPill label={stateLabels[stateKey] || stateKey} tone={stateTones[stateKey] || runTone(stateKey)} dot={stateKey === "running"} />
        </div>
      </div>

      <div className="mt-4 grid min-w-0 grid-cols-[96px_minmax(0,1fr)] items-center gap-4">
        <div
          className="grid h-24 w-24 shrink-0 place-items-center rounded-full"
          style={{ background: `conic-gradient(#3370ff ${progress * 3.6}deg, #e5eef9 0deg)` }}
        >
          <div className="grid h-[74px] w-[74px] place-items-center rounded-full bg-white text-center">
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
      </div>

      <div className="mt-4 grid min-w-0 grid-cols-4 gap-2">
        <TransferMetric label="上传文件" value={status?.uploaded_files ?? activeRun?.counts.uploaded ?? 0} hint="本地到云端" tone="success" />
        <TransferMetric label="下载文件" value={status?.downloaded_files ?? activeRun?.counts.downloaded ?? 0} hint="云端到本地" tone="info" />
        <TransferMetric label="跳过文件" value={status?.skipped_files ?? activeRun?.counts.skipped ?? 0} hint="规则过滤" tone="warning" />
        <TransferMetric label="错误文件" value={status?.failed_files ?? activeRun?.counts.failed ?? 0} hint="需排查" tone="danger" />
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

  return (
    <section className="animate-fade-up min-w-0">
      <div className="grid grid-cols-[minmax(0,1fr)_300px] gap-5">
        <div className="min-w-0 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <button
                className="inline-flex items-center gap-1.5 text-xs font-medium text-[#3370ff] hover:text-[#1d4ed8]"
                onClick={onBack}
                type="button"
              >
                <IconChevronLeft className="h-3.5 w-3.5" />
                同步任务
              </button>
              <h1 className="mt-1 truncate text-xl font-semibold text-[#102033]">任务详情</h1>
            </div>
            <button
              className="inline-flex items-center gap-2 rounded-lg border border-[#c9d8ec] bg-white px-4 py-2 text-xs font-semibold text-[#334762] hover:bg-[#f6faff]"
              onClick={() => {
                refreshTasks();
                refreshStatus();
                void diagnosticsQuery.refetch();
              }}
              type="button"
            >
              <IconRefresh className="h-3.5 w-3.5" />
              刷新
            </button>
          </div>

          <section className="rounded-xl border border-[#d7e4f5] bg-white shadow-[0_16px_40px_rgba(51,112,255,0.06)]">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#edf3fb] px-5 py-4">
              <div className="flex min-w-0 items-center gap-3">
                <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-[#eaf2ff] text-[#3370ff]">
                  <IconFolder className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="truncate text-lg font-semibold text-[#102033]">{task.name || "未命名任务"}</h2>
                    <StatusPill label={health.label} tone={health.tone} dot={health.isRunning} />
                  </div>
                  <p className="mt-1 break-all text-xs text-[#6b7f96]">
                    任务 ID：<span className="font-mono">{task.id}</span>
                    <span className="mx-2 text-[#c9d8ec]">|</span>
                    创建时间：{formatTimestamp(task.created_at)}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs text-[#52657a]">
                <span>启用</span>
                <button
                  aria-label="切换任务启用状态"
                  className={`h-6 w-11 rounded-full p-0.5 transition ${task.enabled ? "bg-[#3370ff]" : "bg-[#c9d8ec]"}`}
                  onClick={handleToggleTask}
                  type="button"
                >
                  <span className={`block h-5 w-5 rounded-full bg-white transition ${task.enabled ? "translate-x-5" : ""}`} />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-[minmax(0,1fr)_112px_minmax(0,1fr)] gap-4 px-5 py-4">
              <div className="min-w-0">
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[#102033]">
                  <IconFolder className="h-4 w-4 text-[#3370ff]" />
                  本地目录
                </div>
                <p className="truncate font-mono text-sm text-[#334762]" title={task.local_path}>{shortPath(task.local_path, 84)}</p>
                <p className="mt-2 text-xs text-[#6b7f96]">本地文件数：{status?.total_files ?? "--"}</p>
                <button
                  className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-[#c9d8ec] px-3 py-1.5 text-xs font-medium text-[#3370ff] hover:bg-[#eef5ff]"
                  onClick={handleCopyLocalPath}
                  type="button"
                >
                  <IconCopy className="h-3.5 w-3.5" />
                  复制路径
                </button>
              </div>

              <div className="flex flex-col items-center justify-center gap-2 text-center">
                <div className="flex w-full items-center gap-2 text-[#3370ff]">
                  <span className="h-px flex-1 bg-[#3370ff]" />
                  <ModeIcon mode={task.sync_mode} className="h-9 w-9" />
                  <span className="h-px flex-1 bg-[#10b981]" />
                </div>
                <p className="text-sm font-medium text-[#102033]">{modeLabels[task.sync_mode] || task.sync_mode}</p>
                <p className="text-xs text-[#047857]">映射正常</p>
              </div>

              <div className="min-w-0 text-right">
                <div className="mb-2 flex items-center justify-end gap-2 text-sm font-semibold text-[#102033]">
                  <IconCloud className="h-4 w-4 text-[#3370ff]" />
                  云端目录
                </div>
                <p className="truncate text-sm text-[#334762]" title={task.cloud_folder_token}>{shortPath(cloudPath, 84)}</p>
                <p className="mt-2 text-xs text-[#6b7f96]">云端标识：{shortPath(task.cloud_folder_token, 32)}</p>
              </div>
            </div>
          </section>

          <CurrentRunPanel task={task} status={status} diagnostics={diagnostics} />

          <section className="rounded-xl border border-[#d7e4f5] bg-white p-5 shadow-[0_16px_40px_rgba(51,112,255,0.06)]">
            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-semibold text-[#102033]">运行历史</h2>
                <p className="mt-1 text-xs text-[#6b7f96]">最近运行记录与处理结果。</p>
              </div>
              {diagnosticsQuery.isLoading ? <span className="text-xs text-[#6b7f96]">加载中...</span> : null}
            </div>
            <div className="min-w-0 overflow-x-auto">
              <RunHistoryTable runs={diagnostics?.recent_runs ?? []} />
            </div>
          </section>
        </div>

        <aside className="min-w-0 w-[300px] space-y-4">
          <InspectorSection title="问题摘要" tone={problemSummary.total > 0 ? "danger" : "neutral"}>
            <div className="flex items-center justify-between">
              <p className="text-sm text-[#52657a]">待处理总数</p>
              <span className="text-xl font-semibold text-[#be123c]">{problemSummary.total}</span>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {problemSummary.rows.map((row) => (
                <div key={row.label} className="rounded-lg border border-[#edf3fb] bg-white px-3 py-2">
                  <p className="text-xs text-[#6b7f96]">{row.label}</p>
                  <p className="mt-1 text-base font-semibold text-[#102033]">{row.value}</p>
                </div>
              ))}
            </div>
            {status?.last_error ? <p className="mt-3 text-xs leading-5 text-[#be123c]">{status.last_error}</p> : null}
          </InspectorSection>

          <InspectorSection title="任务操作">
            <div className="grid grid-cols-2 gap-2">
              <button
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#3370ff] px-3 py-2 text-xs font-semibold text-white hover:bg-[#1d4ed8] disabled:opacity-50"
                disabled={health.isRunning}
                onClick={handleRunTask}
                type="button"
              >
                <IconPlay className="h-3.5 w-3.5" />
                立即同步
              </button>
              <button
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-[#c9d8ec] px-3 py-2 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]"
                onClick={handleToggleTask}
                type="button"
              >
                <IconPause className="h-3.5 w-3.5" />
                {task.enabled ? "暂停" : "启用"}
              </button>
              <button
                className="col-span-2 inline-flex items-center justify-center gap-2 rounded-lg border border-[#c9d8ec] px-3 py-2 text-xs font-semibold text-[#334762] hover:bg-[#f6faff]"
                onClick={onBack}
                type="button"
              >
                <IconArrowRightLeft className="h-3.5 w-3.5" />
                编辑策略
              </button>
            </div>
          </InspectorSection>

          <InspectorSection title="策略摘要">
            <dl className="space-y-2 text-xs">
              <div className="flex justify-between gap-3">
                <dt className="text-[#6b7f96]">同步模式</dt>
                <dd className="text-right font-medium text-[#102033]">{modeLabels[task.sync_mode] || task.sync_mode}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-[#6b7f96]">更新策略</dt>
                <dd className="text-right font-medium text-[#102033]">{updateModeLabels[task.update_mode || "auto"]}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-[#6b7f96]">冲突处理</dt>
                <dd className="text-right font-medium text-[#102033]">保留双方文件</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-[#6b7f96]">删除策略</dt>
                <dd className="text-right font-medium text-[#102033]">{deletePolicyLabel(task.delete_policy)}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-[#6b7f96]">MD 模式</dt>
                <dd className="text-right font-medium text-[#102033]">
                  {task.sync_mode === "download_only" ? "不适用" : mdSyncModeLabels[task.md_sync_mode || "enhanced"]}
                </dd>
              </div>
            </dl>
          </InspectorSection>

          <InspectorSection title={`忽略目录 (${ignoredSubpaths.length})`}>
            <div className="flex flex-wrap gap-2">
              {ignoredSubpaths.slice(0, 8).map((path) => (
                <span key={path} className="rounded-md bg-[#eef5ff] px-2 py-1 font-mono text-xs text-[#52657a]">
                  {summarizePath(path, 1, 18)}
                </span>
              ))}
            </div>
          </InspectorSection>

          <InspectorSection title="危险操作" tone="danger">
            <div className="space-y-2">
              <button
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-[#f43f5e]/40 px-3 py-2 text-xs font-semibold text-[#be123c] hover:bg-[#fff1f2] disabled:opacity-50"
                disabled={resettingLinks}
                onClick={handleResetLinks}
                type="button"
              >
                <IconRefresh className="h-3.5 w-3.5" />
                {resettingLinks ? "重置中..." : "重置映射"}
              </button>
              <button
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-[#f43f5e]/40 px-3 py-2 text-xs font-semibold text-[#be123c] hover:bg-[#fff1f2]"
                onClick={handleDeleteTask}
                type="button"
              >
                <IconTrash className="h-3.5 w-3.5" />
                删除任务
              </button>
              <p className="text-xs leading-5 text-[#9f1239]">重置映射不会删除本地或云端文件；删除任务会移除本地任务配置。</p>
            </div>
          </InspectorSection>
        </aside>
      </div>
    </section>
  );
}
