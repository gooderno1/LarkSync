import { useEffect, useMemo, useState } from "react";

import { StatusPill } from "../components/StatusPill";
import { ActivityIssuesShowcasePage } from "../components/showcase/RemainingPagesShowcase";
import { useToast } from "../components/ui/toast";
import { useLogCenterTaskDiagnostics } from "../hooks/useLogCenterTaskDiagnostics";
import { useRemainingPagesShowcase } from "../lib/remainingPagesShowcase";
import { useWindowLayoutMode } from "../hooks/useWindowLayoutMode";
import { EVENT_FILTERS, type EventFilter } from "../lib/eventFilters";
import { classifyEventProblem, eventStatusDisplay } from "../lib/eventManagement";
import { formatTimestamp } from "../lib/formatters";
import { compactRunId, formatDuration, shortPath } from "../lib/logCenter";
import { stateLabels, stateTones } from "../lib/constants";
import { cn } from "../lib/utils";
import type { SyncLogEntry, SyncTaskOverview, SyncTaskRunSummary } from "../types";
import type { WindowLayoutMode } from "../lib/windowLayout";
import { parseActivityLink } from "../lib/activityNavigation";
import { getRunActivityTimestamp } from "../lib/taskDiagnosticsSelection";

type Props = { layoutMode?: WindowLayoutMode };

const EVENT_TYPE_LABELS: Record<string, string> = {
  uploaded: "上传",
  downloaded: "下载",
  deleted: "删除",
  delete_pending: "待删除",
  delete_failed: "删除失败",
  skipped: "跳过",
  conflict: "冲突",
  failed: "失败",
  cancelled: "中断",
  queued: "排队",
  started: "开始",
  completed: "完成",
  mirrored: "镜像",
};

function eventKey(entry: SyncLogEntry): string {
  return entry.eventId || [entry.taskId, entry.runId || "", entry.timestamp, entry.status, entry.path].join("::");
}

function TaskRow({
  overview,
  selected,
  onSelect,
}: {
  overview: SyncTaskOverview;
  selected: boolean;
  onSelect: () => void;
}) {
  const state = overview.status.state;
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "w-full rounded-lg border px-3 py-2.5 text-left transition",
        selected
          ? "border-[#3370ff]/45 bg-[#eef5ff]"
          : "border-transparent bg-white hover:border-[#c9d8ec] hover:bg-[#f6faff]",
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-sm font-semibold text-[#102033]">
          {overview.task.name || "未命名任务"}
        </span>
        <StatusPill
          label={overview.task.enabled ? stateLabels[state] || state : "已停用"}
          tone={overview.task.enabled ? stateTones[state] || "neutral" : "neutral"}
          dot={state === "running"}
        />
      </div>
      <p className="mt-1 truncate text-xs text-[#52657a]" title={overview.task.local_path}>
        {shortPath(overview.task.local_path, 34)}
      </p>
    </button>
  );
}

function RunRow({
  run,
  selected,
  onSelect,
}: {
  run: SyncTaskRunSummary;
  selected: boolean;
  onSelect: () => void;
}) {
  const deletionParts = [
    run.counts.deleted > 0 ? `删 ${run.counts.deleted}` : null,
    run.counts.delete_pending > 0 ? `待删 ${run.counts.delete_pending}` : null,
    run.counts.delete_failed > 0 ? `删失败 ${run.counts.delete_failed}` : null,
  ].filter(Boolean);
  const summary = [
    `上 ${run.counts.uploaded}`,
    `下 ${run.counts.downloaded}`,
    ...deletionParts,
    `异常 ${run.problem_count}`,
  ].join(" · ");
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "w-full rounded-lg border px-3 py-2.5 text-left transition",
        selected
          ? "border-[#3370ff]/45 bg-[#eef5ff]"
          : "border-[#d7e4f5] bg-white hover:border-[#b8c9df] hover:bg-[#f6faff]",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-mono text-sm font-semibold text-[#102033]">
            {compactRunId(run.run_id)}
          </p>
          <p className="mt-1 text-xs text-[#52657a]">{formatTimestamp(run.started_at)}</p>
        </div>
        <StatusPill label={stateLabels[run.state] || run.state} tone={stateTones[run.state] || "neutral"} />
      </div>
      <div className="mt-2 flex items-center justify-between gap-2 text-xs text-[#52657a]">
        <span>{summary}</span>
        <span>{formatDuration(run.started_at, run.finished_at, run.last_event_at)}</span>
      </div>
    </button>
  );
}

