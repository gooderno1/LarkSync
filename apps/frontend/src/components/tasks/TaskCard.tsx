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
  onOpenDetail?: () => void;
};

const TASK_CARD_QUEUE_STATUSES = new Set(["queued", "creating", "created", "reimporting"]);

function countLastFileStatus(status: SyncTaskStatus | undefined, matcher: (value: string) => boolean): number {
  return (status?.last_files || []).filter((item) => matcher(item.status)).length;
}

function buildTaskPendingDetail(status: SyncTaskStatus | undefined, conflictCount: number) {
  const queueCount = countLastFileStatus(status, (value) => TASK_CARD_QUEUE_STATUSES.has(value));
  const deletePendingCount = Math.max(
    status?.delete_pending_files ?? 0,
    countLastFileStatus(status, (value) => value === "delete_pending"),
  );
  const deleteFailedCount = status?.delete_failed_files ?? 0;
  const failedCount = status?.failed_files ?? 0;
  const parts: string[] = [];
  const details: string[] = [];

  if (queueCount > 0) {
    parts.push(`队列 ${queueCount}`);
    details.push(`队列 ${queueCount} 条表示等待上传、创建或重导入`);
  }
  if (deletePendingCount > 0) {
    parts.push(`待删 ${deletePendingCount}`);
    details.push(`待删 ${deletePendingCount} 条处于安全删除宽限队列，到期后自动执行`);
  }
  if (deleteFailedCount > 0) {
    parts.push(`删失败 ${deleteFailedCount}`);
    details.push(`删失败 ${deleteFailedCount} 条需要检查权限、占用或路径状态`);
  }
  if (failedCount > 0) {
    parts.push(`失败 ${failedCount}`);
    details.push(`失败 ${failedCount} 条需要查看错误并重试`);
  }
  if (conflictCount > 0) {
    parts.push(`冲突 ${conflictCount}`);
    details.push(`冲突 ${conflictCount} 条需要到事件管理选择保留版本`);
  }

  return {
    summary: parts.length > 0 ? parts.join("，") : "无",
    detail: details.join("；"),
  };
}

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
  onOpenDetail,
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
  const pendingDetail = buildTaskPendingDetail(status, conflictCount);

  return (
    <article className="min-w-0 rounded-xl border border-[#d7e4f5] bg-white p-5 shadow-[0_16px_40px_rgba(51,112,255,0.06)]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-2">
          <div className="flex min-w-0 flex-wrap items-center gap-3">
            <StatusPill label={health.label} tone={health.tone} dot={health.isRunning} />
            <p className="min-w-0 truncate text-lg font-semibold text-[#102033]">{task.name || "未命名任务"}</p>
          </div>
          <p className="text-xs text-[#6b7f96]">
            {summarizePath(task.local_path, 2, 42)} 与 {summarizePath(cloudPath, 2, 42)} 保持同步
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-[#52657a]">
          <span className="inline-flex items-center gap-2 rounded-lg border border-[#c9d8ec] bg-[#f8fbff] px-3 py-1">
            <ModeIcon mode={task.sync_mode} className="h-3.5 w-3.5" />
            {modeLabels[task.sync_mode] || task.sync_mode}
          </span>
          <span className="rounded-lg border border-[#c9d8ec] bg-[#f8fbff] px-3 py-1">
            更新：{updateModeLabels[task.update_mode || "auto"]}
          </span>
          <span className="rounded-lg border border-[#c9d8ec] bg-[#f8fbff] px-3 py-1">
            MD：
            {task.sync_mode === "download_only"
              ? "不适用（仅下载）"
              : mdSyncModeLabels[task.md_sync_mode || "enhanced"]}
          </span>
          <span className="rounded-lg border border-[#c9d8ec] bg-[#f8fbff] px-3 py-1">
            {deletePolicyLabel(task.delete_policy)}
          </span>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-[#d7e4f5] bg-[#f8fbff] p-4">
        <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_64px_minmax(0,1fr)] gap-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-[#ecfdf5] p-2 text-[#047857]">
              <IconFolder className="h-4 w-4" />
            </div>
            <div className="min-w-0 w-full">
              <div className="flex items-center justify-between gap-2">
                <p className="text-[11px] font-semibold uppercase tracking-widest text-[#6b7f96]">本地目录</p>
                <button
                  className="text-[11px] text-[#3370ff] hover:text-[#1d4ed8]"
                  onClick={() => onTogglePath("local")}
                  type="button"
                >
                  {localPathExpanded ? "收起" : "展开"}
                </button>
              </div>
              <button
                className={`mt-1 w-full text-left font-mono text-xs leading-relaxed text-[#334762] ${
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
            <span className="rounded-full border border-[#c9d8ec] bg-white p-2 text-[#3370ff] shadow-[0_8px_22px_rgba(51,112,255,0.12)]">
              <ModeIcon mode={task.sync_mode} className="h-4 w-4" />
            </span>
          </div>
          <div className="flex items-center justify-end gap-3 text-right">
            <div className="min-w-0 w-full">
              <div className="flex items-center justify-between gap-2">
                <p className="text-[11px] font-semibold uppercase tracking-widest text-[#6b7f96]">云端目录</p>
                <button
                  className="text-[11px] text-[#3370ff] hover:text-[#1d4ed8]"
                  onClick={() => onTogglePath("cloud")}
                  type="button"
                >
                  {cloudPathExpanded ? "收起" : "展开"}
                </button>
              </div>
              <button
                className={`mt-1 w-full text-left text-xs leading-relaxed text-[#334762] ${
                  cloudPathExpanded ? "break-all" : "truncate"
                }`}
                onClick={() => onTogglePath("cloud")}
                title={task.cloud_folder_token}
                type="button"
              >
                {cloudPathExpanded ? cloudPath : summarizePath(cloudPath)}
              </button>
            </div>
            <div className="rounded-xl bg-[#eaf2ff] p-2 text-[#3370ff]">
              <IconCloud className="h-4 w-4" />
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-[#6b7f96]">
        <span>最近同步：{lastSyncTime ? formatTimestamp(lastSyncTime) : "暂无"}</span>
        <span className="text-[#c9d8ec]">|</span>
        <span>待处理：{pendingDetail.summary}</span>
        <span className="text-[#c9d8ec]">|</span>
        <span>删除 {status?.deleted_files ?? 0}</span>
        <span className="text-[#c9d8ec]">|</span>
        <span>待删 {status?.delete_pending_files ?? 0}</span>
        <span className="text-[#c9d8ec]">|</span>
        <span>删失败 {status?.delete_failed_files ?? 0}</span>
        <span className="text-[#c9d8ec]">|</span>
        <span>失败 {status?.failed_files ?? 0}</span>
        <span className="text-[#c9d8ec]">|</span>
        <span>冲突 {conflictCount}</span>
        {progress !== null ? (
          <>
            <span className="text-[#c9d8ec]">|</span>
            <span>完成率：{progress}%</span>
          </>
        ) : null}
      </div>
      {pendingDetail.detail ? (
        <p className="mt-2 rounded-lg border border-[#f59e0b]/25 bg-[#fffbeb] px-3 py-2 text-xs leading-5 text-[#92400e]">
          待处理说明：{pendingDetail.detail}。
        </p>
      ) : null}
      {status?.last_error ? <p className="mt-2 text-xs text-[#be123c]">错误：{status.last_error}</p> : null}
      {progress !== null ? (
        <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-[#dce8f8]">
          <div className="h-full rounded-full bg-[#3370ff] transition-all" style={{ width: `${progress}%` }} />
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {onOpenDetail ? (
          <button
            className="inline-flex items-center gap-2 rounded-lg bg-[#3370ff] px-4 py-2 text-xs font-semibold text-white shadow-[0_10px_24px_rgba(51,112,255,0.2)] transition hover:bg-[#1d4ed8]"
            onClick={onOpenDetail}
            type="button"
          >
            查看详情
          </button>
        ) : null}
        <button
          className="inline-flex items-center gap-2 rounded-lg border border-[#10b981]/30 bg-[#ecfdf5] px-4 py-2 text-xs font-semibold text-[#047857] transition hover:bg-[#d1fae5] disabled:opacity-50"
          onClick={onRun}
          disabled={health.isRunning}
          type="button"
        >
          <IconPlay className="h-3.5 w-3.5" /> {health.isRunning ? "同步中" : "立即同步"}
        </button>
        <button
          className="rounded-lg border border-[#c9d8ec] px-4 py-2 text-xs font-medium text-[#334762] hover:bg-[#f6faff]"
          onClick={onToggleEnabled}
          type="button"
        >
          {task.enabled ? "停用" : "启用"}
        </button>
        <button
          className="inline-flex items-center gap-2 rounded-lg border border-[#f43f5e]/40 px-4 py-2 text-xs font-medium text-[#be123c] transition hover:bg-[#fff1f2]"
          onClick={onDelete}
          type="button"
        >
          <IconTrash className="h-3.5 w-3.5" /> 删除
        </button>
        <button
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#c9d8ec] px-4 py-2 text-xs font-medium text-[#3370ff] hover:bg-[#eef5ff]"
          onClick={onToggleExpanded}
          type="button"
        >
          {expanded ? <IconChevronDown className="h-3 w-3" /> : <IconChevronRight className="h-3 w-3" />}
          {expanded ? "收起管理" : "任务管理"}
        </button>
      </div>

      {expanded ? (
        <div className="mt-4 grid grid-cols-4 gap-4">
          <div className="col-span-4 rounded-xl border border-[#d7e4f5] bg-[#f8fbff] p-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-[#6b7f96]">高级信息</p>
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-[#52657a]">
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
          <div className="rounded-xl border border-[#d7e4f5] bg-[#f8fbff] p-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-[#6b7f96]">同步模式</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <select
                className="rounded-lg border border-[#c9d8ec] bg-white px-4 py-2 text-xs text-[#334762] outline-none focus:border-[#3370ff]"
                value={syncModeValue}
                onChange={(e) => onSyncModeChange(e.target.value)}
              >
                <option value="bidirectional">双向同步</option>
                <option value="download_only">仅下载</option>
                <option value="upload_only">仅上传</option>
              </select>
              <button
                className="rounded-lg border border-[#c9d8ec] bg-white px-4 py-2 text-xs font-medium text-[#3370ff] hover:bg-[#eef5ff]"
                onClick={onApplySyncMode}
                type="button"
              >
                应用
              </button>
            </div>
          </div>
          <div className="rounded-xl border border-[#d7e4f5] bg-[#f8fbff] p-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-[#6b7f96]">更新模式</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <select
                className="rounded-lg border border-[#c9d8ec] bg-white px-4 py-2 text-xs text-[#334762] outline-none focus:border-[#3370ff]"
                value={updateModeValue}
                onChange={(e) => onUpdateModeChange(e.target.value)}
              >
                <option value="auto">自动更新</option>
                <option value="partial">局部更新</option>
                <option value="full">全量覆盖</option>
              </select>
              <button
                className="rounded-lg border border-[#c9d8ec] bg-white px-4 py-2 text-xs font-medium text-[#3370ff] hover:bg-[#eef5ff]"
                onClick={onApplyUpdateMode}
                type="button"
              >
                应用
              </button>
            </div>
          </div>
          <div className="rounded-xl border border-[#d7e4f5] bg-[#f8fbff] p-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-[#6b7f96]">MD 上传模式</p>
            {taskUploadEnabled ? (
              <>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <select
                    className="rounded-lg border border-[#c9d8ec] bg-white px-4 py-2 text-xs text-[#334762] outline-none focus:border-[#3370ff]"
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
                    className="rounded-lg border border-[#c9d8ec] bg-white px-4 py-2 text-xs font-medium text-[#3370ff] hover:bg-[#eef5ff]"
                    onClick={onApplyMdSyncMode}
                    type="button"
                  >
                    应用
                  </button>
                </div>
                <p className="mt-2 text-[11px] leading-5 text-[#6b7f96]">
                  {mdSyncModeValue === "enhanced"
                    ? "增强：上传云文档，并维护云端 MD 副本目录。"
                    : mdSyncModeValue === "download_only"
                      ? "仅下载：不执行本地 MD 上行，适合把飞书作为默认编辑端。"
                      : "仅云文档：只更新云文档，不保留云端 MD 副本（复杂格式可能有损耗）。"}
                </p>
              </>
            ) : (
              <p className="mt-3 text-sm leading-6 text-[#6b7f96]">
                当前任务为仅下载，不会执行本地 Markdown 上行，因此不显示 MD 上传配置。
              </p>
            )}
          </div>
          <div className="rounded-xl border border-[#d7e4f5] bg-[#f8fbff] p-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-[#6b7f96]">删除策略</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <select
                className="rounded-lg border border-[#c9d8ec] bg-white px-3 py-2 text-xs text-[#334762] outline-none focus:border-[#3370ff]"
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
                className="w-20 rounded-lg border border-[#c9d8ec] bg-white px-3 py-2 text-xs text-[#334762] outline-none disabled:bg-[#edf3fb] disabled:text-[#9fb2c8] focus:border-[#3370ff]"
                type="number"
                min="0"
                step="1"
                value={deleteGraceValue}
                onChange={(e) => onDeleteGraceChange(e.target.value)}
                disabled={deletePolicyValue === "strict"}
              />
              <span className="text-xs text-[#6b7f96]">分钟</span>
              <button
                className="rounded-lg border border-[#c9d8ec] bg-white px-4 py-2 text-xs font-medium text-[#3370ff] hover:bg-[#eef5ff]"
                onClick={onApplyDeletePolicy}
                type="button"
              >
                应用
              </button>
            </div>
            <p className="mt-2 text-[11px] leading-5 text-[#6b7f96]">
              {deletePolicyValue === "off"
                ? "关闭：本地删除和云端删除都不联动。"
                : deletePolicyValue === "safe"
                  ? "安全：先进入删除待处理，宽限后执行；云端删本地时先移入 .larksync_trash。"
                  : `严格：删除会尽快联动执行，宽限时间固定为 ${deleteGraceMinutes} 分钟。`}
            </p>
          </div>
        </div>
      ) : null}
    </article>
  );
}
