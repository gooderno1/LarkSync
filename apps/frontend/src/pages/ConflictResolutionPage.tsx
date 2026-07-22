import { useEffect, useMemo, useState } from "react";

import { StatusPill } from "../components/StatusPill";
import { ConflictResolutionShowcasePage } from "../components/showcase/RemainingPagesShowcase";
import { confirm } from "../components/ui/confirm-dialog";
import { useToast } from "../components/ui/toast";
import { useProblems } from "../hooks/useProblems";
import { useRemainingPagesShowcase } from "../lib/remainingPagesShowcase";
import { useTasks } from "../hooks/useTasks";
import { useWindowLayoutMode } from "../hooks/useWindowLayoutMode";
import { formatTimestamp } from "../lib/formatters";
import { parseProblemLink } from "../lib/activityNavigation";
import {
  problemCategoryLabel,
  problemSeverityTone,
  problemStateLabels,
  shouldKeepProblemSelection,
} from "../lib/problemCenter";
import { cn } from "../lib/utils";
import type {
  ProblemActionRecord,
  ProblemAvailableAction,
  ProblemItem,
  ProblemOccurrence,
} from "../types";
import type { WindowLayoutMode } from "../lib/windowLayout";

type Props = { layoutMode?: WindowLayoutMode };
type StateScope = "unresolved" | "resolved" | "ignored";
type DetailTab = "diagnosis" | "evidence" | "history";
type ProblemTimeRange = "24h" | "7d" | "30d" | "all";

const CATEGORY_OPTIONS = [
  "auth_permission",
  "upload",
  "download",
  "conversion",
  "deletion",
  "conflict",
  "task_config",
  "network_remote",
  "local_io",
  "system",
];

const STATE_QUERY: Record<StateScope, string> = {
  unresolved: "open,in_progress,waiting",
  resolved: "resolved",
  ignored: "ignored",
};

function evidenceText(evidence: Record<string, unknown>): string {
  return Object.entries(evidence)
    .map(([key, value]) => `${key}: ${typeof value === "string" ? value : JSON.stringify(value)}`)
    .join("\n");
}

function ProblemQueueItem({
  problem,
  selected,
  onSelect,
}: {
  problem: ProblemItem;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "block min-h-[84px] w-full rounded-lg border px-3 py-2.5 text-left transition",
        selected
          ? "border-[#3370ff]/45 bg-[#eef5ff]"
          : "border-[#d7e4f5] bg-white hover:border-[#b8c9df] hover:bg-[#f6faff]",
      )}
    >
      <div className="flex items-start gap-2">
        <span className={cn(
          "mt-1 h-2.5 w-2.5 shrink-0 rounded-full",
          problem.severity === "critical" || problem.severity === "high" ? "bg-[#e11d48]" : problem.severity === "medium" ? "bg-[#f59e0b]" : "bg-[#3370ff]",
        )} />
        <span className="min-w-0 flex-1 truncate text-sm font-semibold text-[#102033]" title={problem.title}>{problem.title}</span>
        <span className="shrink-0 text-xs text-[#52657a]">{formatTimestamp(problem.last_seen_at)}</span>
      </div>
      <div className="mt-2 flex items-center gap-2 pl-[18px] text-xs text-[#52657a]">
        <span className="truncate">{problem.task_id || "系统"}</span>
        <span>·</span>
        <span>{problemCategoryLabel(problem.category)}</span>
        <span>·</span>
        <span>重复 {problem.occurrence_count} 次</span>
      </div>
    </button>
  );
}

