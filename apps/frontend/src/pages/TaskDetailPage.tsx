import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { TaskSettingsModal } from "../components/tasks/TaskSettingsModal";
import { confirm } from "../components/ui/confirm-dialog";
import { useToast } from "../components/ui/toast";
import { StatusPill } from "../components/StatusPill";
import {
  IconAlertTriangle,
  IconCircleCheck,
  IconCloud,
  IconCopy,
  IconExternalLink,
  IconFolder,
  IconMonitor,
  IconPause,
  IconPlay,
  IconSettings,
} from "../components/Icons";
import { useConflicts } from "../hooks/useConflicts";
import { useTasks } from "../hooks/useTasks";
import { apiFetch } from "../lib/api";
import {
  mdSyncModeLabels,
  modeLabels,
  stateLabels,
  stateTones,
  updateModeLabels,
} from "../lib/constants";
import { formatTimestamp } from "../lib/formatters";
import { shortPath } from "../lib/logCenter";
import { computeTaskProgress } from "../lib/progress";
import { buildTaskDiagnosticsQueryPath } from "../lib/taskDiagnosticsQuery";
import { buildTaskDetailShowcase, type TaskDetailShowcaseStats } from "../lib/taskDetailShowcase";
import {
  TASK_PAGE_SHOWCASE_STATUS,
  TASK_PAGE_SHOWCASE_TASKS,
  useTaskPageShowcase,
} from "../lib/taskPageShowcase";
import { deletePolicyLabel, deriveTaskHealth, summarizePath } from "../lib/taskManagement";
import type {
  SyncLogEntry,
  SyncTask,
  SyncTaskDiagnostics,
  SyncTaskRunSummary,
  SyncTaskStatus,
  Tone,
} from "../types";

type TaskDetailPageProps = {
  taskId: string;
  onBack: () => void;
  showcase?: boolean;
};

const queueStatuses = new Set(["queued", "creating", "created", "reimporting"]);
const defaultIgnoredSubpaths = [".git/", "node_modules/", "__pycache__/", ".DS_Store", "Thumbs.db"];
const liveStats: TaskDetailShowcaseStats = {
  localFiles: "文件统计：尚未统计",
  cloudFiles: "文件统计：尚未统计",
  elapsed: "--",
  remaining: "--",
  speed: "--",
  runSizes: {},
};

function LarkSyncBrandMark() {
  return (
    <svg
      aria-label="LarkSync 同步标识"
      className="h-[50px] w-[110px] shrink-0"
      data-sync-brand-mark="true"
      role="img"
      viewBox="0 0 214 97"
    >
      <image height="97" href="/logo-horizontal.png" preserveAspectRatio="xMinYMid meet" width="600" />
    </svg>
  );
}

