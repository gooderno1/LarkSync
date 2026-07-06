import { statusLabelMap } from "./constants";
import type { SyncLogEntry, Tone } from "../types";

export type EventProblemKey =
  | "mirror_folder_forbidden"
  | "docx_block_write_forbidden"
  | "sync_permission_forbidden"
  | "delete_target_missing"
  | "delete_permission_failed"
  | "delete_failed"
  | "conflict"
  | "delete_pending"
  | "cancelled"
  | "sync_failed"
  | "sync_activity";

export type EventProblemMeta = {
  key: EventProblemKey;
  title: string;
  shortLabel: string;
  tone: Tone;
  priority: number;
  needsAction: boolean;
  summary: string;
  cause: string;
  recommendedAction: string;
};

export type EventIssueGroup = {
  key: EventProblemKey;
  problem: EventProblemMeta;
  entries: SyncLogEntry[];
  count: number;
  latestAt: number;
  taskNames: string[];
  unresolvedConflictCount?: number;
};

export type TaskProblemSummary = {
  problem: EventProblemMeta;
  count: number;
};

export type TaskEventGroup = {
  key: string;
  taskName: string;
  latestAt: number;
  entries: SyncLogEntry[];
  problemSummaries: TaskProblemSummary[];
  needsActionCount: number;
};

export type EventRunGroup = {
  key: string;
  runId: string | null;
  label: string;
  latestAt: number;
  entries: SyncLogEntry[];
  problemSummaries: TaskProblemSummary[];
  needsActionCount: number;
};

type EventGroupOptions = {
  includeInformational: boolean;
  unresolvedConflictCount?: number;
};

const NEEDS_ATTENTION_STATUSES = new Set([
  "failed",
  "delete_failed",
  "conflict",
  "delete_pending",
  "cancelled",
]);