function Diagnosis({
  problem,
  latest,
  onViewActivity,
}: {
  problem: ProblemItem;
  latest?: ProblemOccurrence;
  onViewActivity: () => void;
}) {
  const evidence = latest?.evidence ?? {};
  return (
    <div className="space-y-4">
      <section>
        <h3 className="text-sm font-semibold text-[#102033]">问题摘要</h3>
        <p className="mt-2 text-sm leading-6 text-[#52657a]">{problem.summary}</p>
      </section>
      <section className="rounded-lg border border-[#d7e4f5] bg-[#f6faff] p-4">
        <h3 className="text-sm font-semibold text-[#102033]">当前判断</h3>
        <p className="mt-2 text-sm leading-6 text-[#52657a]">
          后端分类为“{problemCategoryLabel(problem.category)}”，严重级别为 {problem.severity}。该结论由 {problem.classifier_version} 产生，前端不根据错误文本重新分类。
        </p>
        <p className="mt-2 text-xs text-[#52657a]">
          处理方式：{problem.actionability === "manual_required" ? "需要人工处理" : problem.actionability === "auto_recovering" ? "系统自动恢复并等待同对象成功验证" : "仅提供诊断证据"}。
        </p>
        {problem.state === "resolved" && problem.resolved_at ? (
          <p className="mt-3 rounded-md border border-[#bde5cc] bg-[#f2fbf5] px-3 py-2 text-xs leading-5 text-[#257044]">
            已于 {formatTimestamp(problem.resolved_at)} 自动确认恢复
            {problem.resolution_verification === "same_object_operation_succeeded" ? "，依据是同一对象、同一操作后续成功" : ""}。
          </p>
        ) : null}
      </section>
      <section>
        <h3 className="text-sm font-semibold text-[#102033]">对象与关联</h3>
        <dl className="mt-2 grid grid-cols-2 gap-3 text-xs">
          <div className="rounded-lg border border-[#edf3fb] p-3"><dt className="text-[#6b7f96]">对象</dt><dd className="mt-1 break-words font-mono text-[#102033]">{problem.object_path || problem.object_key}</dd></div>
          <div className="rounded-lg border border-[#edf3fb] p-3"><dt className="text-[#6b7f96]">关联运行</dt><dd className="mt-1 break-words font-mono text-[#102033]">{problem.latest_run_id || "无"}</dd></div>
        </dl>
        {problem.task_id ? <button type="button" onClick={onViewActivity} className="mt-3 text-xs font-semibold text-[#3370ff] hover:text-[#1d4ed8]">查看关联活动 →</button> : null}
      </section>
      {Object.keys(evidence).length > 0 ? (
        <section>
          <h3 className="text-sm font-semibold text-[#102033]">最近证据摘要</h3>
          <pre className="mt-2 max-h-44 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-[#d7e4f5] bg-[#fbfdff] p-3 font-mono text-xs leading-5 text-[#334762]">{evidenceText(evidence)}</pre>
        </section>
      ) : null}
    </div>
  );
}

function EvidenceList({ occurrences }: { occurrences: ProblemOccurrence[] }) {
  if (occurrences.length === 0) return <p className="rounded-lg border border-dashed border-[#c9d8ec] p-8 text-center text-sm text-[#52657a]">暂无证据记录。</p>;
  return (
    <div className="space-y-3">
      {occurrences.map((item) => (
        <article key={item.id} className="rounded-lg border border-[#d7e4f5] bg-white p-4">
          <div className="flex items-center justify-between gap-3 text-xs text-[#52657a]"><span>{item.source_kind}</span><time>{formatTimestamp(item.occurred_at)}</time></div>
          <pre className="mt-3 whitespace-pre-wrap break-words rounded-lg bg-[#f6faff] p-3 font-mono text-xs leading-5 text-[#334762]">{evidenceText(item.evidence)}</pre>
        </article>
      ))}
    </div>
  );
}

function ActionHistory({ actions }: { actions: ProblemActionRecord[] }) {
  if (actions.length === 0) return <p className="rounded-lg border border-dashed border-[#c9d8ec] p-8 text-center text-sm text-[#52657a]">尚未执行处理动作。</p>;
  return (
    <div className="space-y-3">
      {actions.map((item) => (
        <article key={item.id} className="rounded-lg border border-[#d7e4f5] bg-white p-4 text-xs">
          <div className="flex items-center justify-between gap-3"><strong className="text-[#102033]">{item.action_key}</strong><time className="text-[#52657a]">{formatTimestamp(item.requested_at)}</time></div>
          <p className="mt-2 text-[#52657a]">结果：{item.result} · 验证：{item.verification_result || "未验证"}</p>
          {item.error_message ? <p className="mt-2 rounded bg-[#fff7f8] p-2 text-[#be123c]">{item.error_message}</p> : null}
        </article>
      ))}
    </div>
  );
}