function EventList({
  items,
  selected,
  compact,
  onSelect,
}: {
  items: SyncLogEntry[];
  selected: SyncLogEntry | null;
  compact: boolean;
  onSelect: (entry: SyncLogEntry) => void;
}) {
  if (items.length === 0) {
    return (
      <div className="grid h-full min-h-40 place-items-center rounded-lg border border-dashed border-[#c9d8ec] text-sm text-[#52657a]">
        当前运行没有匹配事件。
      </div>
    );
  }
  if (compact) {
    return (
      <div className="divide-y divide-[#d7e4f5] overflow-hidden rounded-lg border border-[#d7e4f5] bg-white">
        {items.map((entry) => {
          const problem = classifyEventProblem(entry);
          return (
            <button
              key={eventKey(entry)}
              type="button"
              onClick={() => onSelect(entry)}
              className={cn(
                "block min-h-[68px] w-full px-4 py-2.5 text-left hover:bg-[#f6faff]",
                selected && eventKey(selected) === eventKey(entry) ? "bg-[#eef5ff]" : "bg-white",
              )}
            >
              <div className="flex items-center gap-3 text-base leading-6">
                <span className="shrink-0 text-sm text-[#52657a]">{formatTimestamp(entry.timestamp).split(" ").pop()}</span>
                <span className="shrink-0 font-semibold text-[#3370ff]">{EVENT_TYPE_LABELS[entry.status] || entry.status}</span>
                <span className="min-w-0 flex-1 truncate font-semibold text-[#102033]" title={entry.path}>{shortPath(entry.path, 74)}</span>
                <StatusPill label={eventStatusDisplay(entry)} tone={problem.tone} />
              </div>
              <p className="mt-1 truncate pl-[122px] text-sm leading-5 text-[#52657a]">
                {entry.message || `运行 ${compactRunId(entry.runId)}`}
              </p>
            </button>
          );
        })}
      </div>
    );
  }
  return (
    <div className="min-w-0 overflow-hidden rounded-lg border border-[#d7e4f5] bg-white">
      <div className="grid grid-cols-[112px_72px_minmax(220px,1fr)_104px_80px] border-b border-[#d7e4f5] bg-[#f6faff] px-3 py-2 text-xs font-semibold text-[#52657a]">
        <span>时间</span><span>类型</span><span>对象</span><span>阶段</span><span>结果</span>
      </div>
      <div className="divide-y divide-[#edf3fb]">
        {items.map((entry) => {
          const problem = classifyEventProblem(entry);
          return (
            <button
              key={eventKey(entry)}
              type="button"
              onClick={() => onSelect(entry)}
              className={cn(
                "grid min-h-11 w-full grid-cols-[112px_72px_minmax(220px,1fr)_104px_80px] items-center px-3 text-left text-xs hover:bg-[#f6faff]",
                selected && eventKey(selected) === eventKey(entry) ? "bg-[#eef5ff]" : "bg-white",
                problem.tone === "danger" ? "border-l-[3px] border-l-[#f43f5e]" : "border-l-[3px] border-l-transparent",
              )}
            >
              <span className="text-[#52657a]">{formatTimestamp(entry.timestamp).split(" ").pop()}</span>
              <span className="font-semibold text-[#3370ff]">{EVENT_TYPE_LABELS[entry.status] || entry.status}</span>
              <span className="truncate pr-3 font-mono text-[#102033]" title={entry.path}>{shortPath(entry.path, 90)}</span>
              <span className="truncate text-[#52657a]">{entry.message ? "同步处理" : "记录"}</span>
              <StatusPill label={eventStatusDisplay(entry)} tone={problem.tone} />
            </button>
          );
        })}
      </div>
    </div>
  );
}