const PROBLEM_META: Record<EventProblemKey, EventProblemMeta> = {
  mirror_folder_forbidden: {
    key: "mirror_folder_forbidden",
    title: "权限禁止：云端镜像目录创建失败",
    shortLabel: "镜像目录权限",
    tone: "danger",
    priority: 100,
    needsAction: true,
    summary: "增强 Markdown 模式尝试创建 `_LarkSync_MD_Mirror` 云端目录，但飞书返回 forbidden。",
    cause: "当前账号或应用没有在目标云端目录创建文件夹的权限，或目标位置不允许创建子文件夹。",
    recommendedAction: "如果任务已改为仅下载，重新运行即可避免上行创建；双向任务可改为 doc_only，或补齐目标目录的创建权限后再重试。",
  },
  docx_block_write_forbidden: {
    key: "docx_block_write_forbidden",
    title: "权限禁止：云文档内容写入失败",
    shortLabel: "文档写入权限",
    tone: "danger",
    priority: 102,
    needsAction: true,
    summary: "同步器向飞书 Docx 写入块内容时被拒绝，常见返回为 403 / 1770032 / forBidden。",
    cause: "当前账号或应用对该云文档没有块级写入权限；这不是本地文件缺失，也通常不是 Markdown 格式错误。",
    recommendedAction: "仅需归档时改为仅下载；需要双向写入时，给当前飞书身份补齐目标文档编辑权限后再重试任务。",
  },
  sync_permission_forbidden: {
    key: "sync_permission_forbidden",
    title: "权限禁止：同步写入被拒绝",
    shortLabel: "权限禁止",
    tone: "danger",
    priority: 94,
    needsAction: true,
    summary: "飞书接口返回 forbidden，当前同步动作没有权限完成。",
    cause: "目标云端目录、文件或当前授权范围不允许本次创建、更新或删除动作。",
    recommendedAction: "确认任务同步模式是否需要写云端；若需要写入，补齐飞书目录/文档权限和应用授权后重试。",
  },
  delete_target_missing: {
    key: "delete_target_missing",
    title: "删除状态已失效：云端目标不存在",
    shortLabel: "目标不存在",
    tone: "warning",
    priority: 82,
    needsAction: false,
    summary: "本地状态库仍记录了待删除目标，但云端返回 not found，说明目标已经不存在。",
    cause: "这通常是删除幂等或状态清理问题，不代表用户还需要去云端手动删除同一个文件。",
    recommendedAction: "后续应按幂等删除清理状态库映射；如果界面反复出现，可以在任务诊断里确认影响路径后重新运行任务。",
  },
  delete_permission_failed: {
    key: "delete_permission_failed",
    title: "权限禁止：删除动作失败",
    shortLabel: "删除权限",
    tone: "danger",
    priority: 88,
    needsAction: true,
    summary: "同步器尝试执行删除联动，但目标端拒绝删除。",
    cause: "当前账号或应用没有删除目标文件/文件夹的权限，或目标正在被保护策略限制。",
    recommendedAction: "确认删除联动是预期行为后，补齐目标端删除权限；不希望联动删除时调整任务删除策略。",
  },
  delete_failed: {
    key: "delete_failed",
    title: "删除失败：需要确认目标状态",
    shortLabel: "删除失败",
    tone: "danger",
    priority: 86,
    needsAction: true,
    summary: "删除动作没有完成，可能由权限、文件占用、路径变化或接口错误导致。",
    cause: "同步器无法确认目标已经安全删除，因此保留失败事件供排查。",
    recommendedAction: "查看影响路径和原始日志，确认目标是否仍存在、是否被占用，以及当前任务删除策略是否符合预期。",
  },
  conflict: {
    key: "conflict",
    title: "冲突：需要选择保留版本",
    shortLabel: "冲突",
    tone: "warning",
    priority: 90,
    needsAction: true,
    summary: "本地和云端在同一同步基线后都发生了变化，系统不会直接覆盖任一侧。",
    cause: "为避免数据丢失，LarkSync 保留冲突记录并等待用户选择本地版本或云端版本。",
    recommendedAction: "在右侧冲突处理区选择“使用本地”或“使用云端”；处理前可先查看本地/云端预览。",
  },
  delete_pending: {
    key: "delete_pending",
    title: "待删除：安全删除宽限队列",
    shortLabel: "待删除",
    tone: "warning",
    priority: 52,
    needsAction: false,
    summary: "删除联动已进入安全宽限期，到期后才会执行真正删除。",
    cause: "这是防误删保护，不等同于同步失败；宽限期内仍可在源端恢复文件或调整删除策略。",
    recommendedAction: "如果删除是预期行为，无需处理；如果不是预期，请在宽限期内恢复源端文件或关闭删除联动。",
  },
  cancelled: {
    key: "cancelled",
    title: "同步已取消：确认是否为预期停止",
    shortLabel: "已取消",
    tone: "neutral",
    priority: 42,
    needsAction: false,
    summary: "某次同步运行被停止，没有继续执行后续文件。",
    cause: "可能是手动停止、应用退出、更新重启，或运行过程被外部中断。",
    recommendedAction: "如果不是主动停止，请重新运行任务，并在任务诊断里观察是否再次中断。",
  },
  sync_failed: {
    key: "sync_failed",
    title: "同步失败：需要查看具体错误",
    shortLabel: "同步失败",
    tone: "danger",
    priority: 80,
    needsAction: true,
    summary: "同步动作没有完成，但日志里未命中更具体的权限、删除或冲突分类。",
    cause: "可能是网络、飞书接口、格式转换、本地文件访问或其他运行时错误。",
    recommendedAction: "查看原始错误消息和影响路径；修复权限、网络或文件占用后重新运行任务。",
  },
  sync_activity: {
    key: "sync_activity",
    title: "普通同步记录",
    shortLabel: "普通事件",
    tone: "info",
    priority: 10,
    needsAction: false,
    summary: "上传、下载、跳过、完成等普通运行事件。",
    cause: "这些事件用于追踪同步过程，默认不会作为待处理问题展示。",
    recommendedAction: "通常无需处理；需要审计完整同步过程时再打开“显示全部事件”。",
  },
};

function normalize(value: string | null | undefined): string {
  return (value || "").toLowerCase();
}

function eventText(entry: SyncLogEntry): string {
  return `${entry.status} ${entry.path || ""} ${entry.message || ""}`.toLowerCase();
}

function isForbidden(text: string): boolean {
  return text.includes("forbidden") || text.includes("权限");
}

