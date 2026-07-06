import { formatTimestamp } from "../../lib/formatters";
import { statusLabelMap } from "../../lib/constants";
import { StatusPill } from "../StatusPill";
import { IconActivity, IconConflicts, IconRefresh } from "../Icons";
import { cn } from "../../lib/utils";
import {
  getConflictStatusMeta,
  type ConflictResolutionStatus,
  type ConflictResolutionSummary,
} from "../../lib/conflictResolution";
import type { ConflictItem, ConflictResolutionAction, SyncLogEntry, Tone } from "../../types";

type EventManagementPanelProps = {
  eventEntries: SyncLogEntry[];
  eventTotal: number;
  eventLoading: boolean;
  eventError: string | null;
  refreshEvents: () => void;
  conflicts: ConflictItem[];
  conflictLoading: boolean;
  conflictError: string | null;
  refreshConflicts: () => void;
  queueSummary: ConflictResolutionSummary;
  conflictResolutionStates: Record<string, ConflictResolutionStatus>;
  onResolveConflict: (id: string, action: ConflictResolutionAction, successMessage: string) => void;
  conflictActionLabels: Record<ConflictResolutionAction, string>;
};

const DANGER_EVENT_STATUSES = new Set(["failed", "delete_failed", "cancelled"]);
const WARNING_EVENT_STATUSES = new Set(["delete_pending", "conflict"]);

function getEventTone(status: string): Tone {
  if (DANGER_EVENT_STATUSES.has(status)) return "danger";
  if (WARNING_EVENT_STATUSES.has(status)) return "warning";
  return "info";
}

function getEventMeaning(entry: SyncLogEntry): string {
  if (entry.status === "delete_pending") {
    return "已进入安全删除宽限队列；到期后自动删除，通常不需要手动处理。";
  }
  if (entry.status === "delete_failed") {
    return "删除动作执行失败，需要检查权限、占用或路径状态。";
  }
  if (entry.status === "failed") {
    return "同步动作失败，需要根据错误信息排查后重试。";
  }
  if (entry.status === "conflict") {
    return "本地与云端同时变化，需要在下方冲突处理中选择保留版本。";
  }
  if (entry.status === "cancelled") {
    return "本次同步被取消；如果不是预期操作，请重新运行任务。";
  }
  return "事件已记录，可结合任务诊断查看上下文。";
}

