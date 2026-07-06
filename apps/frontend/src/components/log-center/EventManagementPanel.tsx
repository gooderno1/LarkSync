import { useMemo, useState } from "react";

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

type EventViewMode = "issue" | "task";
type ManagedEventStatus = "failed" | "delete_failed" | "conflict" | "delete_pending" | "cancelled";

type EventStatusMeta = {
  label: string;
  tone: Tone;
  summary: string;
  action: string;
};

type IssueGroup = {
  status: ManagedEventStatus;
  meta: EventStatusMeta;
  entries: SyncLogEntry[];
};

type TaskEventGroup = {
  key: string;
  taskName: string;
  latestAt: number;
  counts: Record<ManagedEventStatus, number>;
  entries: SyncLogEntry[];
};

const EVENT_STATUS_ORDER: ManagedEventStatus[] = [
  "failed",
  "delete_failed",
  "conflict",
  "delete_pending",
  "cancelled",
];

const EVENT_META: Record<ManagedEventStatus, EventStatusMeta> = {
  failed: {
    label: "同步失败",
    tone: "danger",
    summary: "同步动作没有完成",
    action: "需要查看错误信息，修正权限、网络或接口问题后重试任务。",
  },
  delete_failed: {
    label: "删除失败",
    tone: "danger",
    summary: "删除动作执行失败",
    action: "需要检查文件占用、路径变化或云端/本地权限，再重新运行同步。",
  },
  conflict: {
    label: "冲突",
    tone: "warning",
    summary: "本地与云端同时变化",
    action: "需要在冲突处理区选择保留本地版本或云端版本。",
  },
  delete_pending: {
    label: "待删除",
    tone: "warning",
    summary: "安全删除宽限队列",
    action: "如果删除是预期行为，无需手动处理；如果不是预期，请在源端恢复文件或调整删除策略。",
  },
  cancelled: {
    label: "已取消",
    tone: "neutral",
    summary: "同步被停止",
    action: "如果不是手动停止，请重新运行任务并观察是否再次中断。",
  },
};

function toManagedEventStatus(status: string): ManagedEventStatus | null {
  return EVENT_STATUS_ORDER.includes(status as ManagedEventStatus)
    ? (status as ManagedEventStatus)
    : null;
}

function getEventMeta(status: string): EventStatusMeta {
  const managedStatus = toManagedEventStatus(status);
  return managedStatus
    ? EVENT_META[managedStatus]
    : {
      label: statusLabelMap[status] || status,
      tone: "info",
      summary: "同步事件",
      action: "事件已记录，可结合任务诊断查看上下文。",
    };
}

function createEmptyCounts(): Record<ManagedEventStatus, number> {
  return EVENT_STATUS_ORDER.reduce((acc, status) => {
    acc[status] = 0;
    return acc;
  }, {} as Record<ManagedEventStatus, number>);
}

function buildTaskGroupSummary(group: TaskEventGroup): string {
  const parts: string[] = [];
  if (group.counts.failed > 0) parts.push(`同步失败 ${group.counts.failed} 条需要排查后重试`);
  if (group.counts.delete_failed > 0) parts.push(`删除失败 ${group.counts.delete_failed} 条需要检查权限或占用`);
  if (group.counts.conflict > 0) parts.push(`冲突 ${group.counts.conflict} 条需要选择版本`);
  if (group.counts.delete_pending > 0) parts.push(`待删除 ${group.counts.delete_pending} 条处于安全宽限队列`);
  if (group.counts.cancelled > 0) parts.push(`取消 ${group.counts.cancelled} 条需要确认是否为预期停止`);
  return parts.length > 0 ? parts.join("；") : "暂无需要处理的问题。";
}