function ProblemActions({
  problem,
  pending,
  onAction,
  onVerify,
  wide,
}: {
  problem: ProblemItem;
  pending: boolean;
  onAction: (action: ProblemAvailableAction) => void;
  onVerify: () => void;
  wide: boolean;
}) {
  return (
    <div className={cn(wide ? "space-y-4" : "flex items-center justify-between gap-3")}>
      <div>
        <p className="text-xs font-semibold text-[#52657a]">当前状态</p>
        <div className="mt-2"><StatusPill label={problemStateLabels[problem.state] || problem.state} tone={problemSeverityTone(problem.severity)} /></div>
        <p className="mt-2 text-xs leading-5 text-[#52657a]">动作成功后仍需验证，页面不会因点击按钮直接标记解决。</p>
      </div>
      <div className={cn(wide ? "space-y-2" : "flex shrink-0 items-center gap-2")}>
        {problem.available_actions.map((action) => (
          <button
            key={action.key}
            type="button"
            disabled={pending}
            onClick={() => onAction(action)}
            className={cn(
              "rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50",
              action.tone === "primary" ? "bg-[#3370ff] text-white hover:bg-[#1d4ed8]" : "border border-[#c9d8ec] bg-white text-[#3370ff] hover:bg-[#eef5ff]",
              wide ? "w-full" : "",
            )}
          >
            {action.label}
          </button>
        ))}
        {problem.state === "waiting" ? <button type="button" disabled={pending} onClick={onVerify} className={cn("rounded-lg border border-[#c9d8ec] bg-white px-4 py-2 text-sm font-semibold text-[#334762] hover:bg-[#f6faff] disabled:opacity-50", wide ? "w-full" : "")}>立即验证</button> : null}
        {problem.available_actions.length === 0 && problem.state !== "waiting" ? <p className="text-xs text-[#52657a]">当前没有后端允许的处理动作。</p> : null}
      </div>
    </div>
  );
}