function EventDetail({
  event,
  compact,
  onBack,
}: {
  event: SyncLogEntry;
  compact: boolean;
  onBack: () => void;
}) {
  const { toast } = useToast();
  const problem = classifyEventProblem(event);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText([
        event.taskName,
        event.path,
        event.status,
        event.message || "",
      ].join("\n"));
      toast("事件详情已复制", "success");
    } catch {
      toast("复制失败", "danger");
    }
  };
  const goToProblems = () => {
    const nextHash = `#conflicts?task_id=${encodeURIComponent(event.taskId)}&run_id=${encodeURIComponent(event.runId || "")}&event_id=${encodeURIComponent(event.eventId || "")}`;
    window.history.pushState(
      {
        larksyncActivity: {
          taskId: event.taskId,
          runId: event.runId || null,
          eventId: event.eventId || null,
        },
      },
      "",
      nextHash,
    );
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  };
  return (
    <section
      data-activity-event-detail="true"
      className={cn(
        "flex min-h-0 flex-col bg-white",
        compact
          ? "h-full w-full"
          : "absolute inset-y-0 right-0 z-20 w-[400px] border-l border-[#c9d8ec] shadow-[-18px_0_36px_rgba(32,67,112,0.12)]",
      )}
    >
      <header className="border-b border-[#d7e4f5] px-5 py-4">
        <button type="button" onClick={onBack} className="text-xs font-semibold text-[#3370ff] hover:underline">
          ← 返回事件列表
        </button>
        <div className="mt-3 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-[#102033]">{problem.title}</h2>
            <p className="mt-1 break-words text-sm text-[#52657a]">{event.path}</p>
          </div>
          <StatusPill label={eventStatusDisplay(event)} tone={problem.tone} />
        </div>
      </header>
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4">
        <div className="grid grid-cols-2 gap-3 rounded-lg border border-[#d7e4f5] bg-[#f6faff] p-3 text-xs">
          <div><p className="text-[#6b7f96]">任务</p><p className="mt-1 font-semibold text-[#102033]">{event.taskName}</p></div>
          <div><p className="text-[#6b7f96]">运行</p><p className="mt-1 font-mono text-[#102033]">{compactRunId(event.runId)}</p></div>
          <div><p className="text-[#6b7f96]">时间</p><p className="mt-1 text-[#102033]">{formatTimestamp(event.timestamp)}</p></div>
          <div><p className="text-[#6b7f96]">分类</p><p className="mt-1 text-[#102033]">{problem.shortLabel}</p></div>
        </div>
        <div><h3 className="text-sm font-semibold text-[#102033]">原始证据</h3><pre className="mt-2 whitespace-pre-wrap break-words rounded-lg border border-[#fecdd3] bg-[#fff7f8] p-3 font-mono text-xs leading-5 text-[#334762]">{event.message || "未记录额外错误文本。"}</pre></div>
        <div><h3 className="text-sm font-semibold text-[#102033]">原因</h3><p className="mt-2 text-sm leading-6 text-[#52657a]">{problem.cause}</p></div>
        <div><h3 className="text-sm font-semibold text-[#102033]">建议</h3><p className="mt-2 text-sm leading-6 text-[#52657a]">{problem.recommendedAction}</p></div>
      </div>
      <footer className="grid grid-cols-2 gap-2 border-t border-[#d7e4f5] p-4">
        <button type="button" onClick={copy} className="rounded-lg border border-[#c9d8ec] px-3 py-2 text-sm font-semibold text-[#3370ff] hover:bg-[#eef5ff]">复制详情</button>
        <button type="button" onClick={goToProblems} className="rounded-lg bg-[#3370ff] px-3 py-2 text-sm font-semibold text-white hover:bg-[#1d4ed8]">前往问题中心</button>
      </footer>
    </section>
  );
}