function renderEventRow(entry: SyncLogEntry, key: string) {
  const meta = getEventMeta(entry.status);
  return (
    <div key={key} className="rounded-lg border border-zinc-800 bg-zinc-950/40 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[11px] text-zinc-500">{formatTimestamp(entry.timestamp)}</p>
          <p className="mt-0.5 truncate text-xs font-medium text-zinc-200">{entry.taskName || "未命名任务"}</p>
        </div>
        <StatusPill label={statusLabelMap[entry.status] || meta.label} tone={meta.tone} />
      </div>
      <p className="mt-2 break-words text-xs text-zinc-500">{entry.path || "无路径"}</p>
      {entry.message ? <p className="mt-1 break-words text-xs text-zinc-400">{entry.message}</p> : null}
      <p className="mt-2 text-xs leading-5 text-zinc-500">{meta.action}</p>
    </div>
  );
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
  const [eventViewMode, setEventViewMode] = useState<EventViewMode>("issue");
  const unresolvedConflicts = conflicts.filter((conflict) => !conflict.resolved).length;
  const hasConflictQueue = queueSummary.queued > 0 || queueSummary.running > 0 || queueSummary.waiting > 0 || queueSummary.success > 0 || queueSummary.failed > 0;
  const shouldShowConflictPanel = conflicts.length > 0 || Boolean(conflictError) || hasConflictQueue;

  const issueGroups = useMemo<IssueGroup[]>(() => {
    const grouped = EVENT_STATUS_ORDER.reduce((acc, status) => {
      acc[status] = [];
      return acc;
    }, {} as Record<ManagedEventStatus, SyncLogEntry[]>);
    for (const entry of eventEntries) {
      const status = toManagedEventStatus(entry.status);
      if (status) grouped[status].push(entry);
    }
    return EVENT_STATUS_ORDER
      .map((status) => ({
        status,
        meta: EVENT_META[status],
        entries: grouped[status],
      }))
      .filter((group) => group.entries.length > 0 || (group.status === "conflict" && unresolvedConflicts > 0));
  }, [eventEntries, unresolvedConflicts]);

  const taskGroups = useMemo<TaskEventGroup[]>(() => {
    const grouped = new Map<string, TaskEventGroup>();
    for (const entry of eventEntries) {
      const key = entry.taskId || entry.taskName || entry.path || "unknown-task";
      const current = grouped.get(key) ?? {
        key,
        taskName: entry.taskName || "未命名任务",
        latestAt: entry.timestamp,
        counts: createEmptyCounts(),
        entries: [],
      };
      const status = toManagedEventStatus(entry.status);
      if (status) current.counts[status] += 1;
      current.latestAt = Math.max(current.latestAt, entry.timestamp);
      current.entries.push(entry);
      grouped.set(key, current);
    }
    return Array.from(grouped.values()).sort((a, b) => b.latestAt - a.latestAt);
  }, [eventEntries]);

  const statusSummary = EVENT_STATUS_ORDER.map((status) => {
    const count = eventEntries.filter((event) => event.status === status).length;
    return {
      status,
      count,
      meta: EVENT_META[status],
    };
  });

  const refreshAll = () => {
    refreshEvents();
    refreshConflicts();
  };

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <h3 className="text-base font-semibold text-zinc-50">待处理事件</h3>
            <p className="mt-1 text-xs text-zinc-500">
              展示 {eventEntries.length} 条关注事件{eventTotal > eventEntries.length ? `，接口匹配 ${eventTotal} 条` : ""}；未解决冲突 {unresolvedConflicts} 条。
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-lg border border-zinc-800 bg-zinc-950/50 p-1">
              <button
                className={cn(
                  "rounded-md px-3 py-1.5 text-xs font-medium transition",
                  eventViewMode === "issue"
                    ? "bg-zinc-100 text-zinc-950"
                    : "text-zinc-400 hover:text-zinc-200",
                )}
                onClick={() => setEventViewMode("issue")}
                type="button"
              >
                按问题
              </button>
              <button
                className={cn(
                  "rounded-md px-3 py-1.5 text-xs font-medium transition",
                  eventViewMode === "task"
                    ? "bg-zinc-100 text-zinc-950"
                    : "text-zinc-400 hover:text-zinc-200",
                )}
                onClick={() => setEventViewMode("task")}
                type="button"
              >
                按任务
              </button>
            </div>
            <button
              className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-3 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
              onClick={refreshAll}
              disabled={eventLoading || conflictLoading}
              type="button"
            >
              <IconRefresh className="h-3.5 w-3.5" /> {eventLoading || conflictLoading ? "加载中..." : "刷新"}
            </button>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {statusSummary.map(({ status, count, meta }) => (
            <div key={status} className="rounded-lg border border-zinc-800 bg-zinc-950/30 px-3 py-2 text-xs">
              <span className="text-zinc-500">{meta.label}</span>
              <span className={cn(
                "ml-2 font-semibold",
                count === 0
                  ? "text-zinc-500"
                  : meta.tone === "danger"
                    ? "text-rose-300"
                    : meta.tone === "warning"
                      ? "text-amber-300"
                      : "text-zinc-300",
              )}>
                {count}
              </span>
            </div>
          ))}
        </div>

        {eventError ? <p className="mt-3 text-sm text-rose-400">事件加载失败：{eventError}</p> : null}

        <div className="mt-5">
          {eventLoading && eventEntries.length === 0 ? (
            <div className="grid gap-3 lg:grid-cols-2">
              {[1, 2, 3, 4].map((item) => <div key={item} className="h-32 animate-pulse rounded-xl bg-zinc-800/50" />)}
            </div>
          ) : eventEntries.length === 0 && unresolvedConflicts === 0 ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 py-10 text-center">
              <IconActivity className="mx-auto h-10 w-10 text-zinc-600" />
              <p className="mt-3 text-sm text-zinc-400">暂无需要关注的事件。</p>
            </div>
          ) : eventViewMode === "issue" ? (
            <div className="grid gap-3 xl:grid-cols-2">
              {issueGroups.map((group) => (
                <article key={group.status} className="rounded-xl border border-zinc-800 bg-zinc-950/35 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h4 className="text-sm font-semibold text-zinc-100">{group.meta.label}</h4>
                        <StatusPill label={`${group.entries.length} 条`} tone={group.entries.length > 0 ? group.meta.tone : "neutral"} />
                      </div>
                      <p className="mt-1 text-xs text-zinc-500">{group.meta.summary}</p>
                    </div>
                  </div>
                  <p className="mt-3 rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2 text-xs leading-5 text-zinc-400">
                    {group.meta.action}
                  </p>
                  <div className="mt-3 space-y-2">
                    {group.entries.length === 0 ? (
                      <p className="rounded-lg border border-zinc-800 bg-zinc-950/40 px-3 py-4 text-center text-xs text-zinc-500">
                        当前没有对应日志事件，未解决冲突见下方处理区。
                      </p>
                    ) : (
                      group.entries.slice(0, 6).map((entry, index) => renderEventRow(entry, `${group.status}-${entry.taskId}-${entry.timestamp}-${index}`))
                    )}
                    {group.entries.length > 6 ? (
                      <p className="text-center text-xs text-zinc-500">还有 {group.entries.length - 6} 条同类事件，可切换“按任务”查看来源。</p>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="grid gap-3 xl:grid-cols-2">
              {taskGroups.map((group) => (
                <article key={group.key} className="rounded-xl border border-zinc-800 bg-zinc-950/35 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h4 className="truncate text-sm font-semibold text-zinc-100">{group.taskName}</h4>
                      <p className="mt-1 text-xs text-zinc-500">最近事件：{formatTimestamp(group.latestAt)}</p>
                    </div>
                    <StatusPill label={`${group.entries.length} 条`} tone="info" />
                  </div>
                  <p className="mt-3 rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2 text-xs leading-5 text-zinc-400">
                    {buildTaskGroupSummary(group)}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {EVENT_STATUS_ORDER.filter((status) => group.counts[status] > 0).map((status) => (
                      <StatusPill key={status} label={`${EVENT_META[status].label} ${group.counts[status]}`} tone={EVENT_META[status].tone} />
                    ))}
                  </div>
                  <div className="mt-3 space-y-2">
                    {group.entries.slice(0, 4).map((entry, index) => renderEventRow(entry, `${group.key}-${entry.timestamp}-${index}`))}
                    {group.entries.length > 4 ? (
                      <p className="text-center text-xs text-zinc-500">还有 {group.entries.length - 4} 条该任务事件。</p>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>

      {shouldShowConflictPanel ? (
        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h4 className="text-base font-semibold text-zinc-50">冲突处理</h4>
              <p className="mt-1 text-xs text-zinc-500">
                只有未解决冲突需要选择版本；已解决冲突保留记录。
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

          {hasConflictQueue ? (
            <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950/40 px-4 py-3 text-sm text-zinc-300">
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
                  <div key={conflict.id} className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-5">
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
        </section>
      ) : null}
    </div>
  );
}