function SyncConnector({ direction }: { direction: "left" | "right" }) {
  const isLeft = direction === "left";
  return (
    <svg
      aria-hidden="true"
      className="h-2.5 w-full"
      data-sync-connector={direction}
      preserveAspectRatio="none"
      viewBox="0 0 32 10"
    >
      <path
        d={isLeft ? "M31 5H5M9 1 4 5l5 4" : "M1 5h26M23 1l5 4-5 4"}
        fill="none"
        stroke={isLeft ? "#3370ff" : "#10b981"}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

function countLastFileStatus(status: SyncTaskStatus | undefined, matcher: (value: string) => boolean): number {
  return (status?.last_files || []).filter((item) => matcher(item.status)).length;
}

function runTone(state?: string | null): Tone {
  if (state === "running") return "info";
  if (state === "success" || state === "idle") return "success";
  if (state === "cancelled") return "warning";
  if (state === "failed") return "danger";
  return "neutral";
}

function buildProblemSummary(status: SyncTaskStatus | undefined, conflictCount: number, problems: SyncLogEntry[]) {
  const queueCount = countLastFileStatus(status, (value) => queueStatuses.has(value));
  const failed = (status?.failed_files ?? 0) + (status?.delete_failed_files ?? 0);
  const deletePending = Math.max(
    status?.delete_pending_files ?? 0,
    countLastFileStatus(status, (value) => value === "delete_pending"),
  );
  const conflicts = Math.max(conflictCount, status?.conflict_files ?? 0, problems.length);
  return {
    total: queueCount + failed + deletePending + conflicts,
    rows: [
      { label: "队列", value: queueCount, tone: "warning" as Tone },
      { label: "失败", value: failed, tone: "danger" as Tone },
      { label: "冲突", value: conflicts, tone: "danger" as Tone },
      { label: "待删", value: deletePending, tone: "warning" as Tone },
    ],
  };
}

function formatRunDuration(run: SyncTaskRunSummary): string {
  if (!run.started_at || !run.finished_at) return run.state === "running" ? "进行中" : "--";
  const duration = Math.max(0, Math.round(run.finished_at - run.started_at));
  const hours = Math.floor(duration / 3600);
  const minutes = Math.floor((duration % 3600) / 60);
  const seconds = duration % 60;
  return [hours, minutes, seconds].map((value) => String(value).padStart(2, "0")).join(":");
}

function RunHistoryTable({ runs, runSizes }: { runs: SyncTaskRunSummary[]; runSizes: Record<string, string> }) {
  if (runs.length === 0) {
    return (
      <div className="grid h-full place-items-center rounded-lg border border-dashed border-[#c9d8ec] text-sm text-[#52657a]">
        暂无运行历史
      </div>
    );
  }

  return (
    <div className="min-h-0 overflow-hidden">
      <table className="w-full table-fixed text-left text-[11px] text-[#334762]">
        <thead className="border-b border-[#d7e4f5] text-[#52657a]">
          <tr>
            <th className="w-[20%] px-2.5 py-1.5 font-medium">开始时间</th>
            <th className="w-[25%] px-2.5 py-1.5 font-medium">运行 ID</th>
            <th className="w-[12%] px-2.5 py-1.5 font-medium">状态</th>
            <th className="w-[12%] px-2.5 py-1.5 font-medium">耗时</th>
            <th className="w-[13%] px-2.5 py-1.5 font-medium">上传/下载</th>
            <th className="w-[11%] px-2.5 py-1.5 font-medium">数据量</th>
            <th className="w-[7%] px-2.5 py-1.5 text-center font-medium">结果</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#edf3fb]">
          {runs.slice(0, 5).map((run) => (
            <tr data-run-history-row="true" key={run.run_id} className="h-8 hover:bg-[#f8fbff]">
              <td className="truncate px-2.5 py-1">{formatTimestamp(run.started_at)}</td>
              <td className="truncate px-2.5 py-1 font-mono" title={run.run_id}>{run.run_id}</td>
              <td className="px-2.5 py-1">
                <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium ${run.state === "running" ? "bg-[#eef5ff] text-[#1d4ed8]" : run.state === "success" ? "bg-[#ecfdf5] text-[#047857]" : "bg-[#fffbeb] text-[#b45309]"}`}>{stateLabels[run.state] || run.state}</span>
              </td>
              <td className="px-2.5 py-1">{formatRunDuration(run)}</td>
              <td className="px-2.5 py-1">{run.counts.uploaded} / {run.counts.downloaded}</td>
              <td className="px-2.5 py-1">{runSizes[run.run_id] || "--"}</td>
              <td className="px-2.5 py-1 text-center">
                {run.state === "success" ? <IconCircleCheck className="mx-auto h-4 w-4 text-[#10b981]" /> :
                  run.state === "cancelled" || run.state === "failed" ? <IconAlertTriangle className="mx-auto h-4 w-4 text-[#f59e0b]" /> : "--"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function getRunPanelHeading(state: string | null | undefined, hasRun: boolean): string {
  if (state === "running") return "当前运行";
  if (hasRun) return "最近一次运行";
  return "运行状态";
}

function CurrentRunPanel({
  task,
  status,
  diagnostics,
  stats,
}: {
  task: SyncTask;
  status?: SyncTaskStatus;
  diagnostics?: SyncTaskDiagnostics;
  stats: TaskDetailShowcaseStats;
}) {
  const progressState = computeTaskProgress(status);
  const progress = progressState.progress ?? (status?.state === "success" ? 100 : 0);
  const activeRun = diagnostics?.selected_run ?? diagnostics?.recent_runs?.[0] ?? null;
  const hasRun = Boolean(activeRun || status?.current_run_id || task.last_run_at);
  const runId = status?.current_run_id || activeRun?.run_id || "暂无运行 ID";
  const stateKey = status?.state || activeRun?.state || "idle";
  const startedAt = status?.started_at ?? activeRun?.started_at ?? task.last_run_at ?? null;
  const metrics = [
    { label: "上传文件", value: status?.uploaded_files ?? activeRun?.counts.uploaded ?? 0, hint: "本地到云端", color: "text-[#047857]" },
    { label: "下载文件", value: status?.downloaded_files ?? activeRun?.counts.downloaded ?? 0, hint: "云端到本地", color: "text-[#1d4ed8]" },
    { label: "跳过文件", value: status?.skipped_files ?? activeRun?.counts.skipped ?? 0, hint: "规则过滤", color: "text-[#7c3aed]" },
    { label: "错误文件", value: status?.failed_files ?? activeRun?.counts.failed ?? 0, hint: "需排查", color: "text-[#dc2626]" },
  ];

  return (
    <section data-task-detail-current-run="true" className="min-h-0 rounded-lg border border-[#d7e4f5] bg-white px-4 py-3 shadow-[0_8px_24px_rgba(51,112,255,0.04)]">
      <div className="flex items-center justify-between">
        <h2 className="text-[15px] font-semibold text-[#102033]">{getRunPanelHeading(stateKey, hasRun)}</h2>
        <StatusPill label={stateLabels[stateKey] || stateKey} tone={stateTones[stateKey] || runTone(stateKey)} dot={stateKey === "running"} />
      </div>
      {hasRun ? (
        <div className="mt-2 grid grid-cols-[126px_254px_minmax(0,1fr)] items-center gap-4">
          <div
            className="grid h-[100px] w-[100px] place-items-center rounded-full"
            style={{ background: `conic-gradient(#3370ff ${progress * 3.6}deg, #e6eef9 0deg)` }}
          >
            <div className="grid h-[82px] w-[82px] place-items-center rounded-full bg-white text-center">
              <div>
                <p className="text-2xl font-semibold text-[#102033]">{progress}%</p>
                <p className="text-xs text-[#52657a]">{stateLabels[stateKey] || stateKey}</p>
              </div>
            </div>
          </div>
          <dl className="grid grid-cols-[80px_minmax(0,1fr)] gap-y-1.5 text-xs">
            <dt className="text-[#6b7f96]">运行 ID</dt><dd className="flex min-w-0 items-center gap-1.5 truncate font-mono text-[#334762]" title={runId}>{runId}<IconCopy className="h-3 w-3 shrink-0" /></dd>
            <dt className="text-[#6b7f96]">开始时间</dt><dd className="text-[#334762]">{formatTimestamp(startedAt)}</dd>
            <dt className="text-[#6b7f96]">已用时间</dt><dd className="text-[#334762]">{stats.elapsed}</dd>
            <dt className="text-[#6b7f96]">预计剩余</dt><dd className="text-[#334762]">{stats.remaining}</dd>
            <dt className="text-[#6b7f96]">当前速度</dt><dd className="text-[#334762]">{stats.speed}</dd>
          </dl>
          <div data-run-metrics="true" className="grid grid-cols-4">
            {metrics.map((metric) => (
              <div className="min-w-0 border-l border-[#d7e4f5] px-3 text-center first:border-l-0" key={metric.label}>
                <p className="text-xs text-[#52657a]">{metric.label}</p>
                <p className={`mt-2 text-xl font-semibold ${metric.color}`}>{metric.value}</p>
                <p className="mt-1 text-[10px] text-[#7e91a8]">{metric.hint}</p>
              </div>
            ))}
            <div className="col-span-4 mt-4 h-1.5 overflow-hidden rounded-full bg-[#e5eef9]">
              <div className="h-full rounded-full bg-[#3370ff]" style={{ width: `${progress}%` }} />
            </div>
          </div>
        </div>
      ) : (
        <div className="mt-3 grid h-[122px] place-items-center rounded-lg border border-dashed border-[#c9d8ec] bg-[#f8fbff] text-center">
          <div><p className="text-sm font-medium text-[#334762]">尚未运行</p><p className="mt-1 text-xs text-[#6b7f96]">首次同步后显示进度和处理结果</p></div>
        </div>
      )}
    </section>
  );
}

export function TaskDetailPage({ taskId, onBack, showcase }: TaskDetailPageProps) {
  const {
    tasks,
    statusMap,
    taskLoading,
    runTask,
    toggleTask,
    deleteTask,
    updateTaskSettings,
    resetLinks,
    resettingLinks,
  } = useTasks();
  const { conflicts } = useConflicts();
  const { toast } = useToast();
  const automaticShowcase = useTaskPageShowcase();
  const showcaseMode = showcase ?? automaticShowcase;
  const initialShowcaseTask = TASK_PAGE_SHOWCASE_TASKS.find((item) => item.id === taskId) || null;
  const [showcaseTask, setShowcaseTask] = useState<SyncTask | null>(initialShowcaseTask);
  const [showcaseStatus, setShowcaseStatus] = useState<SyncTaskStatus | undefined>(
    initialShowcaseTask ? TASK_PAGE_SHOWCASE_STATUS[initialShowcaseTask.id] : undefined,
  );
  const [settingsOpen, setSettingsOpen] = useState(false);
  const liveTask = tasks.find((item) => item.id === taskId) || null;
  const task = showcaseMode ? showcaseTask : liveTask;
  const sourceStatus = showcaseMode ? showcaseStatus : statusMap[taskId];
  const showcaseData = useMemo(
    () => (showcaseMode && task ? buildTaskDetailShowcase(task, sourceStatus) : null),
    [showcaseMode, sourceStatus, task],
  );
  const status = showcaseData?.status ?? sourceStatus;

  const diagnosticsQuery = useQuery<SyncTaskDiagnostics>({
    queryKey: ["task-detail-diagnostics", taskId],
    queryFn: () => apiFetch<SyncTaskDiagnostics>(buildTaskDiagnosticsQueryPath({
      selectedTaskId: taskId,
      selectedRunId: null,
      includeProblems: true,
      limit: 120,
    })),
    enabled: Boolean(taskId) && !showcaseMode,
    refetchInterval: status?.state === "running" ? 5_000 : 10_000,
  });

  const taskConflicts = useMemo(
    () => (task && !showcaseMode
      ? conflicts.filter((conflict) => !conflict.resolved && conflict.local_path.startsWith(task.local_path))
      : []),
    [conflicts, showcaseMode, task],
  );

  if (!showcaseMode && taskLoading && !task) {
    return <section className="animate-fade-up rounded-xl border border-[#d7e4f5] bg-white p-8 text-center text-sm text-[#52657a]">正在加载任务详情...</section>;
  }

  if (!task) {
    return (
      <section className="animate-fade-up rounded-xl border border-[#d7e4f5] bg-white p-8 text-center">
        <p className="text-base font-semibold text-[#102033]">未找到任务</p>
        <p className="mt-2 text-sm text-[#52657a]">任务可能已被删除或尚未同步到本地状态。</p>
        <button className="mt-5 rounded-lg bg-[#3370ff] px-4 py-2 text-sm font-semibold text-white" onClick={onBack} type="button">返回同步任务</button>
      </section>
    );
  }

  const diagnostics = showcaseData?.diagnostics ?? diagnosticsQuery.data;
  const stats = showcaseData?.stats ?? liveStats;
  const conflictCount = showcaseMode ? status?.conflict_files ?? 0 : taskConflicts.length;
  const health = deriveTaskHealth({
    enabled: task.enabled,
    state: status?.state,
    lastFiles: status?.last_files,
    conflictCount,
    lastError: status?.last_error,
    failedFiles: status?.failed_files,
    deleteFailedFiles: status?.delete_failed_files,
  });
  const problems = diagnostics?.problems ?? [];
  const problemSummary = buildProblemSummary(status, conflictCount, problems);
  const ignoredSubpaths = task.ignored_subpaths?.length ? task.ignored_subpaths : defaultIgnoredSubpaths;
  const usingDefaultIgnores = !task.ignored_subpaths?.length;
  const progressState = computeTaskProgress(status);
  const cloudPath = task.cloud_folder_name || task.cloud_folder_token || "-";

  const handleRunTask = () => {
    if (showcaseMode) {
      setShowcaseStatus((current) => current ? { ...current, state: "running", started_at: Date.now() / 1000 } : current);
    } else {
      runTask(task);
    }
    toast("同步已触发", "info");
  };

  const handleToggleTask = () => {
    if (showcaseMode) {
      setShowcaseTask((current) => current ? { ...current, enabled: !current.enabled } : current);
    } else {
      toggleTask(task);
    }
    toast(task.enabled ? "任务已停用" : "任务已启用", "info");
  };

  const handleOpenLocalFolder = async () => {
    if (showcaseMode) {
      toast(`演示目录：${task.local_path}`, "info");
      return;
    }
    try {
      await apiFetch<{ path: string }>(`/sync/tasks/${task.id}/open-local-folder`, { method: "POST" });
      toast("已在文件管理器中打开本地目录", "success");
    } catch (error) {
      toast(error instanceof Error ? error.message : "打开本地目录失败", "danger");
    }
  };

  const handleOpenCloudFolder = () => {
    if (typeof window === "undefined") return;
    window.open(`https://www.feishu.cn/drive/folder/${encodeURIComponent(task.cloud_folder_token)}`, "_blank", "noopener,noreferrer");
  };

  const handleDeleteTask = async () => {
    const ok = await confirm({
      title: "确认删除任务",
      description: `即将删除任务「${task.name || task.local_path}」，此操作不可恢复。`,
      confirmLabel: "删除",
      tone: "danger",
    });
    if (!ok) return;
    if (showcaseMode) setShowcaseTask(null);
    else deleteTask(task);
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
    if (showcaseMode) {
      toast("演示映射已重置", "success");
      return;
    }
    try {
      const result = await resetLinks(task.id);
      toast(`已清除 ${result.deleted_links} 条同步映射`, "success");
    } catch (error) {
      toast(error instanceof Error ? error.message : "重置失败", "danger");
    }
  };

  const handleSaveSettings = async (patch: Record<string, unknown>) => {
    try {
      if (showcaseMode) setShowcaseTask((current) => current ? { ...current, ...patch } : current);
      else await updateTaskSettings({ id: task.id, patch });
      toast("任务设置已保存", "success");
    } catch (error) {
      toast(error instanceof Error ? error.message : "任务设置保存失败", "danger");
      throw error;
    }
  };

  return (
    <section className="tasks-clarity animate-fade-up flex h-full min-h-0 min-w-0 flex-col">
      <div className="mb-2 shrink-0">
        <div className="flex items-center gap-2 text-xs text-[#52657a]">
          <button className="font-medium text-[#3370ff] hover:underline" onClick={onBack} type="button">同步任务</button>
          <span>/</span>
          <span className="truncate">{task.name || "未命名任务"}</span>
        </div>
        <h1 className="mt-1 text-[22px] font-semibold leading-7 text-[#102033]">任务详情</h1>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_300px] items-stretch gap-4">
        <div className="grid min-h-0 min-w-0 grid-rows-[258px_202px_minmax(0,1fr)] gap-3">
          <section data-task-detail-identity="true" className="min-h-0 overflow-hidden rounded-lg border border-[#d7e4f5] bg-white shadow-[0_8px_24px_rgba(51,112,255,0.04)]">
            <div className="flex h-[86px] items-center justify-between gap-4 px-5">
              <div className="flex min-w-0 items-center gap-3">
                <div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-[#3370ff] to-[#6b93ff] text-white shadow-[0_8px_18px_rgba(51,112,255,0.24)]"><IconFolder className="h-7 w-7" /></div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2"><h2 className="truncate text-lg font-semibold text-[#102033]">{task.name || "未命名任务"}</h2><StatusPill label={health.label} tone={health.tone} dot={health.isRunning} /></div>
                  <p className="mt-1 text-xs text-[#52657a]">任务 ID：<span className="font-mono">{task.id}</span><span className="mx-4">创建时间：{formatTimestamp(task.created_at)}</span></p>
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <span className="text-xs font-medium text-[#334762]">启用</span>
                <button aria-checked={task.enabled} aria-label="切换任务启用状态" className={`h-6 w-11 rounded-full p-0.5 transition ${task.enabled ? "bg-[#3370ff]" : "bg-[#c9d8ec]"}`} onClick={handleToggleTask} role="switch" type="button"><span className={`block h-5 w-5 rounded-full bg-white transition ${task.enabled ? "translate-x-5" : ""}`} /></button>
                <button className="inline-flex h-9 items-center gap-2 rounded-lg border border-[#bfd3ee] px-3.5 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]" onClick={() => setSettingsOpen(true)} type="button"><IconSettings className="h-4 w-4" />编辑策略</button>
              </div>
            </div>
            <div data-task-detail-path-map="true" className="grid h-[170px] grid-cols-[minmax(0,1fr)_190px_minmax(0,1fr)] items-center border-t border-[#d7e4f5] px-6">
              <div className="w-[300px] max-w-full min-w-0 justify-self-start" data-sync-endpoint-content="local">
                <div className="flex items-center gap-2"><IconMonitor className="h-5 w-5 text-[#3370ff]" data-local-endpoint-icon="monitor" /><h3 className="text-sm font-semibold text-[#102033]">本地目录</h3></div>
                <p className="mt-3 truncate font-mono text-xs text-[#334762]" title={task.local_path}>{shortPath(task.local_path, 72)}</p>
                <p className="mt-2 text-xs text-[#52657a]">{stats.localFiles}</p>
                <button className="mt-3 inline-flex h-8 items-center gap-1.5 rounded-md border border-[#bfd3ee] px-3 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]" onClick={() => void handleOpenLocalFolder()} type="button"><IconExternalLink className="h-3.5 w-3.5" />打开目录</button>
              </div>
              <div className="flex -translate-x-[17px] flex-col items-center text-center" data-sync-relationship="true" data-sync-visual-offset="-17">
                <div className="grid w-full grid-cols-[minmax(0,1fr)_110px_minmax(0,1fr)] items-center gap-2">
                  <SyncConnector direction="left" />
                  <LarkSyncBrandMark />
                  <SyncConnector direction="right" />
                </div>
                <div className="mt-1.5 text-xs font-semibold text-[#334762]" data-sync-mode-label="true">{modeLabels[task.sync_mode] || task.sync_mode}</div>
                <p className="mt-2 inline-flex items-center gap-1.5 text-[11px] font-semibold text-[#047857]" data-sync-health="true">
                  <span className="grid h-3.5 w-3.5 place-items-center rounded-full bg-[#10b981] text-white">
                    <svg aria-hidden="true" className="h-2.5 w-2.5" fill="none" viewBox="0 0 12 12"><path d="m2.5 6 2.1 2.1 4.9-5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" /></svg>
                  </span>
                  映射正常
                </p>
              </div>
              <div className="w-[300px] max-w-full min-w-0 justify-self-end" data-sync-endpoint-content="cloud">
                <div className="flex items-center gap-2"><IconCloud className="h-5 w-5 text-[#3370ff]" /><h3 className="text-sm font-semibold text-[#102033]">云端目录</h3></div>
                <p className="mt-3 truncate text-xs font-medium text-[#334762]" title={cloudPath}>{shortPath(cloudPath, 72)}</p>
                <p className="mt-2 text-xs text-[#52657a]">{stats.cloudFiles}</p>
                <button className="mt-3 inline-flex h-8 items-center gap-1.5 rounded-md border border-[#bfd3ee] px-3 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]" onClick={handleOpenCloudFolder} type="button"><IconExternalLink className="h-3.5 w-3.5" />打开目录</button>
              </div>
            </div>
          </section>

          <CurrentRunPanel task={task} status={status} diagnostics={diagnostics} stats={stats} />

          <section data-task-detail-history="true" className="flex min-h-0 flex-col overflow-hidden rounded-lg border border-[#d7e4f5] bg-white px-4 py-3 shadow-[0_8px_24px_rgba(51,112,255,0.04)]">
            <div className="mb-0.5 flex shrink-0 items-center justify-between">
              <h2 className="text-[15px] font-semibold text-[#102033]">运行历史</h2>
              {diagnosticsQuery.isLoading && !showcaseMode ? <span className="text-xs text-[#52657a]">加载中...</span> : null}
            </div>
            <div className="min-h-0 flex-1"><RunHistoryTable runs={diagnostics?.recent_runs ?? []} runSizes={stats.runSizes} /></div>
            <button className="mt-1 w-fit shrink-0 text-xs font-semibold text-[#3370ff]" type="button">查看更多历史记录 ›</button>
          </section>
        </div>

        <aside data-task-detail-inspector="true" className="flex min-h-0 w-[300px] flex-col gap-2">
          <section data-task-detail-inspector-card="problems" className="shrink-0 rounded-lg border border-[#d7e4f5] bg-white p-3 shadow-[0_8px_24px_rgba(51,112,255,0.04)]">
            <div className="flex items-center justify-between"><h2 className="text-[15px] font-semibold text-[#102033]">问题摘要</h2><span className={`grid h-5 min-w-5 place-items-center rounded-full px-1 text-xs font-semibold ${problemSummary.total ? "bg-[#fee2e2] text-[#dc2626]" : "bg-[#d1fae5] text-[#047857]"}`}>{problemSummary.total}</span></div>
            {problemSummary.total ? (
              <div className="mt-2.5 rounded-md border border-[#fecaca] bg-[#fff7f7] p-2.5">
                <div className="flex items-center justify-between text-xs font-semibold text-[#dc2626]"><span className="inline-flex items-center gap-1.5"><IconAlertTriangle className="h-4 w-4" />冲突等待处理</span><span>{problemSummary.rows.find((row) => row.label === "冲突")?.value || problemSummary.total}</span></div>
                <p className="mt-2 truncate text-[11px] font-medium text-[#334762]">{problems[0] ? shortPath(problems[0].path, 34) : "有文件需要检查"}</p>
                <p className="mt-0.5 text-[10px] text-[#6b7f96]">请前往冲突处理页完成决策</p>
              </div>
            ) : <div className="mt-2.5 rounded-md border border-[#a7f3d0] bg-[#ecfdf5] p-2.5 text-xs text-[#047857]">当前没有待处理问题</div>}
            <button className="mt-2 text-xs font-semibold text-[#3370ff]" type="button">查看全部 ›</button>
          </section>

          <section data-task-detail-inspector-card="actions" className="shrink-0 rounded-lg border border-[#d7e4f5] bg-white p-3 shadow-[0_8px_24px_rgba(51,112,255,0.04)]">
            <h2 className="text-[15px] font-semibold text-[#102033]">任务操作</h2>
            <div className="mt-2.5 grid grid-cols-2 gap-2">
              <button className="inline-flex h-9 items-center justify-center gap-1.5 rounded-md border border-[#bfd3ee] text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]" disabled={health.isRunning} onClick={handleRunTask} type="button"><IconPlay className="h-3.5 w-3.5" />立即同步</button>
              <button className="inline-flex h-9 items-center justify-center gap-1.5 rounded-md border border-[#bfd3ee] text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]" onClick={handleToggleTask} type="button"><IconPause className="h-3.5 w-3.5" />{task.enabled ? "暂停任务" : "启用任务"}</button>
              <button className="inline-flex h-9 items-center justify-center gap-1.5 rounded-md border border-[#bfd3ee] text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]" onClick={() => void handleOpenLocalFolder()} type="button"><IconFolder className="h-3.5 w-3.5" />打开目录</button>
              <button className="inline-flex h-9 items-center justify-center gap-1.5 rounded-md border border-[#bfd3ee] text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]" onClick={() => setSettingsOpen(true)} type="button"><IconSettings className="h-3.5 w-3.5" />编辑策略</button>
            </div>
          </section>

          <section data-task-detail-inspector-card="strategy" className="shrink-0 rounded-lg border border-[#d7e4f5] bg-white p-3 shadow-[0_8px_24px_rgba(51,112,255,0.04)]">
            <h2 className="text-[15px] font-semibold text-[#102033]">策略摘要</h2>
            <dl className="mt-2 space-y-1 text-xs">
              {[
                ["同步模式", modeLabels[task.sync_mode] || task.sync_mode],
                ["更新策略", updateModeLabels[task.update_mode || "auto"]],
                ["冲突处理", "云端优先（保留副本）"],
                ["删除联动", deletePolicyLabel(task.delete_policy)],
                ["MD 模式", task.sync_mode === "download_only" ? "不适用" : mdSyncModeLabels[task.md_sync_mode || "enhanced"]],
              ].map(([label, value]) => <div className="flex justify-between gap-3" key={label}><dt className="text-[#6b7f96]">{label}</dt><dd className="truncate text-right font-medium text-[#334762]" title={value}>{value}</dd></div>)}
            </dl>
            <button className="mt-1.5 text-xs font-semibold text-[#3370ff]" onClick={() => setSettingsOpen(true)} type="button">查看详情 ›</button>
          </section>

          <section data-task-detail-inspector-card="ignored" className="shrink-0 rounded-lg border border-[#d7e4f5] bg-white p-3 shadow-[0_8px_24px_rgba(51,112,255,0.04)]">
            <div className="flex items-center justify-between"><h2 className="text-[15px] font-semibold text-[#102033]">忽略目录（{ignoredSubpaths.length}）</h2>{usingDefaultIgnores ? <span className="text-[10px] text-[#7e91a8]">默认</span> : null}</div>
            <div className="mt-2.5 flex flex-wrap gap-1.5">{ignoredSubpaths.slice(0, 5).map((path) => <span className="rounded-md bg-[#eef5ff] px-2 py-1 font-mono text-[10px] text-[#334762]" key={path}>{summarizePath(path, 1, 18)}</span>)}</div>
          </section>

          <section data-task-detail-inspector-card="danger" className="min-h-0 flex-1 overflow-hidden rounded-lg border border-[#fca5a5] bg-[#fffafa] p-3 shadow-[0_8px_24px_rgba(244,63,94,0.04)]">
            <h2 className="text-[15px] font-semibold text-[#7f1d1d]">危险操作</h2>
            <button className="mt-2.5 inline-flex h-8 w-full items-center justify-center gap-2 rounded-md border border-[#f87171] text-xs font-semibold text-[#dc2626] hover:bg-[#fff1f2] disabled:opacity-50" disabled={resettingLinks} onClick={() => void handleResetLinks()} type="button"><IconAlertTriangle className="h-4 w-4" />{resettingLinks ? "重置中..." : "重置映射"}</button>
            <p className="mt-2 text-[10px] leading-4 text-[#7f1d1d]">清除本机状态库中的同步映射；下次运行重新扫描，不会删除文件。</p>
          </section>
        </aside>
      </div>

      {settingsOpen ? (
        <TaskSettingsModal
          task={task}
          processed={progressState.processed}
          total={progressState.effectiveTotal}
          onClose={() => setSettingsOpen(false)}
          onDelete={handleDeleteTask}
          onSave={handleSaveSettings}
        />
      ) : null}
    </section>
  );
}
