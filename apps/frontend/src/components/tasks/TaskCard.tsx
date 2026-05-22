import { formatTimestamp } from "../../lib/formatters";
import {
  mdSyncModeLabels,
  modeLabels,
  stateLabels,
  syncModeSupportsUpload,
  updateModeLabels,
} from "../../lib/constants";
import { computeTaskProgress } from "../../lib/progress";
import {
  deletePolicyLabel,
  deriveTaskHealth,
  parseDeleteGraceMinutes,
  summarizePath,
} from "../../lib/taskManagement";
import { StatusPill } from "../StatusPill";
import {
  IconChevronDown,
  IconChevronRight,
  IconCloud,
  IconFolder,
  IconPlay,
  IconTrash,
  ModeIcon,
} from "../Icons";
import type { SyncTask, SyncTaskStatus } from "../../types";

type TaskCardProps = {
  task: SyncTask;
  status?: SyncTaskStatus;
  conflictCount: number;
  expanded: boolean;
  onToggleExpanded: () => void;
  localPathExpanded: boolean;
  cloudPathExpanded: boolean;
  onTogglePath: (side: "local" | "cloud") => void;
  syncModeValue: string;
  updateModeValue: string;
  mdSyncModeValue: "enhanced" | "download_only" | "doc_only";
  deletePolicyValue: "off" | "safe" | "strict";
  deleteGraceValue: string;
  onSyncModeChange: (value: string) => void;
  onUpdateModeChange: (value: string) => void;
  onMdSyncModeChange: (value: "enhanced" | "download_only" | "doc_only") => void;
  onDeletePolicyChange: (value: "off" | "safe" | "strict") => void;
  onDeleteGraceChange: (value: string) => void;
  onApplySyncMode: () => void;
  onApplyUpdateMode: () => void;
  onApplyMdSyncMode: () => void;
  onApplyDeletePolicy: () => void;
  onRun: () => void;
  onToggleEnabled: () => void;
  onDelete: () => void;
};

