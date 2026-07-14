import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLogCenterTaskDiagnostics } from "../hooks/useLogCenterTaskDiagnostics";
import { useTasks } from "../hooks/useTasks";
import { apiFetch } from "../lib/api";
import {
  buildEventIssueGroups,
  classifyEventProblem,
  eventStatusDisplay,
} from "../lib/eventManagement";
import { formatTimestamp } from "../lib/formatters";
import {
  compactRunId,
  formatDuration,
  mapSyncLogResponse,
  shortPath,
  type SyncLogResponse,
  type SyncLogResponseRaw,
} from "../lib/logCenter";
import { stateLabels, stateTones } from "../lib/constants";
import { StatusPill } from "../components/StatusPill";
import { useToast } from "../components/ui/toast";
import {
  IconActivity,
  IconCopy,
  IconPlay,
  IconRefresh,
  IconSearch,
} from "../components/Icons";
import { cn } from "../lib/utils";
import type { SyncLogEntry, SyncTaskRunSummary, Tone } from "../types";
import { ActivityIssuesShowcasePage } from "../components/showcase/RemainingPagesShowcase";
import { useRemainingPagesShowcase } from "../lib/remainingPagesShowcase";

const ISSUE_STATUSES = ["delete_pending", "delete_failed", "failed", "conflict", "cancelled"];
const EMPTY_TIMELINE_ENTRIES: SyncLogEntry[] = [];

function LightPanel({
  title,
  hint,
  children,
  action,
  className,
}: {
  title: string;
  hint?: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("min-w-0 rounded-lg border border-[#d7e4f5] bg-white p-4 shadow-[0_10px_28px_rgba(51,112,255,0.05)]", className)}>
      <div className="mb-4 flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-[#102033]">{title}</h2>
          {hint ? <p className="mt-1 text-xs leading-5 text-[#6b7f96]">{hint}</p> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
      {children}
    </section>
  );
}

function metricToneClass(tone: Tone): string {
  if (tone === "danger") return "border-[#f43f5e]/25 bg-[#fff7f8] text-[#be123c]";
  if (tone === "warning") return "border-[#f59e0b]/30 bg-[#fffbeb] text-[#b45309]";
  if (tone === "success") return "border-[#10b981]/25 bg-[#ecfdf5] text-[#047857]";
  if (tone === "info") return "border-[#3370ff]/25 bg-[#eef5ff] text-[#1d4ed8]";
  return "border-[#d7e4f5] bg-white text-[#52657a]";
}