export function EventManagementPanel({
  eventEntries,
  eventTotal,
  eventLoading,
  eventError,
  refreshEvents,
  conflicts,
  conflictLoading,
  conflictError,
  refreshConflicts,
  queueSummary,
  conflictResolutionStates,
  onResolveConflict,
  conflictActionLabels,
}: EventManagementPanelProps) {
  const unresolvedConflicts = conflicts.filter((conflict) => !conflict.resolved).length;
  const deletePendingCount = eventEntries.filter((event) => event.status === "delete_pending").length;
  const failedCount = eventEntries.filter((event) => event.status === "failed" || event.status === "delete_failed").length;
  const conflictEventCount = eventEntries.filter((event) => event.status === "conflict").length;
  const cancelledCount = eventEntries.filter((event) => event.status === "cancelled").length;
  const summaryItems = [
    {
      label: "待删除",
      value: deletePendingCount,
      tone: deletePendingCount > 0 ? "warning" : "success",
      hint: "安全宽限队列，到期自动执行",
    },
    {
      label: "失败",
      value: failedCount,
      tone: failedCount > 0 ? "danger" : "success",
      hint: "需要排查权限、网络或接口错误",
    },
    {
      label: "冲突",
      value: unresolvedConflicts + conflictEventCount,
      tone: unresolvedConflicts + conflictEventCount > 0 ? "warning" : "success",
      hint: "需要选择本地或云端版本",
    },
    {
      label: "取消",
      value: cancelledCount,
      tone: cancelledCount > 0 ? "danger" : "success",
      hint: "确认是否为预期停止",
    },
  ] as const;

  const refreshAll = () => {
    refreshEvents();
    refreshConflicts();
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
        <div>
          <h3 className="text-lg font-semibold text-zinc-50">事件管理</h3>
          <p className="mt-1 text-xs text-zinc-400">
            统一查看待删除、失败、取消和冲突事件；只有失败与未解决冲突通常需要人工处理。
          </p>
        </div>
        <button
          className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
          onClick={refreshAll}
          disabled={eventLoading || conflictLoading}
          type="button"
        >
          <IconRefresh className="h-3.5 w-3.5" /> {eventLoading || conflictLoading ? "加载中..." : "刷新"}
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {summaryItems.map((item) => (
          <div key={item.label} className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs text-zinc-500">{item.label}</span>
              <StatusPill label={String(item.value)} tone={item.tone} />
            </div>
            <p className="mt-2 text-xs text-zinc-400">{item.hint}</p>
          </div>
        ))}
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h4 className="text-base font-semibold text-zinc-50">最近关注事件</h4>
            <p className="mt-1 text-xs text-zinc-500">
              当前展示 {eventEntries.length} 条，接口共返回 {eventTotal} 条匹配事件。
            </p>
          </div>
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-3 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
            onClick={refreshEvents}
            disabled={eventLoading}
            type="button"
          >
            <IconRefresh className="h-3.5 w-3.5" /> 刷新事件
          </button>
        </div>
        {eventError ? <p className="mt-3 text-sm text-rose-400">事件加载失败：{eventError}</p> : null}
        <div className="mt-4 space-y-3">
          {eventLoading && eventEntries.length === 0 ? (
            [1, 2, 3].map((item) => <div key={item} className="h-24 animate-pulse rounded-xl bg-zinc-800/50" />)
          ) : eventEntries.length === 0 ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 py-10 text-center">
              <IconActivity className="mx-auto h-10 w-10 text-emerald-500/70" />
              <p className="mt-3 text-sm text-zinc-400">暂无需要关注的事件。</p>
            </div>
          ) : (
            eventEntries.map((entry, index) => (
              <div key={`${entry.taskId}-${entry.timestamp}-${index}`} className="rounded-xl border border-zinc-800 bg-zinc-950/45 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 space-y-1">
                    <p className="text-xs text-zinc-500">{formatTimestamp(entry.timestamp)}</p>
                    <p className="truncate text-sm font-semibold text-zinc-100">{entry.taskName || "未命名任务"}</p>
                  </div>
                  <StatusPill label={statusLabelMap[entry.status] || entry.status} tone={getEventTone(entry.status)} />
                </div>
                <p className="mt-2 break-words text-xs text-zinc-500">{entry.path || "无路径"}</p>
                {entry.message ? <p className="mt-1 break-words text-xs text-zinc-400">{entry.message}</p> : null}
                <p className="mt-2 text-xs text-zinc-500">{getEventMeaning(entry)}</p>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h4 className="text-base font-semibold text-zinc-50">冲突处理</h4>
            <p className="mt-1 text-xs text-zinc-500">
              仅当本地与云端同时修改同一文档时需要选择版本；已解决冲突会保留记录。
            </p>
          </div>
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-3 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
            onClick={refreshConflicts}
            disabled={conflictLoading}
            type="button"
          >
            <IconRefresh className="h-3.5 w-3.5" /> 刷新冲突
          </button>
        </div>

        {(queueSummary.queued > 0 || queueSummary.running > 0 || queueSummary.waiting > 0 || queueSummary.success > 0 || queueSummary.failed > 0) ? (
          <div className="mt-4 rounded-2xl border border-[#3370FF]/30 bg-[#3370FF]/10 px-4 py-3 text-sm text-zinc-200">
            当前冲突处理队列：处理中 {queueSummary.running} 条，等待任务空闲 {queueSummary.waiting} 条，排队中 {queueSummary.queued} 条，最近成功 {queueSummary.success} 条，失败 {queueSummary.failed} 条。
          </div>
        ) : null}
        {conflictError ? <p className="mt-3 text-sm text-rose-400">冲突加载失败：{conflictError}</p> : null}
        <div className="mt-4 space-y-4">
          {conflicts.length === 0 ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 py-10 text-center">
              <IconConflicts className="mx-auto h-10 w-10 text-zinc-700" />
              <p className="mt-3 text-sm text-zinc-500">暂无需要手动处理的冲突。</p>
            </div>
          ) : (
            conflicts.map((conflict) => {
              const resolutionState = conflictResolutionStates[conflict.id];
              const meta = getConflictStatusMeta(conflict.resolved, conflict.resolved_action, resolutionState);
              const disabled = conflict.resolved || (resolutionState ? resolutionState.state !== "error" : false);
              const primaryLabel = resolutionState?.state === "running"
                ? "处理中..."
                : resolutionState?.state === "waiting"
                  ? "等待重试..."
                  : resolutionState?.state === "queued"
                    ? "已排队"
                    : "使用本地";
              const secondaryLabel = resolutionState?.state === "running"
                ? "处理中..."
                : resolutionState?.state === "waiting"
                  ? "等待重试..."
                  : resolutionState?.state === "queued"
                    ? "已排队"
                    : "使用云端";
              return (
                <div key={conflict.id} className="rounded-2xl border border-zinc-800 bg-zinc-950/45 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0 space-y-1">
                      <p className="text-xs uppercase tracking-widest text-zinc-500">本地路径</p>
                      <p className="break-words text-sm text-zinc-200">{conflict.local_path}</p>
                      <p className="break-words text-xs text-zinc-500">云端 token：{conflict.cloud_token}</p>
                      <p className="text-xs text-zinc-600">哈希：{conflict.local_hash.slice(0, 8)} / {conflict.db_hash.slice(0, 8)}</p>
                    </div>
                    <StatusPill label={meta.label} tone={meta.tone} />
                  </div>
                  <div className="mt-4 grid gap-4 lg:grid-cols-2">
                    <div>
                      <p className="text-xs uppercase tracking-widest text-zinc-500">本地版本</p>
                      <pre className="mt-2 max-h-56 overflow-auto rounded-lg border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs text-zinc-300">
                        {conflict.local_preview || "暂无本地预览。"}
                      </pre>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-widest text-zinc-500">云端版本</p>
                      <pre className="mt-2 max-h-56 overflow-auto rounded-lg border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs text-zinc-300">
                        {conflict.cloud_preview || "暂无云端预览。"}
                      </pre>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <button
                      className="rounded-lg bg-emerald-500/20 px-4 py-2 text-xs font-semibold text-emerald-300 transition hover:bg-emerald-500/30 disabled:opacity-50"
                      disabled={disabled}
                      onClick={() => onResolveConflict(conflict.id, "use_local", "已采用本地版本")}
                      type="button"
                    >
                      {primaryLabel}
                    </button>
                    <button
                      className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 transition hover:bg-zinc-800 disabled:opacity-50"
                      disabled={disabled}
                      onClick={() => onResolveConflict(conflict.id, "use_cloud", "已采用云端版本")}
                      type="button"
                    >
                      {secondaryLabel}
                    </button>
                    {conflict.resolved ? (
                      <span className="self-center text-xs text-zinc-500">已处理：{conflict.resolved_action}</span>
                    ) : resolutionState ? (
                      <span className={cn(
                        "self-center text-xs",
                        resolutionState.state === "error"
                          ? "text-rose-400"
                          : resolutionState.state === "success"
                            ? "text-emerald-300"
                            : resolutionState.state === "waiting"
                              ? "text-amber-300"
                              : "text-zinc-500",
                      )}>
                        {meta.label}：
                        {conflictActionLabels[resolutionState.action]}
                        {resolutionState.message ? `，${resolutionState.message}` : ""}
                      </span>
                    ) : null}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