function ActivityManagementLivePage({ layoutMode }: Props) {
  const viewport = useWindowLayoutMode();
  const mode = layoutMode || viewport.mode;
  const compact = mode === "compact";
  const wide = mode === "wide";
  const initialLink = useMemo(
    () => parseActivityLink(typeof window === "undefined" ? "" : window.location.hash),
    [],
  );
  const [timeRange, setTimeRange] = useState<"24h" | "7d" | "30d" | "all">("all");
  const {
    selectedTaskId,
    setSelectedRunId,
    sortedOverviews,
    activeOverview,
    selectTask,
    selectedStatus,
    recentRuns,
    activeRunId,
    selectedRun,
    diagnosticCounts,
    refreshDiagnostics,
    setDetailTab,
    setShowAllTasks,
    eventFilter,
    setEventFilter,
    eventSearch,
    setEventSearch,
    eventPage,
    setEventPage,
    eventPageSize,
    setEventPageSize,
    setEventTimeRange,
    selectedTimelineEntries,
    selectedTimelineTotal,
    selectedEventsQuery,
    overviewQuery,
    diagnosticsQuery,
  } = useLogCenterTaskDiagnostics(true);
  const [selectedEvent, setSelectedEvent] = useState<SyncLogEntry | null>(null);
  const [taskSearch, setTaskSearch] = useState("");

  useEffect(() => {
    setShowAllTasks(true);
    setDetailTab("events");
  }, [setDetailTab, setShowAllTasks]);
  useEffect(() => setSelectedEvent(null), [selectedTaskId, activeRunId]);
  useEffect(() => {
    if (initialLink.taskId && sortedOverviews.some((item) => item.task.id === initialLink.taskId)) {
      selectTask(initialLink.taskId);
    }
  }, [initialLink.taskId, selectTask, sortedOverviews]);
  useEffect(() => {
    if (
      initialLink.runId
      && selectedTaskId === initialLink.taskId
      && recentRuns.some((run) => run.run_id === initialLink.runId)
    ) {
      setSelectedRunId(initialLink.runId);
    }
  }, [initialLink.runId, initialLink.taskId, recentRuns, selectedTaskId, setSelectedRunId]);
  useEffect(() => {
    if (!initialLink.eventId) return;
    const target = selectedTimelineEntries.find((entry) => entry.eventId === initialLink.eventId);
    if (target) setSelectedEvent(target);
  }, [initialLink.eventId, selectedTimelineEntries]);

  const rangeSince = useMemo(() => {
    const seconds = timeRange === "24h" ? 86400 : timeRange === "7d" ? 7 * 86400 : timeRange === "30d" ? 30 * 86400 : 0;
    return seconds ? Math.floor(Date.now() / 1000) - seconds : null;
  }, [timeRange]);
  useEffect(() => setEventTimeRange(rangeSince), [rangeSince, setEventTimeRange]);

  const taskItems = useMemo(() => {
    const query = taskSearch.trim().toLowerCase();
    if (!query) return sortedOverviews;
    return sortedOverviews.filter((item) =>
      `${item.task.name || ""} ${item.task.local_path}`.toLowerCase().includes(query),
    );
  }, [sortedOverviews, taskSearch]);
  const visibleRuns = useMemo(
    () => recentRuns.filter((run) => rangeSince == null || getRunActivityTimestamp(run) >= rangeSince),
    [rangeSince, recentRuns],
  );
  const successfulRuns = visibleRuns.filter((run) => run.state === "success").length;
  const failedRuns = visibleRuns.filter((run) => run.state === "failed").length;
  const maxPage = Math.max(1, Math.ceil(selectedTimelineTotal / eventPageSize));

  const taskSelector = (
    <select
      aria-label="选择活动任务"
      value={selectedTaskId || ""}
      onChange={(event) => selectTask(event.target.value)}
      className="h-10 min-w-0 rounded-lg border border-[#c9d8ec] bg-white px-3 text-sm font-semibold text-[#102033] outline-none focus:border-[#3370ff]"
    >
      {sortedOverviews.map((overview) => <option key={overview.task.id} value={overview.task.id}>{overview.task.name || "未命名任务"}</option>)}
    </select>
  );
  const runSelector = (
    <select
      aria-label="选择活动运行"
      value={activeRunId || ""}
      onChange={(event) => setSelectedRunId(event.target.value || null)}
      className="h-10 min-w-0 rounded-lg border border-[#c9d8ec] bg-white px-3 text-sm text-[#102033] outline-none focus:border-[#3370ff]"
    >
      {visibleRuns.length === 0 ? <option value="">暂无真实活动运行</option> : null}
      {visibleRuns.map((run) => <option key={run.run_id} value={run.run_id}>{compactRunId(run.run_id)} · {stateLabels[run.state] || run.state}</option>)}
    </select>
  );

  if (compact && selectedEvent) {
    return <EventDetail event={selectedEvent} compact onBack={() => setSelectedEvent(null)} />;
  }

  return (
    <section data-activity-management="true" data-window-layout={mode} className="flex h-full min-h-0 min-w-0 flex-col gap-3 animate-fade-up">
      <header className="flex min-w-0 items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-[#102033]">活动管理</h1>
          <p className="mt-1 text-sm text-[#52657a]">按任务、运行与事件审计同步活动。</p>
        </div>
        <div className="flex items-center gap-2">
          <select aria-label="活动时间范围" value={timeRange} onChange={(event) => setTimeRange(event.target.value as typeof timeRange)} className="h-9 rounded-lg border border-[#c9d8ec] bg-white px-3 text-xs text-[#102033]"><option value="24h">最近 24 小时</option><option value="7d">最近 7 天</option><option value="30d">最近 30 天</option><option value="all">全部保留记录</option></select>
          <button type="button" onClick={refreshDiagnostics} className="h-9 rounded-lg border border-[#c9d8ec] bg-white px-4 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]">刷新</button>
        </div>
      </header>

      <div className="grid grid-cols-4 overflow-hidden rounded-lg border border-[#d7e4f5] bg-white text-xs">
        <div className="px-4 py-2"><span className="text-[#52657a]">任务</span><strong className="ml-2 text-[#102033]">{sortedOverviews.length}</strong></div>
        <div className="border-l border-[#edf3fb] px-4 py-2"><span className="text-[#52657a]">运行中</span><strong className="ml-2 text-[#3370ff]">{selectedStatus?.state === "running" ? 1 : 0}</strong></div>
        <div className="border-l border-[#edf3fb] px-4 py-2"><span className="text-[#52657a]">{compact ? "异常" : "成功 / 失败"}</span><strong className="ml-2 text-[#102033]">{compact ? failedRuns : `${successfulRuns} / ${failedRuns}`}</strong></div>
        <div className="border-l border-[#edf3fb] px-4 py-2"><span className="text-[#52657a]">事件</span><strong className="ml-2 text-[#102033]">{selectedTimelineTotal}</strong></div>
      </div>

      {activeOverview?.check_state ? (
        <div className={cn(
          "flex items-center justify-between gap-3 rounded-lg border px-4 py-2 text-xs",
          activeOverview.check_state.state === "failed"
            ? "border-[#f2b8b8] bg-[#fff5f5] text-[#9f2525]"
            : "border-[#d7e4f5] bg-[#f8fbff] text-[#52657a]",
        )}>
          <span>
            最近检查：{activeOverview.check_state.finished_at ? formatTimestamp(activeOverview.check_state.finished_at) : "进行中"}
            {activeOverview.check_state.state === "no_change" ? " · 正常，没有发现变化" : null}
            {activeOverview.check_state.state === "changes_found" ? ` · 发现 ${activeOverview.check_state.change_count} 项变化` : null}
            {activeOverview.check_state.state === "checking" ? " · 正在检测" : null}
            {activeOverview.check_state.state === "failed" ? ` · ${activeOverview.check_state.last_error || "检测失败"}` : null}
          </span>
          {activeOverview.check_state.consecutive_no_change > 0 ? (
            <span className="shrink-0">连续 {activeOverview.check_state.consecutive_no_change} 次无变化</span>
          ) : null}
        </div>
      ) : null}

      {overviewQuery.error || diagnosticsQuery.error ? (
        <div className="flex items-center justify-between gap-3 rounded-lg border border-[#fecdd3] bg-[#fff7f8] px-4 py-3 text-xs text-[#be123c]">
          <span>活动数据读取失败：{(overviewQuery.error || diagnosticsQuery.error)?.message || "本地服务暂时不可用"}</span>
          <button type="button" onClick={refreshDiagnostics} className="shrink-0 rounded-lg border border-[#fda4af] bg-white px-3 py-1.5 font-semibold">重试</button>
        </div>
      ) : null}

      {compact ? (
        <div className="grid grid-cols-2 gap-2">{taskSelector}{runSelector}</div>
      ) : null}

      <div className={cn(
        "grid min-h-0 flex-1 gap-4",
        wide ? "grid-cols-[248px_288px_minmax(640px,1fr)]" : compact ? "grid-cols-1" : "grid-cols-[248px_minmax(720px,1fr)]",
      )}>
        {!compact ? (
          <aside className="flex min-h-0 flex-col rounded-xl border border-[#d7e4f5] bg-[#fbfdff] p-3">
            <div className="flex items-center justify-between"><h2 className="text-sm font-semibold text-[#102033]">任务列表</h2><span className="text-xs text-[#52657a]">{taskItems.length} / {sortedOverviews.length}</span></div>
            <input value={taskSearch} onChange={(event) => setTaskSearch(event.target.value)} placeholder="搜索任务" className="mt-3 h-9 rounded-lg border border-[#c9d8ec] bg-white px-3 text-xs outline-none focus:border-[#3370ff]" />
            <div className="mt-3 min-h-0 flex-1 space-y-1 overflow-y-auto">
              {overviewQuery.isLoading ? <div className="h-full min-h-48 animate-pulse rounded-lg bg-[#eef5ff]" /> : null}
              {!overviewQuery.isLoading && !overviewQuery.error && taskItems.length === 0 ? <p className="rounded-lg border border-dashed border-[#c9d8ec] p-6 text-center text-sm text-[#52657a]">暂无同步任务。</p> : null}
              {taskItems.map((overview) => <TaskRow key={overview.task.id} overview={overview} selected={overview.task.id === selectedTaskId} onSelect={() => selectTask(overview.task.id)} />)}
            </div>
          </aside>
        ) : null}

        {wide ? (
          <aside className="flex min-h-0 flex-col rounded-xl border border-[#d7e4f5] bg-[#fbfdff] p-3">
            <div className="flex items-center justify-between"><h2 className="text-sm font-semibold text-[#102033]">运行列表</h2><span className="text-xs text-[#52657a]">{visibleRuns.length} 条</span></div>
            <div className="mt-3 min-h-0 flex-1 space-y-2 overflow-y-auto">
              {visibleRuns.map((run) => <RunRow key={run.run_id} run={run} selected={activeRunId === run.run_id} onSelect={() => setSelectedRunId(run.run_id)} />)}
              {visibleRuns.length === 0 ? <p className="rounded-lg border border-dashed border-[#c9d8ec] p-6 text-center text-sm text-[#52657a]">所选时间内暂无运行。</p> : null}
            </div>
          </aside>
        ) : null}

        <main className="relative flex min-h-0 min-w-0 flex-col overflow-hidden rounded-xl border border-[#d7e4f5] bg-white">
          {!wide && !compact ? <div className="flex items-center gap-3 border-b border-[#d7e4f5] bg-[#fbfdff] p-3"><span className="shrink-0 text-xs font-semibold text-[#52657a]">当前运行</span><div className="min-w-0 flex-1">{runSelector}</div><span className="shrink-0 text-[11px] text-[#7e91a8]">仅显示有实际动作的运行</span></div> : null}
          <div className="flex flex-wrap items-center gap-2 border-b border-[#d7e4f5] px-3 py-2.5">
            <select value={eventFilter} onChange={(event) => { setEventFilter(event.target.value as EventFilter); setEventPage(1); }} className="h-9 rounded-lg border border-[#c9d8ec] bg-white px-3 text-xs text-[#102033]">
              {EVENT_FILTERS.map((filter) => <option key={filter.value} value={filter.value}>{filter.label}</option>)}
            </select>
            <input value={eventSearch} onChange={(event) => { setEventSearch(event.target.value); setEventPage(1); }} placeholder="搜索对象或错误" className="h-9 min-w-[180px] flex-1 rounded-lg border border-[#c9d8ec] bg-white px-3 text-xs outline-none focus:border-[#3370ff]" />
            <span className="text-xs text-[#52657a]">当前运行 {compactRunId(selectedRun?.run_id || activeRunId)} · 共 {selectedTimelineTotal} 条</span>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto p-3">
            {selectedEventsQuery.isFetching && selectedTimelineEntries.length === 0 ? <div className="h-full animate-pulse rounded-lg bg-[#eef5ff]" /> : selectedEventsQuery.error ? <div className="grid h-full min-h-48 place-items-center rounded-lg border border-[#fecdd3] bg-[#fff7f8] px-6 text-center text-sm text-[#be123c]"><div><p>运行事件读取失败：{selectedEventsQuery.error.message}</p><button type="button" onClick={() => selectedEventsQuery.refetch()} className="mt-3 rounded-lg border border-[#fda4af] bg-white px-4 py-2 text-xs font-semibold">重新读取</button></div></div> : <EventList items={selectedTimelineEntries} selected={selectedEvent} compact={compact} onSelect={setSelectedEvent} />}
          </div>
          <footer className="flex min-h-10 items-center justify-between border-t border-[#d7e4f5] px-3 py-2 text-xs text-[#52657a]">
            <span>上传 {diagnosticCounts?.uploaded ?? 0} · 下载 {diagnosticCounts?.downloaded ?? 0} · 删除 {diagnosticCounts?.deleted ?? 0}</span>
            {compact ? (
              <button type="button" disabled={eventPageSize >= selectedTimelineTotal} onClick={() => { setEventPage(1); setEventPageSize(Math.min(200, eventPageSize + 30)); }} className="rounded-lg border border-[#c9d8ec] px-3 py-1.5 font-semibold text-[#3370ff] disabled:opacity-40">加载更多</button>
            ) : (
              <div className="flex items-center gap-2"><button type="button" disabled={eventPage <= 1} onClick={() => setEventPage(Math.max(1, eventPage - 1))} className="rounded border border-[#c9d8ec] px-2 py-1 disabled:opacity-40">上一页</button><span>{eventPage} / {maxPage}</span><button type="button" disabled={eventPage >= maxPage} onClick={() => setEventPage(Math.min(maxPage, eventPage + 1))} className="rounded border border-[#c9d8ec] px-2 py-1 disabled:opacity-40">下一页</button></div>
            )}
          </footer>
          {!compact && selectedEvent ? <EventDetail event={selectedEvent} compact={false} onBack={() => setSelectedEvent(null)} /> : null}
        </main>
      </div>
    </section>
  );
}

export function ActivityIssuesPage(props: Props) {
  return useRemainingPagesShowcase() ? <ActivityIssuesShowcasePage /> : <ActivityManagementLivePage {...props} />;
}