export function isAttentionEvent(entry: SyncLogEntry): boolean {
  return NEEDS_ATTENTION_STATUSES.has(entry.status);
}

export function classifyEventProblem(entry: SyncLogEntry): EventProblemMeta {
  const text = eventText(entry);
  const status = normalize(entry.status);

  if (status === "conflict") return PROBLEM_META.conflict;
  if (status === "delete_pending") return PROBLEM_META.delete_pending;
  if (status === "cancelled") return PROBLEM_META.cancelled;

  if (status === "delete_failed") {
    if (text.includes("not found") || text.includes("not_found") || text.includes("不存在")) {
      return PROBLEM_META.delete_target_missing;
    }
    if (isForbidden(text)) return PROBLEM_META.delete_permission_failed;
    return PROBLEM_META.delete_failed;
  }

  if (status === "failed") {
    if (
      text.includes("_larksync_md_mirror") ||
      (text.includes("创建云端文件夹失败") && isForbidden(text))
    ) {
      return PROBLEM_META.mirror_folder_forbidden;
    }
    if (
      text.includes("创建块失败") ||
      text.includes("1770032") ||
      text.includes("/blocks/") ||
      text.includes("/children")
    ) {
      return isForbidden(text) ? PROBLEM_META.docx_block_write_forbidden : PROBLEM_META.sync_failed;
    }
    if (isForbidden(text)) return PROBLEM_META.sync_permission_forbidden;
    return PROBLEM_META.sync_failed;
  }

  return PROBLEM_META.sync_activity;
}

function shouldIncludeEntry(entry: SyncLogEntry, includeInformational: boolean): boolean {
  if (includeInformational) return true;
  const problem = classifyEventProblem(entry);
  return problem.key !== "sync_activity";
}

function sortIssueGroups(a: EventIssueGroup, b: EventIssueGroup): number {
  if (a.problem.needsAction !== b.problem.needsAction) return a.problem.needsAction ? -1 : 1;
  if (a.problem.priority !== b.problem.priority) return b.problem.priority - a.problem.priority;
  return b.latestAt - a.latestAt;
}

function sortTaskGroups(a: TaskEventGroup, b: TaskEventGroup): number {
  if (a.needsActionCount !== b.needsActionCount) return b.needsActionCount - a.needsActionCount;
  return b.latestAt - a.latestAt;
}

function sortRunGroups(a: EventRunGroup, b: EventRunGroup): number {
  if (a.needsActionCount !== b.needsActionCount) return b.needsActionCount - a.needsActionCount;
  return b.latestAt - a.latestAt;
}

function compactRunId(runId: string): string {
  if (runId.length <= 18) return runId;
  return `${runId.slice(0, 8)}...${runId.slice(-6)}`;
}

function summarizeProblemCounts(summaries: TaskProblemSummary[]): string {
  if (summaries.length === 0) return "暂无需要关注的事件。";
  return summaries
    .slice(0, 4)
    .map(({ problem, count }) => `${problem.shortLabel} ${count} 条`)
    .join("；");
}

export function buildEventIssueGroups(
  entries: SyncLogEntry[],
  options: EventGroupOptions,
): EventIssueGroup[] {
  const grouped = new Map<EventProblemKey, EventIssueGroup>();

  for (const entry of entries) {
    if (!shouldIncludeEntry(entry, options.includeInformational)) continue;
    const problem = classifyEventProblem(entry);
    const group = grouped.get(problem.key) ?? {
      key: problem.key,
      problem,
      entries: [],
      count: 0,
      latestAt: 0,
      taskNames: [],
    };
    group.entries.push(entry);
    group.count += 1;
    group.latestAt = Math.max(group.latestAt, entry.timestamp || 0);
    if (entry.taskName && !group.taskNames.includes(entry.taskName)) {
      group.taskNames.push(entry.taskName);
    }
    grouped.set(problem.key, group);
  }

  const unresolvedConflictCount = options.unresolvedConflictCount ?? 0;
  if (unresolvedConflictCount > 0 && !grouped.has("conflict")) {
    grouped.set("conflict", {
      key: "conflict",
      problem: PROBLEM_META.conflict,
      entries: [],
      count: unresolvedConflictCount,
      latestAt: 0,
      taskNames: [],
      unresolvedConflictCount,
    });
  }

  return Array.from(grouped.values()).sort(sortIssueGroups);
}

