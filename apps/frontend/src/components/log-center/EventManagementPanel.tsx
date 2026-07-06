import { useMemo, useState } from "react";

import {
  buildEventIssueGroups,
  buildTaskEventGroups,
  buildTaskSummaryText,
  classifyEventProblem,
  eventStatusDisplay,
  type EventIssueGroup,
  type TaskEventGroup,
} from "../../lib/eventManagement";
import { formatTimestamp } from "../../lib/formatters";
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
  eventWarning?: string | null;
  showAllEvents: boolean;
  setShowAllEvents: (value: boolean | ((value: boolean) => boolean)) => void;
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

function matchEventSearch(entry: SyncLogEntry, keyword: string): boolean {
  if (!keyword) return true;
  const problem = classifyEventProblem(entry);
  const haystack = [
    entry.taskName,
    entry.path,
    entry.message,
    entry.status,
    problem.title,
    problem.shortLabel,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return haystack.includes(keyword);
}

function toneTextClass(tone: Tone): string {
  if (tone === "danger") return "text-rose-300";
  if (tone === "warning") return "text-amber-300";
  if (tone === "success") return "text-emerald-300";
  if (tone === "info") return "text-blue-300";
  return "text-zinc-300";
}

function renderEventRow(entry: SyncLogEntry, key: string) {
  const problem = classifyEventProblem(entry);
  return (
    <div key={key} className="rounded-lg border border-zinc-800 bg-zinc-950/45 px-3 py-2.5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[11px] text-zinc-500">{formatTimestamp(entry.timestamp)}</p>
          <p className="mt-0.5 truncate text-xs font-medium text-zinc-200">{entry.taskName || "未命名任务"}</p>
        </div>
        <StatusPill label={eventStatusDisplay(entry)} tone={problem.tone} />
      </div>
      <p className="mt-2 break-words font-mono text-[11px] leading-5 text-zinc-500">{entry.path || "无路径"}</p>
      {entry.message ? <p className="mt-1 break-words text-xs leading-5 text-zinc-400">{entry.message}</p> : null}
    </div>
  );
}

function EventIssueListItem({
  group,
  selected,
  onSelect,
}: {
  group: EventIssueGroup;
  selected: boolean;
  onSelect: () => void;
}) {
  const sourceText = group.taskNames.length > 0
    ? group.taskNames.slice(0, 2).join(" / ")
    : group.unresolvedConflictCount
      ? "冲突处理队列"
      : "未记录任务";
  return (
    <button
      className={cn(
        "w-full rounded-lg border px-3 py-3 text-left transition",
        selected
          ? "border-[#3370FF]/50 bg-[#3370FF]/10"
          : "border-zinc-800 bg-zinc-950/40 hover:border-zinc-700 hover:bg-zinc-950/60",
      )}
      onClick={onSelect}
      type="button"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-zinc-100">{group.problem.title}</p>
          <p className="mt-1 text-xs leading-5 text-zinc-500">{group.problem.summary}</p>
        </div>
        <StatusPill label={`${group.count} 条`} tone={group.problem.tone} />
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-zinc-500">
        <span className={toneTextClass(group.problem.tone)}>{group.problem.needsAction ? "需要处理" : "状态说明"}</span>
        <span className="text-zinc-700">|</span>
        <span className="truncate">{sourceText}</span>
      </div>
    </button>
  );
}

function TaskEventListItem({
  group,
  selected,
  onSelect,
}: {
  group: TaskEventGroup;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      className={cn(
        "w-full rounded-lg border px-3 py-3 text-left transition",
        selected
          ? "border-[#3370FF]/50 bg-[#3370FF]/10"
          : "border-zinc-800 bg-zinc-950/40 hover:border-zinc-700 hover:bg-zinc-950/60",
      )}
      onClick={onSelect}
      type="button"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-zinc-100">{group.taskName}</p>
          <p className="mt-1 text-xs leading-5 text-zinc-500">{buildTaskSummaryText(group)}</p>
        </div>
        <StatusPill label={`${group.entries.length} 条`} tone={group.needsActionCount > 0 ? "danger" : "neutral"} />
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {group.problemSummaries.slice(0, 3).map(({ problem, count }) => (
          <StatusPill key={problem.key} label={`${problem.shortLabel} ${count}`} tone={problem.tone} />
        ))}
      </div>
    </button>
  );
}

function IssueDetail({ group }: { group: EventIssueGroup }) {
  return (
    <div className="space-y-4">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill label={group.problem.needsAction ? "需要处理" : "无需立即处理"} tone={group.problem.tone} />
          <StatusPill label={`${group.count} 条事件`} tone="neutral" />
        </div>
        <h4 className="mt-3 text-base font-semibold text-zinc-50">{group.problem.title}</h4>
        <p className="mt-2 text-sm leading-6 text-zinc-400">{group.problem.summary}</p>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <div className="rounded-lg border border-zinc-800 bg-zinc-950/35 p-3">
          <p className="text-[11px] uppercase tracking-widest text-zinc-500">原因</p>
          <p className="mt-2 text-xs leading-5 text-zinc-300">{group.problem.cause}</p>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-950/35 p-3">
          <p className="text-[11px] uppercase tracking-widest text-zinc-500">建议动作</p>
          <p className="mt-2 text-xs leading-5 text-zinc-300">{group.problem.recommendedAction}</p>
        </div>
      </div>

      <div>
        <p className="text-[11px] uppercase tracking-widest text-zinc-500">影响范围</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {group.taskNames.length > 0 ? (
            group.taskNames.slice(0, 6).map((taskName) => (
              <span key={taskName} className="rounded-full border border-zinc-800 bg-zinc-950/50 px-3 py-1 text-xs text-zinc-300">
                {taskName}
              </span>
            ))
          ) : (
            <span className="text-xs text-zinc-500">暂无任务来源；可能只有冲突队列记录。</span>
          )}
        </div>
      </div>
    </div>
  );
}

function TaskDetail({ group }: { group: TaskEventGroup }) {
  const primaryProblem = group.problemSummaries[0]?.problem;
  return (
    <div className="space-y-4">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill label={`${group.entries.length} 条事件`} tone="neutral" />
          {group.needsActionCount > 0 ? <StatusPill label={`需处理 ${group.needsActionCount} 条`} tone="danger" /> : null}
        </div>
        <h4 className="mt-3 text-base font-semibold text-zinc-50">{group.taskName}</h4>
        <p className="mt-2 text-sm leading-6 text-zinc-400">{buildTaskSummaryText(group)}</p>
      </div>

      <div className="space-y-2">
        <p className="text-[11px] uppercase tracking-widest text-zinc-500">待处理组成</p>
        {group.problemSummaries.map(({ problem, count }) => (
          <div key={problem.key} className="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-zinc-800 bg-zinc-950/35 px-3 py-2.5">
            <div className="min-w-0">
              <p className="text-sm font-medium text-zinc-100">{problem.title}</p>
              <p className="mt-1 text-xs leading-5 text-zinc-500">{problem.recommendedAction}</p>
            </div>
            <StatusPill label={`${count} 条`} tone={problem.tone} />
          </div>
        ))}
      </div>

      {primaryProblem ? (
        <div className="rounded-lg border border-zinc-800 bg-zinc-950/35 p-3">
          <p className="text-[11px] uppercase tracking-widest text-zinc-500">优先排查</p>
          <p className="mt-2 text-xs leading-5 text-zinc-300">{primaryProblem.cause}</p>
        </div>
      ) : null}
    </div>
  );
}

export function EventManagementPanel({
  eventEntries,
  eventTotal,
  eventLoading,
  eventError,
  eventWarning,
  showAllEvents,
  setShowAllEvents,
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
  const [eventSearch, setEventSearch] = useState("");
  const [selectedIssueKey, setSelectedIssueKey] = useState<string | null>(null);
  const [selectedTaskKey, setSelectedTaskKey] = useState<string | null>(null);

  const unresolvedConflicts = conflicts.filter((conflict) => !conflict.resolved).length;
  const hasConflictQueue = queueSummary.queued > 0 || queueSummary.running > 0 || queueSummary.waiting > 0 || queueSummary.success > 0 || queueSummary.failed > 0;
  const shouldShowConflictPanel = conflicts.length > 0 || Boolean(conflictError) || hasConflictQueue;
  const searchKeyword = eventSearch.trim().toLowerCase();

  const filteredEntries = useMemo(
    () => eventEntries.filter((entry) => matchEventSearch(entry, searchKeyword)),
    [eventEntries, searchKeyword],
  );

  const issueGroups = useMemo(
    () => buildEventIssueGroups(filteredEntries, {
      includeInformational: showAllEvents,
      unresolvedConflictCount: unresolvedConflicts,
    }),
    [filteredEntries, showAllEvents, unresolvedConflicts],
  );

  const taskGroups = useMemo(
    () => buildTaskEventGroups(filteredEntries, { includeInformational: showAllEvents }),
    [filteredEntries, showAllEvents],
  );

  const activeIssueGroup = issueGroups.find((group) => group.key === selectedIssueKey) ?? issueGroups[0] ?? null;
  const activeTaskGroup = taskGroups.find((group) => group.key === selectedTaskKey) ?? taskGroups[0] ?? null;
  const activeEntries = eventViewMode === "issue" ? activeIssueGroup?.entries ?? [] : activeTaskGroup?.entries ?? [];

  const refreshAll = () => {
    refreshEvents();
    refreshConflicts();
  };

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="text-base font-semibold text-zinc-50">事件管理</h3>
            <p className="mt-1 text-xs text-zinc-500">
              {showAllEvents ? "正在显示最近同步事件" : "默认只显示失败、冲突、删除和取消等需关注事件"}
              {eventTotal > filteredEntries.length ? `；本页载入 ${filteredEntries.length} 条，接口返回总量 ${eventTotal} 条` : ""}；未解决冲突 {unresolvedConflicts} 条。
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-lg border border-zinc-800 bg-zinc-950/50 p-1">
              <button
                className={cn(
                  "rounded-md px-3 py-1.5 text-xs font-medium transition",
                  eventViewMode === "issue"
                    ? "border border-[#3370FF]/40 bg-[#3370FF]/10 text-[#3370FF]"
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
                    ? "border border-[#3370FF]/40 bg-[#3370FF]/10 text-[#3370FF]"
                    : "text-zinc-400 hover:text-zinc-200",
                )}
                onClick={() => setEventViewMode("task")}
                type="button"
              >
                按任务
              </button>
            </div>
            <button
              className={cn(
                "rounded-lg border px-3 py-2 text-xs font-medium transition",
                showAllEvents
                  ? "border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                  : "border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]",
              )}
              onClick={() => setShowAllEvents((value) => !value)}
              type="button"
            >
              {showAllEvents ? "只看需关注" : "显示全部事件"}
            </button>
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

        <div className="mt-3">
          <input
            className="w-full rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-2 text-sm text-zinc-200 outline-none transition placeholder:text-zinc-600 focus:border-[#3370FF]"
            placeholder="搜索任务、路径、错误码或问题类型"
            value={eventSearch}
            onChange={(event) => setEventSearch(event.target.value)}
          />
        </div>

        {eventWarning ? (
          <p className="mt-3 rounded-lg border border-amber-500/25 bg-zinc-950/35 px-3 py-2 text-xs leading-5 text-amber-300">
            {eventWarning}
          </p>
        ) : null}
        {eventError ? <p className="mt-3 text-sm text-rose-400">事件加载失败：{eventError}</p> : null}

        <div className="mt-4 grid min-h-[560px] gap-4 xl:grid-cols-[minmax(320px,0.82fr)_minmax(0,1.18fr)]">
          <aside className="flex min-h-0 flex-col rounded-xl border border-zinc-800 bg-zinc-950/35 p-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-zinc-100">{eventViewMode === "issue" ? "问题队列" : "任务队列"}</p>
                <p className="mt-1 text-[11px] text-zinc-500">
                  {eventViewMode === "issue" ? `${issueGroups.length} 类问题` : `${taskGroups.length} 个任务`}
                </p>
              </div>
              <StatusPill label={`${filteredEntries.length} 条`} tone={filteredEntries.length > 0 ? "info" : "neutral"} />
            </div>

            <div className="mt-3 min-h-0 flex-1 space-y-2 overflow-y-auto pr-1 log-scroll-area">
              {eventLoading && filteredEntries.length === 0 ? (
                [1, 2, 3, 4].map((item) => <div key={item} className="h-24 animate-pulse rounded-lg bg-zinc-800/50" />)
              ) : eventViewMode === "issue" ? (
                issueGroups.length === 0 ? (
                  <div className="rounded-lg border border-zinc-800 bg-zinc-950/40 py-10 text-center">
                    <IconActivity className="mx-auto h-9 w-9 text-zinc-700" />
                    <p className="mt-3 text-sm text-zinc-500">暂无需要关注的事件。</p>
                  </div>
                ) : (
                  issueGroups.map((group) => (
                    <EventIssueListItem
                      key={group.key}
                      group={group}
                      selected={activeIssueGroup?.key === group.key}
                      onSelect={() => setSelectedIssueKey(group.key)}
                    />
                  ))
                )
              ) : taskGroups.length === 0 ? (
                <div className="rounded-lg border border-zinc-800 bg-zinc-950/40 py-10 text-center">
                  <IconActivity className="mx-auto h-9 w-9 text-zinc-700" />
                  <p className="mt-3 text-sm text-zinc-500">暂无匹配任务事件。</p>
                </div>
              ) : (
                taskGroups.map((group) => (
                  <TaskEventListItem
                    key={group.key}
                    group={group}
                    selected={activeTaskGroup?.key === group.key}
                    onSelect={() => setSelectedTaskKey(group.key)}
                  />
                ))
              )}
            </div>
          </aside>

          <section className="flex min-h-0 flex-col rounded-xl border border-zinc-800 bg-zinc-950/40 p-4">
            {eventViewMode === "issue" && activeIssueGroup ? (
              <IssueDetail group={activeIssueGroup} />
            ) : null}
            {eventViewMode === "task" && activeTaskGroup ? (
              <TaskDetail group={activeTaskGroup} />
            ) : null}
            {!activeIssueGroup && !activeTaskGroup ? (
              <div className="flex flex-1 items-center justify-center text-center">
                <div>
                  <IconActivity className="mx-auto h-10 w-10 text-zinc-700" />
                  <p className="mt-3 text-sm text-zinc-500">请选择左侧事件查看详情。</p>
                </div>
              </div>
            ) : null}

            {activeIssueGroup || activeTaskGroup ? (
              <div className="mt-5 min-h-0 flex-1 overflow-y-auto border-t border-zinc-800 pt-4 pr-1 log-scroll-area">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-zinc-100">原始事件</p>
                  <span className="text-xs text-zinc-500">
                    {activeEntries.length > 0 ? `最近 ${Math.min(activeEntries.length, 20)} / ${activeEntries.length} 条` : "暂无原始日志"}
                  </span>
                </div>
                {activeEntries.length === 0 ? (
                  <div className="rounded-lg border border-zinc-800 bg-zinc-950/40 py-8 text-center text-xs text-zinc-500">
                    当前问题没有对应同步日志，可能来自未解决冲突队列。
                  </div>
                ) : (
                  <div className="space-y-2">
                    {activeEntries.slice(0, 20).map((entry, index) => renderEventRow(entry, `${entry.taskId}-${entry.timestamp}-${index}`))}
                  </div>
                )}
              </div>
            ) : null}
          </section>
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
                        className="rounded-lg border border-[#3370FF]/50 bg-[#3370FF]/10 px-4 py-2 text-xs font-semibold text-[#3370FF] transition hover:bg-[#3370FF]/15 disabled:opacity-50"
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