export function TaskCard({
  task,
  status,
  conflictCount,
  expanded,
  onToggleExpanded,
  localPathExpanded,
  cloudPathExpanded,
  onTogglePath,
  syncModeValue,
  updateModeValue,
  mdSyncModeValue,
  deletePolicyValue,
  deleteGraceValue,
  onSyncModeChange,
  onUpdateModeChange,
  onMdSyncModeChange,
  onDeletePolicyChange,
  onDeleteGraceChange,
  onApplySyncMode,
  onApplyUpdateMode,
  onApplyMdSyncMode,
  onApplyDeletePolicy,
  onRun,
  onToggleEnabled,
  onDelete,
}: TaskCardProps) {
  const stateKey = !task.enabled ? "paused" : status?.state || "idle";
  const progressState = computeTaskProgress(status);
  const progress = progressState.progress;
  const cloudPath = task.cloud_folder_name || task.cloud_folder_token || "-";
  const taskUploadEnabled = syncModeSupportsUpload(syncModeValue);
  const deleteGraceMinutes = parseDeleteGraceMinutes(
    deletePolicyValue,
    deleteGraceValue,
    task.delete_grace_minutes ?? 30
  );
  const lastSyncTime = status?.finished_at ?? status?.started_at ?? task.last_run_at ?? null;
  const health = deriveTaskHealth({
    enabled: task.enabled,
    state: status?.state,
    lastFiles: status?.last_files,
    conflictCount,
    lastError: status?.last_error,
    failedFiles: status?.failed_files,
    deleteFailedFiles: status?.delete_failed_files,
  });

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <StatusPill label={health.label} tone={health.tone} dot={health.isRunning} />
            <p className="text-lg font-semibold text-zinc-50">{task.name || "未命名任务"}</p>
          </div>
          <p className="text-xs text-zinc-500">
            {summarizePath(task.local_path, 2, 42)} 与 {summarizePath(cloudPath, 2, 42)} 保持同步
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-400">
          <span className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-3 py-1">
            <ModeIcon mode={task.sync_mode} className="h-3.5 w-3.5" />
            {modeLabels[task.sync_mode] || task.sync_mode}
          </span>
          <span className="rounded-lg border border-zinc-700 px-3 py-1">
            更新：{updateModeLabels[task.update_mode || "auto"]}
          </span>
          <span className="rounded-lg border border-zinc-700 px-3 py-1">
            MD：
            {task.sync_mode === "download_only"
              ? "不适用（仅下载）"
              : mdSyncModeLabels[task.md_sync_mode || "enhanced"]}
          </span>
          <span className="rounded-lg border border-zinc-700 px-3 py-1">
            {deletePolicyLabel(task.delete_policy)}
          </span>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
        <div className="grid gap-4 lg:grid-cols-[1fr_auto_1fr]">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-emerald-500/20 p-2 text-emerald-300">
              <IconFolder className="h-4 w-4" />
            </div>
            <div className="min-w-0 w-full">
              <div className="flex items-center justify-between gap-2">
                <p className="text-[11px] uppercase tracking-widest text-zinc-500">本地目录</p>
                <button
                  className="text-[11px] text-zinc-500 hover:text-zinc-300"
                  onClick={() => onTogglePath("local")}
                  type="button"
                >
                  {localPathExpanded ? "收起" : "展开"}
                </button>
              </div>
              <button
                className={`mt-1 w-full text-left font-mono text-xs leading-relaxed text-zinc-200 ${
                  localPathExpanded ? "break-all" : "truncate"
                }`}
                onClick={() => onTogglePath("local")}
                title={task.local_path}
                type="button"
              >
                {localPathExpanded ? task.local_path : summarizePath(task.local_path)}
              </button>
            </div>
          </div>
          <div className="flex items-center justify-center">
            <span className="rounded-full border border-zinc-700 bg-zinc-900 p-2 text-zinc-400">
              <ModeIcon mode={task.sync_mode} className="h-4 w-4" />
            </span>
          </div>
          <div className="flex items-center justify-end gap-3 text-right">
            <div className="min-w-0 w-full">
              <div className="flex items-center justify-between gap-2">
                <p className="text-[11px] uppercase tracking-widest text-zinc-500">云端目录</p>
                <button
                  className="text-[11px] text-zinc-500 hover:text-zinc-300"
                  onClick={() => onTogglePath("cloud")}
                  type="button"
                >
                  {cloudPathExpanded ? "收起" : "展开"}
                </button>
              </div>
              <button
                className={`mt-1 w-full text-left text-xs leading-relaxed text-zinc-200 ${
                  cloudPathExpanded ? "break-all" : "truncate"
                }`}
                onClick={() => onTogglePath("cloud")}
                title={task.cloud_folder_token}
                type="button"
              >
                {cloudPathExpanded ? cloudPath : summarizePath(cloudPath)}
              </button>
            </div>
            <div className="rounded-xl bg-[#3370FF]/15 p-2 text-[#3370FF]">
              <IconCloud className="h-4 w-4" />
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-zinc-500">
        <span>最近同步：{lastSyncTime ? formatTimestamp(lastSyncTime) : "暂无"}</span>
        <span className="text-zinc-600">|</span>
        <span>待处理 {health.pendingRealtimeCount}</span>
        <span className="text-zinc-600">|</span>
        <span>删除 {status?.deleted_files ?? 0}</span>
        <span className="text-zinc-600">|</span>
        <span>待删 {status?.delete_pending_files ?? 0}</span>
        <span className="text-zinc-600">|</span>
        <span>删失败 {status?.delete_failed_files ?? 0}</span>
        <span className="text-zinc-600">|</span>
        <span>失败 {status?.failed_files ?? 0}</span>
        <span className="text-zinc-600">|</span>
        <span>冲突 {conflictCount}</span>
        {progress !== null ? (
          <>
            <span className="text-zinc-600">|</span>
            <span>完成率：{progress}%</span>
          </>
        ) : null}
      </div>
      {status?.last_error ? <p className="mt-2 text-xs text-rose-400">错误：{status.last_error}</p> : null}
      {progress !== null ? (
        <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
          <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${progress}%` }} />
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          className="inline-flex items-center gap-2 rounded-lg bg-emerald-500/20 px-4 py-2 text-xs font-semibold text-emerald-300 transition hover:bg-emerald-500/30 disabled:opacity-50"
          onClick={onRun}
          disabled={health.isRunning}
          type="button"
        >
          <IconPlay className="h-3.5 w-3.5" /> {health.isRunning ? "同步中" : "立即同步"}
        </button>
        <button
          className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
          onClick={onToggleEnabled}
          type="button"
        >
          {task.enabled ? "停用" : "启用"}
        </button>
        <button
          className="inline-flex items-center gap-2 rounded-lg border border-rose-500/40 px-4 py-2 text-xs font-medium text-rose-300 transition hover:bg-rose-500/10"
          onClick={onDelete}
          type="button"
        >
          <IconTrash className="h-3.5 w-3.5" /> 删除
        </button>
        <button
          className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
          onClick={onToggleExpanded}
          type="button"
        >
          {expanded ? <IconChevronDown className="h-3 w-3" /> : <IconChevronRight className="h-3 w-3" />}
          {expanded ? "收起管理" : "任务管理"}
        </button>
      </div>

      {expanded ? (
        <div className="mt-4 grid gap-4 lg:grid-cols-4">
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4 lg:col-span-4">
            <p className="text-xs uppercase tracking-widest text-zinc-500">高级信息</p>
            <div className="mt-3 grid gap-2 text-xs text-zinc-500 md:grid-cols-2">
              <p className="break-all">任务 ID：{task.id}</p>
              <p className="break-all">base_path：{task.base_path || "默认同本地目录"}</p>
              {status ? (
                <p>
                  已处理 {progressState.processed}/{progressState.effectiveTotal}，完成 {status.completed_files}
                  ，删除 {status.deleted_files}，待删 {status.delete_pending_files}，删失败{" "}
                  {status.delete_failed_files}，跳过 {status.skipped_files}
                </p>
              ) : null}
              <p>原始状态：{stateLabels[stateKey] || stateKey}</p>
            </div>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
            <p className="text-xs uppercase tracking-widest text-zinc-500">同步模式</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <select
                className="rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-xs text-zinc-200 outline-none"
                value={syncModeValue}
                onChange={(e) => onSyncModeChange(e.target.value)}
              >
                <option value="bidirectional">双向同步</option>
                <option value="download_only">仅下载</option>
                <option value="upload_only">仅上传</option>
              </select>
              <button
                className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
                onClick={onApplySyncMode}
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
                value={updateModeValue}
                onChange={(e) => onUpdateModeChange(e.target.value)}
              >
                <option value="auto">自动更新</option>
                <option value="partial">局部更新</option>
                <option value="full">全量覆盖</option>
              </select>
              <button
                className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
                onClick={onApplyUpdateMode}
                type="button"
              >
                应用
              </button>
            </div>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
            <p className="text-xs uppercase tracking-widest text-zinc-500">MD 上传模式</p>
            {taskUploadEnabled ? (
              <>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <select
                    className="rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-xs text-zinc-200 outline-none"
                    value={mdSyncModeValue}
                    onChange={(e) =>
                      onMdSyncModeChange(
                        e.target.value as "enhanced" | "download_only" | "doc_only"
                      )
                    }
                  >
                    <option value="enhanced">增强 MD 上传</option>
                    <option value="download_only">MD 仅下载</option>
                    <option value="doc_only">仅云文档上传</option>
                  </select>
                  <button
                    className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
                    onClick={onApplyMdSyncMode}
                    type="button"
                  >
                    应用
                  </button>
                </div>
                <p className="mt-2 text-[11px] text-zinc-500">
                  {mdSyncModeValue === "enhanced"
                    ? "增强：上传云文档，并维护云端 MD 副本目录。"
                    : mdSyncModeValue === "download_only"
                      ? "仅下载：不执行本地 MD 上行，适合把飞书作为默认编辑端。"
                      : "仅云文档：只更新云文档，不保留云端 MD 副本（复杂格式可能有损耗）。"}
                </p>
              </>
            ) : (
              <p className="mt-3 text-sm leading-6 text-zinc-400">
                当前任务为仅下载，不会执行本地 Markdown 上行，因此不显示 MD 上传配置。
              </p>
            )}
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
            <p className="text-xs uppercase tracking-widest text-zinc-500">删除策略</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <select
                className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-zinc-200 outline-none"
                value={deletePolicyValue}
                onChange={(e) =>
                  onDeletePolicyChange(e.target.value as "off" | "safe" | "strict")
                }
              >
                <option value="off">关闭</option>
                <option value="safe">安全</option>
                <option value="strict">严格</option>
              </select>
              <input
                className="w-20 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-zinc-200 outline-none"
                type="number"
                min="0"
                step="1"
                value={deleteGraceValue}
                onChange={(e) => onDeleteGraceChange(e.target.value)}
                disabled={deletePolicyValue === "strict"}
              />
              <span className="text-xs text-zinc-500">分钟</span>
              <button
                className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
                onClick={onApplyDeletePolicy}
                type="button"
              >
                应用
              </button>
            </div>
            <p className="mt-2 text-[11px] text-zinc-500">
              {deletePolicyValue === "off"
                ? "关闭：本地删除和云端删除都不联动。"
                : deletePolicyValue === "safe"
                  ? "安全：先进入删除待处理，宽限后执行；云端删本地时先移入 .larksync_trash。"
                  : `严格：删除会尽快联动执行，宽限时间固定为 ${deleteGraceMinutes} 分钟。`}
            </p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