function RunItem({
  run,
  active,
  onSelect,
}: {
  run: SyncTaskRunSummary;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      className={cn(
        "w-full rounded-lg border px-3 py-3 text-left transition",
        active
          ? "border-[#3370ff]/40 bg-[#eef5ff]"
          : "border-[#d7e4f5] bg-white hover:border-[#b8c9df] hover:bg-[#f6faff]"
      )}
      onClick={onSelect}
      type="button"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-mono text-sm font-semibold text-[#102033]">{compactRunId(run.run_id)}</p>
          <p className="mt-1 text-xs text-[#6b7f96]">{formatTimestamp(run.started_at)}</p>
        </div>
        <StatusPill label={stateLabels[run.state] || run.state} tone={stateTones[run.state] || "neutral"} dot={run.state === "running"} />
      </div>
      <p className="mt-2 text-xs text-[#6b7f96]">
        上 {run.counts.uploaded} / 下 {run.counts.downloaded} / 失败 {run.counts.failed} / 冲突 {run.counts.conflicts}
      </p>
      <p className="mt-1 text-xs text-[#6b7f96]">耗时 {formatDuration(run.started_at, run.finished_at, run.last_event_at)}</p>
    </button>
  );
}

function ActivityIssuesLivePage() {
  const { runTask } = useTasks();
  const { toast } = useToast();
  const {
    selectedTaskId,
    setSelectedRunId,
    taskPickerOptions,
    selectTask,
    selectedTask,
    selectedStatus,
    selectedStateKey,
    recentRuns,
    activeRunId,
    selectedRun,
    selectedProblems,
    diagnosticCounts,
    refreshDiagnostics,
    setDetailTab,
  } = useLogCenterTaskDiagnostics(true);
  const [selectedEventKey, setSelectedEventKey] = useState<string | null>(null);
  const [runQuery, setRunQuery] = useState("");

  useEffect(() => {
    setDetailTab("problems");
  }, [setDetailTab, selectedTaskId, activeRunId]);

  const timelineQuery = useQuery<SyncLogResponse>({
    queryKey: ["activity-issue-timeline", selectedTaskId, activeRunId],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("limit", "120");
      params.set("order", "desc");
      if (selectedTaskId) params.append("task_ids", selectedTaskId);
      if (activeRunId) params.append("run_ids", activeRunId);
      for (const status of ISSUE_STATUSES) {
        params.append("statuses", status);
      }
      return mapSyncLogResponse(await apiFetch<SyncLogResponseRaw>(`/sync/logs/sync?${params.toString()}`));
    },
    enabled: Boolean(selectedTaskId),
    staleTime: 5_000,
    refetchInterval: selectedStatus?.state === "running" ? 5_000 : 10_000,
    placeholderData: { total: 0, items: [] },
  });

  const timelineEntries = timelineQuery.data?.items ?? EMPTY_TIMELINE_ENTRIES;
  const issueSourceEntries = selectedProblems.length > 0 ? selectedProblems : timelineEntries;
  const issueGroups = useMemo(
    () => buildEventIssueGroups(issueSourceEntries, { includeInformational: false }),
    [issueSourceEntries]
  );
  const visibleRecentRuns = useMemo(
    () => recentRuns.filter((run) => run.run_id.toLowerCase().includes(runQuery.trim().toLowerCase())),
    [recentRuns, runQuery]
  );
  const selectedEvent = useMemo(() => {
    if (selectedEventKey) {
      const found = timelineEntries.find((entry, index) => `${entry.taskId}-${entry.timestamp}-${index}` === selectedEventKey);
      if (found) return found;
    }
    return timelineEntries[0] ?? selectedProblems[0] ?? null;
  }, [selectedEventKey, timelineEntries, selectedProblems]);
  const selectedProblem = selectedEvent ? classifyEventProblem(selectedEvent) : null;
  const handleRetry = () => {
    if (!selectedTask) return;
    runTask(selectedTask);
    toast("任务已重新触发", "info");
    refreshDiagnostics();
    void timelineQuery.refetch();
  };

  const handleCopyError = async () => {
    if (!selectedEvent) return;
    const text = [selectedEvent.taskName, selectedEvent.path, selectedEvent.message, selectedEvent.status].filter(Boolean).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      toast("错误信息已复制", "success");
    } catch {
      toast("复制错误信息失败", "danger");
    }
  };

  return (
    <section className="grid h-full min-h-0 min-w-0 grid-rows-[auto_minmax(0,1fr)] gap-4 animate-fade-up">
      <header className="grid min-w-0 grid-cols-[minmax(0,1fr)_440px_auto] items-end gap-5">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-[#102033]">活动与问题</h1>
          <p className="mt-1 text-sm text-[#52657A]">诊断运行问题，快速定位并解决同步异常。</p>
        </div>
        <div data-activity-context="true" data-activity-task-selector="true" className="min-w-0">
          <p className="mb-1.5 text-xs font-semibold text-[#52657a]">任务选择</p>
          <div className="grid grid-cols-[minmax(0,1fr)_118px] gap-2">
            <select
              aria-label="选择诊断任务"
              className="h-9 min-w-0 rounded-lg border border-[#bfd3ee] bg-white px-3 text-xs font-semibold text-[#102033] outline-none focus:border-[#3370ff]"
              value={selectedTaskId ?? ""}
              onChange={(event) => {
                selectTask(event.target.value);
                setSelectedEventKey(null);
              }}
            >
              {taskPickerOptions.map((overview) => <option key={overview.task.id} value={overview.task.id}>{overview.task.name || "未命名任务"}</option>)}
            </select>
            <div className="flex h-9 items-center justify-center rounded-lg border border-[#bfd3ee] bg-white">
              <StatusPill label={stateLabels[selectedStateKey] || selectedStateKey} tone={stateTones[selectedStateKey] || "neutral"} />
            </div>
          </div>
        </div>
        <button
          className="inline-flex h-9 items-center gap-2 rounded-lg border border-[#c9d8ec] bg-white px-4 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]"
          onClick={refreshDiagnostics}
          type="button"
        >
          <IconRefresh className="h-3.5 w-3.5" />
          刷新诊断
        </button>
      </header>

      <div data-diagnostic-workspace="true" className="grid min-h-0 grid-cols-[276px_minmax(0,1fr)_416px] overflow-hidden rounded-xl border border-[#d7e4f5] bg-white shadow-[0_14px_34px_rgba(51,112,255,0.06)]">
        <div className="min-h-0 min-w-0 overflow-y-auto border-r border-[#d7e4f5] bg-[#fbfdff]">
          <LightPanel title="运行历史" hint="选择一次运行查看对应事件。" className="rounded-none border-0 bg-transparent shadow-none">
            <label data-activity-run-search="true" className="relative mb-3 block">
              <IconSearch className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-[#8aa0b8]" />
              <input className="h-9 w-full rounded-lg border border-[#c9d8ec] bg-white pl-9 pr-3 text-xs text-[#102033] outline-none placeholder:text-[#8aa0b8] focus:border-[#3370ff]" placeholder="搜索运行 ID" value={runQuery} onChange={(event) => setRunQuery(event.target.value)} />
            </label>
            <div className="max-h-[420px] space-y-2 overflow-y-auto pr-1 log-scroll-area">
              {!selectedTask ? (
                <div className="rounded-xl border border-dashed border-[#c9d8ec] px-4 py-8 text-center text-sm text-[#6b7f96]">
                  请选择任务。
                </div>
              ) : recentRuns.length === 0 ? (
                <div className="rounded-xl border border-dashed border-[#c9d8ec] px-4 py-8 text-center text-sm text-[#6b7f96]">
                  暂无运行历史。
                </div>
              ) : (
                visibleRecentRuns.slice(0, 10).map((run) => (
                  <RunItem
                    key={run.run_id}
                    run={run}
                    active={activeRunId === run.run_id}
                    onSelect={() => {
                      setSelectedRunId(run.run_id);
                      setSelectedEventKey(null);
                    }}
                  />
                ))
              )}
            </div>
          </LightPanel>
        </div>

        <main className="min-h-0 min-w-0 overflow-y-auto border-r border-[#d7e4f5]">
          <LightPanel
            title="问题概览"
            hint={selectedRun ? `当前运行：${compactRunId(selectedRun.run_id)}` : "按问题类型汇总当前任务或当前运行。"}
            className="rounded-none border-0 border-b border-[#d7e4f5] shadow-none"
          >
            {issueGroups.length === 0 ? (
              <div className="rounded-xl border border-dashed border-[#c9d8ec] px-5 py-10 text-center">
                <IconActivity className="mx-auto h-10 w-10 text-[#9fb2c8]" />
                <p className="mt-3 text-sm text-[#6b7f96]">当前没有需要处理的问题。</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                {issueGroups.map((group) => (
                  <article key={group.key} className={`rounded-xl border p-4 ${metricToneClass(group.problem.tone)}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-xs font-semibold opacity-80">{group.problem.shortLabel}</p>
                        <h3 className="mt-2 text-base font-semibold text-[#102033]">{group.problem.title}</h3>
                      </div>
                      <span className="rounded-full bg-white/70 px-2 py-1 text-xs font-semibold">{group.count} 条</span>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-[#52657a]">{group.problem.summary}</p>
                    <p className="mt-3 text-xs leading-5 text-[#6b7f96]">建议：{group.problem.recommendedAction}</p>
                  </article>
                ))}
              </div>
            )}
          </LightPanel>

          <LightPanel
            title="事件时间线"
            hint="默认只展示需要关注的事件，普通成功日志保留在系统日志与任务诊断中。"
            action={timelineQuery.isFetching ? <span className="text-xs text-[#6b7f96]">刷新中...</span> : null}
            className="rounded-none border-0 shadow-none"
          >
            <div className="space-y-2">
              {timelineEntries.length === 0 ? (
                <div className="rounded-xl border border-dashed border-[#c9d8ec] px-5 py-8 text-center text-sm text-[#6b7f96]">
                  当前范围内暂无问题事件。
                </div>
              ) : (
                timelineEntries.slice(0, 12).map((entry, index) => {
                  const key = `${entry.taskId}-${entry.timestamp}-${index}`;
                  const problem = classifyEventProblem(entry);
                  return (
                    <button
                      key={key}
                      className={cn(
                        "w-full rounded-xl border px-4 py-3 text-left transition",
                        selectedEvent === entry
                          ? "border-[#3370ff]/40 bg-[#eef5ff]"
                          : "border-[#d7e4f5] bg-white hover:border-[#b8c9df] hover:bg-[#f6faff]"
                      )}
                      onClick={() => setSelectedEventKey(key)}
                      type="button"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-xs text-[#6b7f96]">{formatTimestamp(entry.timestamp)}</p>
                          <p className="mt-1 truncate text-sm font-semibold text-[#102033]">{entry.taskName || "未命名任务"}</p>
                        </div>
                        <StatusPill label={eventStatusDisplay(entry)} tone={problem.tone} />
                      </div>
                      <p className="mt-2 truncate font-mono text-xs text-[#52657a]" title={entry.path}>{shortPath(entry.path || "无路径", 90)}</p>
                      {entry.message ? <p className="mt-1 line-clamp-2 text-xs leading-5 text-[#6b7f96]">{entry.message}</p> : null}
                    </button>
                  );
                })
              )}
            </div>
          </LightPanel>
        </main>

        <aside data-activity-diagnosis="true" className="min-h-0 min-w-0 overflow-y-auto bg-[#fbfdff]">
          <LightPanel title="事件诊断" hint="查看原因、影响和推荐动作。" className="rounded-none border-0 border-b border-[#d7e4f5] bg-transparent shadow-none">
            {!selectedEvent || !selectedProblem ? (
              <div className="rounded-xl border border-dashed border-[#c9d8ec] px-4 py-10 text-center">
                <IconActivity className="mx-auto h-10 w-10 text-[#9fb2c8]" />
                <p className="mt-3 text-sm text-[#6b7f96]">请选择一条事件。</p>
              </div>
            ) : (
              <div className="space-y-4">
                <StatusPill label={selectedProblem.shortLabel} tone={selectedProblem.tone} />
                <div>
                  <h3 className="text-base font-semibold text-[#102033]">{selectedProblem.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-[#52657a]">{selectedProblem.summary}</p>
                </div>
                <div className="rounded-xl border border-[#d7e4f5] bg-[#f6faff] p-3">
                  <p className="text-xs font-semibold text-[#52657a]">原因</p>
                  <p className="mt-2 text-xs leading-5 text-[#334762]">{selectedProblem.cause}</p>
                </div>
                <div className="rounded-xl border border-[#d7e4f5] bg-[#f6faff] p-3">
                  <p className="text-xs font-semibold text-[#52657a]">建议动作</p>
                  <p className="mt-2 text-xs leading-5 text-[#334762]">{selectedProblem.recommendedAction}</p>
                </div>
                <div data-activity-error-detail="true" className="rounded-xl border border-[#fecdd3] bg-[#fff7f8] p-3">
                  <p className="text-xs font-semibold text-[#102033]">错误详情</p>
                  <p className="mt-2 text-[11px] text-[#6b7f96]">错误码：{selectedEvent.status}</p>
                  <p className="mt-2 break-words font-mono text-xs leading-5 text-[#334762]">{selectedEvent.path || "无路径"}</p>
                  {selectedEvent.message ? <p className="mt-2 break-words text-xs leading-5 text-[#52657a]">{selectedEvent.message}</p> : null}
                </div>
              </div>
            )}
          </LightPanel>

          <LightPanel title="处理操作" className="rounded-none border-0 border-b border-[#d7e4f5] bg-transparent shadow-none">
            <div className="grid grid-cols-2 gap-2">
              <button
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-[#c9d8ec] px-3 py-2 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff] disabled:opacity-50"
                disabled={!selectedTask}
                onClick={handleRetry}
                type="button"
              >
                <IconPlay className="h-3.5 w-3.5" />
                重试任务
              </button>
              <button
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-[#c9d8ec] px-3 py-2 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff] disabled:opacity-50"
                disabled={!selectedEvent}
                onClick={handleCopyError}
                type="button"
              >
                <IconCopy className="h-3.5 w-3.5" />
                复制错误
              </button>
              <button
                className="col-span-2 inline-flex items-center justify-center gap-2 rounded-lg border border-[#c9d8ec] px-3 py-2 text-xs font-semibold text-[#334762] hover:bg-[#f6faff]"
                onClick={() => {
                  refreshDiagnostics();
                  void timelineQuery.refetch();
                }}
                type="button"
              >
                <IconRefresh className="h-3.5 w-3.5" />
                刷新诊断
              </button>
            </div>
          </LightPanel>

          <LightPanel title="本次运行" className="rounded-none border-0 bg-transparent shadow-none">
            <dl className="space-y-2 text-xs">
              <div className="flex justify-between gap-3"><dt className="text-[#6b7f96]">上传</dt><dd className="font-semibold text-[#102033]">{diagnosticCounts?.uploaded ?? 0}</dd></div>
              <div className="flex justify-between gap-3"><dt className="text-[#6b7f96]">下载</dt><dd className="font-semibold text-[#102033]">{diagnosticCounts?.downloaded ?? 0}</dd></div>
              <div className="flex justify-between gap-3"><dt className="text-[#6b7f96]">删除</dt><dd className="font-semibold text-[#102033]">{diagnosticCounts?.deleted ?? 0}</dd></div>
              <div className="flex justify-between gap-3"><dt className="text-[#6b7f96]">失败</dt><dd className="font-semibold text-[#be123c]">{diagnosticCounts?.failed ?? 0}</dd></div>
              <div className="flex justify-between gap-3"><dt className="text-[#6b7f96]">冲突</dt><dd className="font-semibold text-[#b45309]">{diagnosticCounts?.conflicts ?? 0}</dd></div>
            </dl>
          </LightPanel>
        </aside>
      </div>
    </section>
  );
}

export function ActivityIssuesPage() {
  return useRemainingPagesShowcase() ? <ActivityIssuesShowcasePage /> : <ActivityIssuesLivePage />;
}