export function buildTaskEventGroups(
  entries: SyncLogEntry[],
  options: Pick<EventGroupOptions, "includeInformational">,
): TaskEventGroup[] {
  const grouped = new Map<string, TaskEventGroup>();
  const problemCounts = new Map<string, Map<EventProblemKey, TaskProblemSummary>>();

  for (const entry of entries) {
    if (!shouldIncludeEntry(entry, options.includeInformational)) continue;
    const key = entry.taskId || entry.taskName || entry.path || "unknown-task";
    const problem = classifyEventProblem(entry);
    const group = grouped.get(key) ?? {
      key,
      taskName: entry.taskName || "未命名任务",
      latestAt: 0,
      entries: [],
      problemSummaries: [],
      needsActionCount: 0,
    };
    group.entries.push(entry);
    group.latestAt = Math.max(group.latestAt, entry.timestamp || 0);
    group.needsActionCount += problem.needsAction ? 1 : 0;
    grouped.set(key, group);

    const taskProblemCounts = problemCounts.get(key) ?? new Map<EventProblemKey, TaskProblemSummary>();
    const summary = taskProblemCounts.get(problem.key) ?? { problem, count: 0 };
    summary.count += 1;
    taskProblemCounts.set(problem.key, summary);
    problemCounts.set(key, taskProblemCounts);
  }

  for (const [key, group] of grouped.entries()) {
    const summaries = Array.from(problemCounts.get(key)?.values() ?? []);
    group.problemSummaries = summaries.sort((a, b) => {
      if (a.problem.priority !== b.problem.priority) return b.problem.priority - a.problem.priority;
      return b.count - a.count;
    });
  }

  return Array.from(grouped.values()).sort(sortTaskGroups);
}

export function buildEventRunGroups(
  entries: SyncLogEntry[],
  options: Pick<EventGroupOptions, "includeInformational">,
): EventRunGroup[] {
  const grouped = new Map<string, EventRunGroup>();
  const problemCounts = new Map<string, Map<EventProblemKey, TaskProblemSummary>>();

  for (const entry of entries) {
    if (!shouldIncludeEntry(entry, options.includeInformational)) continue;
    const runId = entry.runId || null;
    const key = runId || "no-run";
    const problem = classifyEventProblem(entry);
    const group = grouped.get(key) ?? {
      key,
      runId,
      label: runId ? `运行 ${compactRunId(runId)}` : "无运行 ID",
      latestAt: 0,
      entries: [],
      problemSummaries: [],
      needsActionCount: 0,
    };
    group.entries.push(entry);
    group.latestAt = Math.max(group.latestAt, entry.timestamp || 0);
    group.needsActionCount += problem.needsAction ? 1 : 0;
    grouped.set(key, group);

    const runProblemCounts = problemCounts.get(key) ?? new Map<EventProblemKey, TaskProblemSummary>();
    const summary = runProblemCounts.get(problem.key) ?? { problem, count: 0 };
    summary.count += 1;
    runProblemCounts.set(problem.key, summary);
    problemCounts.set(key, runProblemCounts);
  }

  for (const [key, group] of grouped.entries()) {
    const summaries = Array.from(problemCounts.get(key)?.values() ?? []);
    group.problemSummaries = summaries.sort((a, b) => {
      if (a.problem.priority !== b.problem.priority) return b.problem.priority - a.problem.priority;
      return b.count - a.count;
    });
  }

  return Array.from(grouped.values()).sort(sortRunGroups);
}

export function buildTaskSummaryText(group: TaskEventGroup): string {
  return summarizeProblemCounts(group.problemSummaries);
}

export function buildRunSummaryText(group: EventRunGroup): string {
  return summarizeProblemCounts(group.problemSummaries);
}

export function eventStatusDisplay(entry: SyncLogEntry): string {
  return statusLabelMap[entry.status] || classifyEventProblem(entry).shortLabel || entry.status;
}