function ProblemCenterLivePage({ layoutMode }: Props) {
  const viewport = useWindowLayoutMode();
  const mode = layoutMode || viewport.mode;
  const compact = mode === "compact";
  const wide = mode === "wide";
  const { tasks } = useTasks();
  const initialLink = useMemo(
    () => parseProblemLink(typeof window === "undefined" ? "" : window.location.hash),
    [],
  );
  const [scope, setScope] = useState<StateScope>("unresolved");
  const [category, setCategory] = useState(initialLink.category || "");
  const [taskId, setTaskId] = useState(initialLink.taskId || "");
  const [severity, setSeverity] = useState("");
  const [timeRange, setTimeRange] = useState<ProblemTimeRange>("all");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [selectedId, setSelectedId] = useState<string | null>(initialLink.problemId);
  const [compactDetailOpen, setCompactDetailOpen] = useState(Boolean(initialLink.problemId));
  const [tab, setTab] = useState<DetailTab>("diagnosis");
  const { toast } = useToast();
  const rangeSince = useMemo(() => {
    const seconds = timeRange === "24h" ? 86400 : timeRange === "7d" ? 7 * 86400 : timeRange === "30d" ? 30 * 86400 : 0;
    return seconds ? Math.floor(Date.now() / 1000) - seconds : null;
  }, [timeRange]);
  const filters = useMemo(() => ({
    state: STATE_QUERY[scope],
    categories: category ? [category] : [],
    severities: severity ? [severity] : [],
    taskId,
    search,
    since: rangeSince,
    offset: (page - 1) * pageSize,
    limit: pageSize,
  }), [scope, category, severity, taskId, search, rangeSince, page, pageSize]);
  const {
    problems,
    total,
    summary,
    detail,
    loading,
    fetching,
    error,
    detailLoading,
    detailError,
    actionPending,
    verifyPending,
    executeAction,
    verifyProblem,
    refresh,
  } = useProblems(filters, selectedId, true);

  useEffect(() => {
    setPage(1);
    if (compact) setPageSize(50);
  }, [category, compact, scope, search, severity, taskId, timeRange]);

  useEffect(() => {
    const ids = problems.map((item) => item.id);
    if (shouldKeepProblemSelection(selectedId, ids)) return;
    if (
      selectedId === initialLink.problemId
      && (detailLoading || detail?.problem.id === initialLink.problemId)
    ) return;
    setSelectedId(ids[0] || null);
    if (compact) setCompactDetailOpen(false);
  }, [compact, detail?.problem.id, detailLoading, initialLink.problemId, problems, selectedId]);

  const selected = detail?.problem ?? problems.find((item) => item.id === selectedId) ?? null;
  const maxPage = Math.max(1, Math.ceil(total / pageSize));
  const occurrences = detail?.history.occurrences ?? [];
  const actions = detail?.history.actions ?? [];
  const handleAction = async (action: ProblemAvailableAction) => {
    if (!selected) return;
    if (action.requires_confirmation) {
      const approved = await confirm({
        title: `确认${action.label}？`,
        description: "该操作会改变本地或云端内容。处理完成后仍会执行来源状态验证。",
        confirmLabel: action.label,
        tone: action.key === "use_local" ? "warning" : "neutral",
      });
      if (!approved) return;
    }
    try {
      await executeAction({ problemId: selected.id, actionKey: action.key });
      toast("动作已提交，等待验证", "success");
    } catch (actionError) {
      toast(actionError instanceof Error ? actionError.message : "动作提交失败", "danger");
    }
  };
  const handleVerify = async () => {
    if (!selected) return;
    try {
      const result = await verifyProblem(selected.id);
      toast(result.state === "resolved" ? "问题已验证解决" : "验证未通过，问题保持未解决", result.state === "resolved" ? "success" : "info");
    } catch (verifyError) {
      toast(verifyError instanceof Error ? verifyError.message : "验证失败", "danger");
    }
  };
  const viewRelatedActivity = () => {
    if (!selected?.task_id || typeof window === "undefined") return;
    const params = new URLSearchParams({ task_id: selected.task_id });
    if (selected.latest_run_id) params.set("run_id", selected.latest_run_id);
    if (selected.latest_event_id) params.set("event_id", selected.latest_event_id);
    window.history.pushState(
      { ...window.history.state, larksyncProblem: { problemId: selected.id } },
      "",
      `#activity?${params.toString()}`,
    );
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  };

  const queue = (
    <aside data-problem-queue="true" className="flex min-h-0 flex-col rounded-xl border border-[#d7e4f5] bg-[#fbfdff] p-3">
      <div className="grid grid-cols-1 gap-2">
        <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索问题" className="h-9 min-w-0 rounded-lg border border-[#c9d8ec] bg-white px-3 text-xs outline-none focus:border-[#3370ff]" />
      </div>
      {error ? <p className="mt-3 rounded-lg border border-[#fecdd3] bg-[#fff7f8] p-3 text-xs text-[#be123c]">数据可能不是最新：{error}</p> : null}
      {detailError && selectedId === initialLink.problemId ? <p className="mt-3 rounded-lg border border-[#fecdd3] bg-[#fff7f8] p-3 text-xs text-[#be123c]">无法定位指定问题：{detailError}</p> : null}
      <div className="mt-3 min-h-0 flex-1 space-y-2 overflow-y-auto">
        {loading && problems.length === 0 ? [1, 2, 3, 4, 5, 6].map((item) => <div key={item} className="h-[84px] animate-pulse rounded-lg bg-[#eef5ff]" />) : null}
        {!loading && problems.length === 0 ? <div className="grid h-full min-h-56 place-items-center rounded-lg border border-dashed border-[#c9d8ec] px-5 text-center text-sm text-[#52657a]">{scope === "unresolved" ? "当前没有待处理问题。" : "当前范围没有问题记录。"}</div> : null}
        {problems.map((problem) => <ProblemQueueItem key={problem.id} problem={problem} selected={problem.id === selectedId} onSelect={() => { setSelectedId(problem.id); setTab("diagnosis"); if (compact) setCompactDetailOpen(true); }} />)}
      </div>
      <footer className="mt-3 flex items-center justify-between text-xs text-[#52657a]">
        <span>共 {total} 条</span>
        {compact ? <span className="flex items-center gap-3">{page > 1 ? <button type="button" onClick={() => setPage((value) => Math.max(1, value - 1))} className="font-semibold text-[#3370ff]">上一批</button> : null}{page === 1 && pageSize < Math.min(total, 200) ? <button type="button" onClick={() => setPageSize((value) => Math.min(200, value + 50))} className="font-semibold text-[#3370ff]">加载更多</button> : page < maxPage ? <button type="button" onClick={() => setPage((value) => Math.min(maxPage, value + 1))} className="font-semibold text-[#3370ff]">下一批</button> : null}</span> : null}
        {!compact ? <span className="flex items-center gap-2"><button type="button" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))} className="rounded border border-[#c9d8ec] px-2 py-1 font-semibold text-[#3370ff] disabled:opacity-40">上一页</button><span>{page} / {maxPage}</span><button type="button" disabled={page >= maxPage} onClick={() => setPage((value) => Math.min(maxPage, value + 1))} className="rounded border border-[#c9d8ec] px-2 py-1 font-semibold text-[#3370ff] disabled:opacity-40">下一页</button></span> : null}
      </footer>
    </aside>
  );

  const workbench = selected ? (
    <main data-problem-workbench="true" className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-xl border border-[#d7e4f5] bg-white">
      <header className="border-b border-[#d7e4f5] px-5 py-4">
        {compact ? <button type="button" onClick={() => setCompactDetailOpen(false)} className="mb-3 text-xs font-semibold text-[#3370ff]">← 返回问题列表</button> : null}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="break-words text-lg font-semibold leading-7 text-[#102033]">{selected.title}</h2>
            <p className="mt-1 break-words font-mono text-xs leading-5 text-[#52657a]">{selected.object_path || selected.object_key}</p>
          </div>
          <StatusPill label={problemStateLabels[selected.state] || selected.state} tone={problemSeverityTone(selected.severity)} />
        </div>
        <p className="mt-3 text-xs text-[#52657a]">首次 {formatTimestamp(selected.first_seen_at)} · 最近 {formatTimestamp(selected.last_seen_at)} · 重复 {selected.occurrence_count} 次</p>
      </header>
      <nav className="flex h-11 shrink-0 items-end gap-6 border-b border-[#d7e4f5] px-5">
        {(["diagnosis", "evidence", "history"] as DetailTab[]).map((item) => <button key={item} type="button" onClick={() => setTab(item)} className={cn("h-11 border-b-2 px-1 text-sm font-semibold", tab === item ? "border-[#3370ff] text-[#3370ff]" : "border-transparent text-[#52657a]")}>{item === "diagnosis" ? "诊断" : item === "evidence" ? "证据" : "处理记录"}</button>)}
      </nav>
      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        {tab === "diagnosis" ? <Diagnosis problem={selected} latest={occurrences[0]} onViewActivity={viewRelatedActivity} /> : null}
        {tab === "evidence" ? <EvidenceList occurrences={occurrences} /> : null}
        {tab === "history" ? <ActionHistory actions={actions} /> : null}
      </div>
      {!wide ? <footer className="shrink-0 border-t border-[#d7e4f5] bg-[#fbfdff] px-5 py-3"><ProblemActions problem={selected} pending={actionPending || verifyPending} onAction={handleAction} onVerify={handleVerify} wide={false} /></footer> : null}
    </main>
  ) : (
    <main className="grid min-h-0 place-items-center rounded-xl border border-dashed border-[#c9d8ec] bg-white text-sm text-[#52657a]">请选择一条问题。</main>
  );

  if (compact && compactDetailOpen && selected) return workbench;

  const advancedFilters = (
    <>
      <select aria-label="问题分类" value={category} onChange={(event) => setCategory(event.target.value)} className="h-9 min-w-[132px] rounded-lg border border-[#c9d8ec] bg-white px-2 text-xs text-[#102033]"><option value="">全部分类</option>{CATEGORY_OPTIONS.map((item) => <option key={item} value={item}>{problemCategoryLabel(item)}</option>)}</select>
      <select aria-label="严重级别" value={severity} onChange={(event) => setSeverity(event.target.value)} className="h-9 min-w-[112px] rounded-lg border border-[#c9d8ec] bg-white px-2 text-xs text-[#102033]"><option value="">全部级别</option><option value="critical">严重</option><option value="high">高</option><option value="medium">中</option><option value="low">低</option></select>
      <select aria-label="问题时间范围" value={timeRange} onChange={(event) => setTimeRange(event.target.value as ProblemTimeRange)} className="h-9 min-w-[128px] rounded-lg border border-[#c9d8ec] bg-white px-2 text-xs text-[#102033]"><option value="24h">最近 24 小时</option><option value="7d">最近 7 天</option><option value="30d">最近 30 天</option><option value="all">全部时间</option></select>
      <select aria-label="问题任务" value={taskId} onChange={(event) => setTaskId(event.target.value)} className="h-9 min-w-[180px] rounded-lg border border-[#c9d8ec] bg-white px-3 text-xs text-[#102033]"><option value="">全部任务</option>{tasks.map((task) => <option key={task.id} value={task.id}>{task.name || "未命名任务"}</option>)}</select>
    </>
  );

  return (
    <section data-problem-center="true" data-window-layout={mode} className="flex h-full min-h-0 min-w-0 flex-col gap-3 animate-fade-up">
      <header className="flex min-w-0 items-start justify-between gap-4">
        <div><div className="flex items-center gap-3"><h1 className="text-xl font-semibold text-[#102033]">问题中心</h1><span className="rounded-full bg-[#fff1f2] px-2.5 py-1 text-xs font-semibold text-[#be123c]">未解决 {summary?.unresolved ?? 0}</span></div><p className="mt-1 text-sm text-[#52657a]">集中查看需要关注的问题、证据和真实可执行动作。</p></div>
        <button type="button" disabled={fetching} onClick={refresh} className="h-9 rounded-lg border border-[#c9d8ec] bg-white px-4 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff] disabled:opacity-50">{fetching ? "刷新中" : "刷新"}</button>
      </header>
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-[#d7e4f5] bg-white p-2">
        <div className="flex overflow-hidden rounded-lg border border-[#c9d8ec]">
          {(["unresolved", "resolved", "ignored"] as StateScope[]).map((item) => <button key={item} type="button" onClick={() => { setScope(item); setSelectedId(null); }} className={cn("h-9 px-4 text-xs font-semibold", scope === item ? "bg-[#3370ff] text-white" : "bg-white text-[#52657a] hover:bg-[#f6faff]")}>{item === "unresolved" ? "未解决" : item === "resolved" ? "已解决" : "已忽略"}</button>)}
        </div>
        {compact ? <button type="button" onClick={() => setFiltersOpen((value) => !value)} className="ml-auto h-9 rounded-lg border border-[#c9d8ec] bg-white px-4 text-xs font-semibold text-[#3370ff]">筛选{category || severity || taskId || timeRange !== "all" ? " · 已启用" : ""}</button> : <div className="ml-auto flex flex-wrap items-center justify-end gap-2">{advancedFilters}</div>}
      </div>
      {compact && filtersOpen ? <div className="grid grid-cols-2 gap-2 rounded-lg border border-[#d7e4f5] bg-[#fbfdff] p-3">{advancedFilters}</div> : null}
      <div className={cn("grid min-h-0 flex-1 gap-4", compact ? "grid-cols-1" : wide ? "grid-cols-[288px_minmax(520px,1fr)_320px]" : "grid-cols-[288px_minmax(680px,1fr)]")}>
        {queue}
        {!compact ? workbench : null}
        {wide && selected ? <aside data-problem-actions="true" className="min-h-0 overflow-y-auto rounded-xl border border-[#d7e4f5] bg-[#fbfdff] p-4"><ProblemActions problem={selected} pending={actionPending || verifyPending} onAction={handleAction} onVerify={handleVerify} wide /><div className="mt-5 border-t border-[#d7e4f5] pt-4 text-xs text-[#52657a]"><p className="font-semibold text-[#102033]">验证规则</p><p className="mt-2 leading-5">冲突检查源记录终态；文件问题只接受同一任务、同一对象、同一操作的后续成功事实，无变化检查不能结案。</p><p className="mt-4 font-semibold text-[#102033]">最近动作</p><p className="mt-2">{actions[0] ? `${actions[0].action_key} · ${actions[0].result}` : "尚未执行动作"}</p></div></aside> : null}
      </div>
    </section>
  );
}

export function ConflictResolutionPage(props: Props) {
  return useRemainingPagesShowcase() ? <ConflictResolutionShowcasePage /> : <ProblemCenterLivePage {...props} />;
}
