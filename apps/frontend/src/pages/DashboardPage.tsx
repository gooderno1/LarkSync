/* ------------------------------------------------------------------ */
/*  总览工作台                                                          */
/* ------------------------------------------------------------------ */

import { useMemo } from "react";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../hooks/useAuth";
import { useTasks } from "../hooks/useTasks";
import { useConflicts } from "../hooks/useConflicts";
import { useWebSocketLog } from "../hooks/useWebSocketLog";
import { apiFetch } from "../lib/api";
import { formatShortTime, isSameDay } from "../lib/formatters";
import { shortPath } from "../lib/logCenter";
import { modeLabels, stateLabels, stateTones, statusLabelMap } from "../lib/constants";
import { computeTaskProgress } from "../lib/progress";
import { StatCard } from "../components/StatCard";
import {
  IconActivity,
  IconAlertCircle,
  IconAlertTriangle,
  IconArrowDown,
  IconArrowUp,
  IconChevronRight,
  IconCircleCheck,
  IconClock,
  IconFolder,
  IconGlobe,
  IconPlay,
  IconShieldCheck,
  IconTasks,
} from "../components/Icons";
import type { ConflictItem, NavKey, SyncLogEntry, SyncTask, SyncTaskStatus, Tone } from "../types";

type SyncLogResponse = {
  total: number;
  items: SyncLogEntry[];
};

type SyncLogEntryRaw = {
  task_id: string;
  task_name: string;
  timestamp: number;
  status: string;
  path: string;
  message?: string | null;
};

type SyncLogResponseRaw = {
  total: number;
  items: SyncLogEntryRaw[];
};

type Props = { onNavigate: (tab: NavKey) => void };

const FAILURE_STATUSES = new Set(["failed", "delete_failed", "cancelled"]);
const CONFLICT_STATUSES = new Set(["conflict"]);
const DELETE_PENDING_STATUSES = new Set(["delete_pending"]);
const QUEUED_SYNC_STATUSES = new Set(["queued", "creating", "created", "reimporting"]);
const SUCCESS_STATUSES = new Set(["success", "uploaded", "downloaded", "mirrored", "deleted", "linked", "bootstrapped"]);
const REALTIME_BUCKET_COUNT = 20;
const INCOMING_FLOW_STATUSES = new Set(["downloaded"]);
const OUTGOING_FLOW_STATUSES = new Set(["uploaded", "mirrored", "created", "linked"]);

type RealtimeMetrics = {
  latencyMs: number | null;
  incomingEvents: number;
  outgoingEvents: number;
  incomingSeries: number[];
  outgoingSeries: number[];
};

type DashboardRunningRow = {
  id: string;
  name: string;
  subtitle: string;
  localPath: string;
  cloudPath: string;
  iconVariant?: "folder" | "globe";
  progress: number;
  speedLabel: string;
  stateLabel: string;
  stateTone: Tone;
  etaLabel: string;
  task?: SyncTask;
};

type DashboardRecentRow = {
  id: string;
  timeLabel: string;
  taskName: string;
  directionSymbol: string;
  statusLabel: string;
  statusTone: Tone;
  path: string;
  volumeLabel: string;
  durationLabel: string;
};

type DashboardAttentionPreview = {
  id: string;
  title: string;
  fileName: string;
  folderPath: string;
  timeLabel: string;
  tone: Tone;
};

const SHOWCASE_RUNNING_ROWS: DashboardRunningRow[] = [
  {
    id: "showcase-running-1",
    name: "项目文档",
    subtitle: "FEISHU:/Lark/项目文档",
    localPath: "D:/Knowledge/FeishuMirror/项目文档",
    cloudPath: "我的空间 / 项目文档",
    iconVariant: "folder",
    progress: 68,
    speedLabel: "12.4 MB/s",
    stateLabel: "同步中",
    stateTone: "success",
    etaLabel: "00:01:12",
  },
  {
    id: "showcase-running-2",
    name: "设计资源",
    subtitle: "FEISHU:/Lark/设计资源",
    localPath: "D:/Design/Resources",
    cloudPath: "我的空间 / 设计资源",
    iconVariant: "folder",
    progress: 42,
    speedLabel: "8.7 MB/s",
    stateLabel: "同步中",
    stateTone: "success",
    etaLabel: "00:02:08",
  },
  {
    id: "showcase-running-3",
    name: "公开资料库",
    subtitle: "FEISHU:/Lark/公开资料库",
    localPath: "D:/Company/PublicInfo",
    cloudPath: "共享空间 / 公开资料库",
    iconVariant: "globe",
    progress: 91,
    speedLabel: "5.2 MB/s",
    stateLabel: "同步中",
    stateTone: "success",
    etaLabel: "00:00:18",
  },
];

const SHOWCASE_RECENT_ROWS: DashboardRecentRow[] = [
  {
    id: "showcase-recent-1",
    timeLabel: "10:22:14",
    taskName: "项目文档",
    directionSymbol: "↓",
    statusLabel: "成功",
    statusTone: "success",
    path: "128",
    volumeLabel: "256.3 MB",
    durationLabel: "00:01:34",
  },
  {
    id: "showcase-recent-2",
    timeLabel: "10:20:48",
    taskName: "设计资源",
    directionSymbol: "↑",
    statusLabel: "成功",
    statusTone: "success",
    path: "86",
    volumeLabel: "98.7 MB",
    durationLabel: "00:00:55",
  },
  {
    id: "showcase-recent-3",
    timeLabel: "10:18:32",
    taskName: "公开资料库",
    directionSymbol: "↓",
    statusLabel: "成功",
    statusTone: "success",
    path: "512",
    volumeLabel: "1.02 GB",
    durationLabel: "00:03:21",
  },
  {
    id: "showcase-recent-4",
    timeLabel: "10:15:11",
    taskName: "项目文档",
    directionSymbol: "↑",
    statusLabel: "成功",
    statusTone: "success",
    path: "73",
    volumeLabel: "64.1 MB",
    durationLabel: "00:00:42",
  },
  {
    id: "showcase-recent-5",
    timeLabel: "10:12:03",
    taskName: "设计资源",
    directionSymbol: "↓",
    statusLabel: "成功",
    statusTone: "success",
    path: "201",
    volumeLabel: "312.5 MB",
    durationLabel: "00:01:58",
  },
  {
    id: "showcase-recent-6",
    timeLabel: "10:08:46",
    taskName: "公开资料库",
    directionSymbol: "↓",
    statusLabel: "成功",
    statusTone: "success",
    path: "94",
    volumeLabel: "141.8 MB",
    durationLabel: "00:01:16",
  },
  {
    id: "showcase-recent-7",
    timeLabel: "10:05:27",
    taskName: "项目文档",
    directionSymbol: "↑",
    statusLabel: "成功",
    statusTone: "success",
    path: "37",
    volumeLabel: "42.6 MB",
    durationLabel: "00:00:31",
  },
];

const SHOWCASE_REALTIME_METRICS: RealtimeMetrics = {
  latencyMs: 24,
  incomingEvents: 7,
  outgoingEvents: 5,
  incomingSeries: [12, 18, 15, 20, 14, 22, 19, 34, 27, 30, 18, 22, 14, 19, 29, 42, 34, 39, 31, 28],
  outgoingSeries: [5, 9, 6, 7, 4, 8, 10, 18, 9, 11, 5, 8, 3, 6, 10, 21, 13, 17, 10, 7],
};

const SHOWCASE_ATTENTION_PREVIEW: DashboardAttentionPreview = {
  id: "showcase-conflict",
  title: "冲突待处理",
  fileName: "需求说明.md",
  folderPath: "项目文档/需求/",
  timeLabel: "10:24",
  tone: "danger",
};

function getStatusActivityTime(status?: SyncTaskStatus | null): number | null {
  return status?.finished_at ?? status?.started_at ?? null;
}

function getTaskActivityTime(
  task: SyncTask,
  status: SyncTaskStatus | undefined,
  latestLogTime?: number
): number {
  return (
    getStatusActivityTime(status) ??
    task.last_run_at ??
    latestLogTime ??
    task.updated_at ??
    task.created_at
  );
}

function getDashboardEventTone(status: string): Tone {
  if (FAILURE_STATUSES.has(status)) return "danger";
  if (CONFLICT_STATUSES.has(status) || DELETE_PENDING_STATUSES.has(status)) return "warning";
  if (QUEUED_SYNC_STATUSES.has(status)) return "info";
  if (SUCCESS_STATUSES.has(status)) return "success";
  return "neutral";
}

function getDashboardDirectionSymbol(status: string): string {
  if (status === "uploaded") return "↑";
  if (status === "downloaded") return "↓";
  return "↔";
}

function buildRunningRow(
  task: SyncTask,
  status: SyncTaskStatus | undefined,
  latestLogTimeByTask: Record<string, number>
): DashboardRunningRow {
  const stateKey = !task.enabled ? "paused" : status?.state || "idle";
  const progressState = computeTaskProgress(status);
  const progress = progressState.progress ?? (stateKey === "success" ? 100 : 0);
  const throughputCount =
    (status?.uploaded_files ?? 0) +
    (status?.downloaded_files ?? 0) +
    (status?.deleted_files ?? 0);

  return {
    id: task.id,
    name: task.name || task.local_path,
    subtitle: modeLabels[task.sync_mode] || task.sync_mode,
    localPath: shortPath(task.local_path, 42),
    cloudPath: shortPath(task.cloud_folder_name || task.cloud_folder_token, 38),
    progress,
    speedLabel: throughputCount > 0 ? `${throughputCount} 文件` : "--",
    stateLabel: stateLabels[stateKey] || stateKey,
    stateTone: stateTones[stateKey] || "neutral",
    etaLabel:
      status?.state === "running"
        ? "计算中"
        : formatShortTime(getTaskActivityTime(task, status, latestLogTimeByTask[task.id])),
    task,
  };
}

export function buildRecentRow(entry: SyncLogEntry): DashboardRecentRow {
  return {
    id: `${entry.taskId}-${entry.timestamp}-${entry.path}`,
    timeLabel: formatShortTime(entry.timestamp),
    taskName: entry.taskName,
    directionSymbol: getDashboardDirectionSymbol(entry.status),
    statusLabel: statusLabelMap[entry.status] || entry.status,
    statusTone: getDashboardEventTone(entry.status),
    path: shortPath(entry.path, 48),
    volumeLabel: "—",
    durationLabel: "—",
  };
}

function buildAttentionPreview(entry: SyncLogEntry): DashboardAttentionPreview {
  const normalizedPath = entry.path.replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
  const pathParts = normalizedPath.split("/").filter(Boolean);
  const fileName = pathParts[pathParts.length - 1] || entry.taskName;
  const folderPath = pathParts.length > 1
    ? `${pathParts.slice(0, -1).join("/")}/`
    : entry.taskName;

  return {
    id: `${entry.taskId}-${entry.timestamp}-${entry.path}`,
    title: statusLabelMap[entry.status] || entry.status,
    fileName,
    folderPath,
    timeLabel: formatShortTime(entry.timestamp),
    tone: getDashboardEventTone(entry.status),
  };
}

function buildConflictAttentionPreview(conflict: ConflictItem): DashboardAttentionPreview {
  const normalizedPath = conflict.local_path.replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
  const pathParts = normalizedPath.split("/").filter(Boolean);
  return {
    id: conflict.id,
    title: "冲突待处理",
    fileName: pathParts[pathParts.length - 1] || "未命名文件",
    folderPath: pathParts.length > 1 ? `${pathParts.slice(0, -1).join("/")}/` : "本地文件",
    timeLabel: formatShortTime(conflict.created_at),
    tone: "danger",
  };
}

export function shouldUseDashboardShowcase(search: string, isDevelopment: boolean): boolean {
  if (!isDevelopment) return false;
  return new URLSearchParams(search).get("ui-demo") === "dashboard";
}

export function selectDashboardRecentRows(entries: SyncLogEntry[], showcaseMode: boolean): DashboardRecentRow[] {
  return showcaseMode
    ? SHOWCASE_RECENT_ROWS
    : entries.slice(0, 7).map((entry) => buildRecentRow(entry));
}

export function formatDashboardRelativeTime(timestamp?: number | null, nowSeconds = Date.now() / 1000): string {
  if (!timestamp) return "暂无";
  const elapsed = Math.max(0, Math.floor(nowSeconds - timestamp));
  if (elapsed < 60) return "刚刚";
  if (elapsed < 60 * 60) return `${Math.floor(elapsed / 60)} 分钟前`;
  if (elapsed < 24 * 60 * 60) return `${Math.floor(elapsed / (60 * 60))} 小时前`;
  if (elapsed < 7 * 24 * 60 * 60) return `${Math.floor(elapsed / (24 * 60 * 60))} 天前`;
  return formatShortTime(timestamp);
}

const inlineStatusStyles: Record<Tone, string> = {
  neutral: "text-[#6b7f96]",
  info: "text-[#3370ff]",
  success: "text-[#059669]",
  warning: "text-[#d97706]",
  danger: "text-[#e11d48]",
};

const inlineStatusDotStyles: Record<Tone, string> = {
  neutral: "bg-[#94a3b8]",
  info: "bg-[#3370ff]",
  success: "bg-[#10b981]",
  warning: "bg-[#f59e0b]",
  danger: "bg-[#f43f5e]",
};

const attentionCardStyles: Record<Tone, string> = {
  neutral: "border-[#d7e4f5] bg-[#f8fbff]",
  info: "border-[#bfdbfe] bg-[#f7fbff]",
  success: "border-[#a7f3d0] bg-[#f6fffb]",
  warning: "border-[#fde68a] bg-[#fffdf5]",
  danger: "border-[#fecdd3] bg-[#fffafb]",
};

function RunningInlineStatus({ label, tone }: { label: string; tone: Tone }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 whitespace-nowrap text-xs font-medium text-[#52657a]"
      data-dashboard-row-status="dot"
    >
      <span className={`h-2 w-2 rounded-full ${inlineStatusDotStyles[tone]}`} aria-hidden="true" />
      {label}
    </span>
  );
}

function RecentInlineStatus({ label, tone }: { label: string; tone: Tone }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap text-xs font-medium ${inlineStatusStyles[tone]}`}
      data-dashboard-recent-status="check"
    >
      {tone === "success" ? (
        <IconCircleCheck className="h-4 w-4" />
      ) : (
        <IconAlertCircle className="h-4 w-4" />
      )}
      {label}
    </span>
  );
}

function Panel({
  title,
  hint,
  action,
  children,
  className = "",
  dataKey,
  contentClassName = "",
}: {
  title: string;
  hint?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  dataKey?: "running" | "recent";
  contentClassName?: string;
}) {
  return (
    <section className={`flex min-w-0 flex-col overflow-hidden rounded-lg border border-[#d7e4f5] bg-white p-4 shadow-[0_8px_24px_rgba(51,112,255,0.035)] ${className}`} data-dashboard-panel={dataKey}>
      <div className="mb-2.5 flex min-w-0 flex-none flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-[#102033]">{title}</h2>
          {hint ? <p className="mt-1 text-xs text-[#6b7f96]">{hint}</p> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
      <div className={`min-h-0 flex-1 ${contentClassName}`}>{children}</div>
    </section>
  );
}

export function buildRealtimeMetrics(entries: SyncLogEntry[]): RealtimeMetrics {
  const incomingSeries = Array.from({ length: REALTIME_BUCKET_COUNT }, () => 0);
  const outgoingSeries = Array.from({ length: REALTIME_BUCKET_COUNT }, () => 0);
  const orderedEntries = [...entries]
    .sort((a, b) => a.timestamp - b.timestamp)
    .slice(-80);
  const firstTime = orderedEntries[0]?.timestamp ?? 0;
  const lastTime = orderedEntries[orderedEntries.length - 1]?.timestamp ?? firstTime;
  const span = Math.max(1, lastTime - firstTime);
  let incomingEvents = 0;
  let outgoingEvents = 0;

  orderedEntries.forEach((entry, index) => {
    const bucket = span <= 1
      ? Math.min(REALTIME_BUCKET_COUNT - 1, index % REALTIME_BUCKET_COUNT)
      : Math.min(
        REALTIME_BUCKET_COUNT - 1,
        Math.floor(((entry.timestamp - firstTime) / span) * (REALTIME_BUCKET_COUNT - 1))
      );
    if (INCOMING_FLOW_STATUSES.has(entry.status)) {
      incomingEvents += 1;
      incomingSeries[bucket] += 10;
      return;
    }
    if (OUTGOING_FLOW_STATUSES.has(entry.status)) {
      outgoingEvents += 1;
      outgoingSeries[bucket] += 10;
      return;
    }
  });

  return {
    latencyMs: null,
    incomingEvents,
    outgoingEvents,
    incomingSeries,
    outgoingSeries,
  };
}

function RealtimeLineChart({ metrics }: { metrics: RealtimeMetrics }) {
  const { incomingSeries, outgoingSeries } = metrics;
  const hasTransferEvents =
    incomingSeries.some((value) => value > 0) || outgoingSeries.some((value) => value > 0);

  if (!hasTransferEvents) {
    return (
      <div
        className="mt-4 flex min-h-[124px] flex-1 items-center justify-center border-y border-[#dce7f3] text-xs font-medium text-[#52657a]"
        data-dashboard-realtime-state="empty"
      >
        暂无传输事件
      </div>
    );
  }

  const toPoints = (values: number[]) => {
    const max = Math.max(1, ...incomingSeries, ...outgoingSeries);
    const step = 240 / (values.length - 1);
    return values
      .map((value, index) => {
        const x = Math.round(index * step);
        const y = Math.round(126 - (value / max) * 104);
        return `${x},${y}`;
      })
      .join(" ");
  };

  return (
    <div className="mt-4 min-h-[124px] flex-1 overflow-hidden">
      <svg className="h-full w-full" viewBox="0 0 240 140" role="img" aria-label="今日传输事件趋势" preserveAspectRatio="none">
        <path d="M0 134H240" stroke="#edf3fb" strokeWidth="1" />
        <polyline points={toPoints(incomingSeries)} fill="none" stroke="#3370ff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <polyline points={toPoints(outgoingSeries)} fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        {incomingSeries.map((value, index) => {
          const x = Math.round(index * (240 / (incomingSeries.length - 1)));
          const y = Math.round(126 - (value / Math.max(1, ...incomingSeries, ...outgoingSeries)) * 104);
          return <circle key={`in-${index}`} cx={x} cy={y} r="2" fill="#3370ff" />;
        })}
        {outgoingSeries.map((value, index) => {
          const x = Math.round(index * (240 / (outgoingSeries.length - 1)));
          const y = Math.round(126 - (value / Math.max(1, ...incomingSeries, ...outgoingSeries)) * 104);
          return <circle key={`out-${index}`} cx={x} cy={y} r="2" fill="#10b981" />;
        })}
      </svg>
    </div>
  );
}

function RunningRowIcon({ variant }: { variant?: DashboardRunningRow["iconVariant"] }) {
  if (variant === "globe") {
    return (
      <span className="grid h-8 w-8 shrink-0 place-items-center text-[#3370ff]">
        <IconGlobe className="h-6 w-6" />
      </span>
    );
  }

  if (variant === "folder") {
    return (
      <span className="grid h-8 w-8 shrink-0 place-items-center text-[#f5a400]">
        <IconFolder className="h-6 w-6 fill-current stroke-current" />
      </span>
    );
  }

  return (
    <span className="grid h-8 w-8 shrink-0 place-items-center text-[#3370ff]">
      <IconFolder className="h-6 w-6" />
    </span>
  );
}

export function DashboardPage({ onNavigate }: Props) {
  const { connected } = useAuth();
  const { tasks, taskLoading, statusMap, runTask } = useTasks();
  const { conflicts } = useConflicts();
  const { entries: wsEntries } = useWebSocketLog(connected);

  const syncLogsQuery = useQuery<SyncLogResponse>({
    queryKey: ["sync-logs-dashboard"],
    queryFn: async () => {
      const raw = await apiFetch<SyncLogResponseRaw>("/sync/logs/sync?limit=200&order=desc");
      return {
        total: raw.total,
        items: raw.items.map((item) => ({
          taskId: item.task_id,
          taskName: item.task_name,
          timestamp: item.timestamp,
          status: item.status,
          path: item.path,
          message: item.message ?? null,
        })),
      };
    },
    staleTime: 5_000,
  });

  const historyEntries = syncLogsQuery.data?.items || [];
  const pollingEntries: SyncLogEntry[] = useMemo(() => {
    return Object.values(statusMap)
      .flatMap((st) =>
        (st.last_files || []).map((f) => ({
          taskId: st.task_id,
          taskName: tasks.find((t) => t.id === st.task_id)?.name || "未命名任务",
          timestamp: f.timestamp ?? st.finished_at ?? st.started_at ?? Math.floor(Date.now() / 1000),
          status: f.status,
          path: f.path,
          message: f.message,
        }))
      )
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, 200);
  }, [statusMap, tasks]);

  const baseEntries = historyEntries.length > 0 ? historyEntries : pollingEntries;
  const syncLogEntries = wsEntries.length > 0 ? wsEntries : baseEntries;
  const latestLogTimeByTask = useMemo(() => {
    const mapped: Record<string, number> = {};
    for (const entry of syncLogEntries) {
      mapped[entry.taskId] = Math.max(mapped[entry.taskId] ?? 0, entry.timestamp);
    }
    return mapped;
  }, [syncLogEntries]);

  const unresolvedConflicts = conflicts.filter((c) => !c.resolved);
  const today = new Date();
  const enabledTasks = tasks.filter((t) => t.enabled).length;
  const runningTasks = tasks.filter((t) => statusMap[t.id]?.state === "running").length;
  const pausedTasks = tasks.length - enabledTasks;
  const waitingTasks = Math.max(0, enabledTasks - runningTasks);
  const todayEventCount = syncLogEntries.filter((e) => isSameDay(e.timestamp, today)).length;
  const failedEventCount = syncLogEntries.filter((e) => FAILURE_STATUSES.has(e.status)).length;
  const deletePendingCount = syncLogEntries.filter((e) => DELETE_PENDING_STATUSES.has(e.status)).length;
  const queuedSyncCount = syncLogEntries.filter((e) => QUEUED_SYNC_STATUSES.has(e.status)).length;
  const pendingEventCount = deletePendingCount + queuedSyncCount;
  const attentionCount = failedEventCount + unresolvedConflicts.length;
  const lastSuccess = syncLogEntries.find((e) => SUCCESS_STATUSES.has(e.status));
  const healthTone: Tone =
    failedEventCount > 0 ? "danger" :
      unresolvedConflicts.length > 0 || pendingEventCount > 0 ? "warning" :
        runningTasks > 0 ? "info" :
          enabledTasks > 0 ? "success" : "neutral";
  const healthLabel =
    failedEventCount > 0 ? "有失败" :
      unresolvedConflicts.length > 0 ? "有冲突" :
        deletePendingCount > 0 ? "待删除" :
          queuedSyncCount > 0 ? "有队列" :
            runningTasks > 0 ? "同步中" :
              enabledTasks > 0 ? "健康" : "未启用";
  const healthHint =
    failedEventCount > 0 ? `${failedEventCount} 条失败或取消事件需要排查` :
      unresolvedConflicts.length > 0 ? `${unresolvedConflicts.length} 个冲突需要处理` :
        deletePendingCount > 0 ? `待删除 ${deletePendingCount} 项，处于安全宽限队列` :
          queuedSyncCount > 0 ? `队列中 ${queuedSyncCount} 项等待执行` :
            runningTasks > 0 ? `正在同步 ${runningTasks} 个任务` :
              enabledTasks > 0 ? "系统运行正常" : "请先启用同步任务";

  const focusEntries = syncLogEntries.filter((entry) =>
    FAILURE_STATUSES.has(entry.status) || DELETE_PENDING_STATUSES.has(entry.status) || QUEUED_SYNC_STATUSES.has(entry.status)
  );
  const runningTaskList = useMemo(
    () => tasks.filter((task) => statusMap[task.id]?.state === "running"),
    [tasks, statusMap]
  );
  const showcaseMode = shouldUseDashboardShowcase(
    typeof window === "undefined" ? "" : window.location.search,
    import.meta.env.DEV
  );
  const runningRows = showcaseMode
    ? SHOWCASE_RUNNING_ROWS
    : runningTaskList.map((task) =>
      buildRunningRow(task, statusMap[task.id], latestLogTimeByTask)
    );
  const recentRows = selectDashboardRecentRows(syncLogEntries, showcaseMode);
  const realtimeMetrics = useMemo(
    () => buildRealtimeMetrics(syncLogEntries.filter((entry) => isSameDay(entry.timestamp, new Date()))),
    [syncLogEntries]
  );
  const attentionPreviewEntries = showcaseMode
    ? [SHOWCASE_ATTENTION_PREVIEW]
    : unresolvedConflicts.length > 0
      ? [buildConflictAttentionPreview(unresolvedConflicts[0])]
      : focusEntries.slice(0, 1).map(buildAttentionPreview);
  const displayHealthTone = showcaseMode ? "success" : healthTone;
  const displayHealthLabel = showcaseMode ? "健康" : healthLabel;
  const displayHealthHint = showcaseMode ? "系统运行正常" : healthHint;
  const displayTotalTasks = showcaseMode ? 5 : tasks.length;
  const displayEnabledTasks = showcaseMode ? 5 : enabledTasks;
  const displayRunningCount = showcaseMode ? 3 : runningTasks;
  const displayWaitingTasks = showcaseMode ? 2 : waitingTasks;
  const displayPausedTasks = showcaseMode ? 0 : pausedTasks;
  const displayLastSyncValue = showcaseMode ? "2 分钟前" : formatDashboardRelativeTime(lastSuccess?.timestamp);
  const displayLastSyncHint = showcaseMode ? "下一次：1 分钟后" : lastSuccess ? lastSuccess.taskName : `今日日志事件 ${todayEventCount} 条`;
  const displayAttentionValue = showcaseMode ? 1 : attentionCount + pendingEventCount;
  const displayAttentionHint = showcaseMode
    ? "冲突 1 个 / 问题 0 个"
    : `冲突 ${unresolvedConflicts.length} / 问题 ${failedEventCount} / 队列 ${pendingEventCount}`;
  const displayRealtimeMetrics = showcaseMode ? SHOWCASE_REALTIME_METRICS : realtimeMetrics;
  const displayTodayActivityCount = showcaseMode ? 12 : todayEventCount;
  const displayTodayActivityHint = `下载 ${displayRealtimeMetrics.incomingEvents} / 上传 ${displayRealtimeMetrics.outgoingEvents}`;
  const taskCoverage = displayTotalTasks > 0 ? Math.round((displayEnabledTasks / displayTotalTasks) * 100) : 0;
  const transferEventCount = displayRealtimeMetrics.incomingEvents + displayRealtimeMetrics.outgoingEvents;
  const hasConflictAttention = showcaseMode || unresolvedConflicts.length > 0;

  return (
    <section className="dashboard-clarity flex min-h-full min-w-0 flex-col animate-fade-up">
      {!connected ? (
        <div className="mb-4 flex-none rounded-xl border border-[#f43f5e]/30 bg-[#fff1f2] p-4 text-sm text-[#be123c]">
          飞书账号未连接，请刷新页面以完成授权引导。
        </div>
      ) : null}

      <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_316px] gap-5 overflow-hidden">
        <div className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden" data-dashboard-main-column="true">
          <div className="flex h-9 min-w-0 flex-none flex-wrap items-center justify-between gap-4">
            <div className="min-w-0">
              <h1 className="text-lg font-semibold leading-6 text-[#102033]">同步健康</h1>
            </div>
          </div>

          <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-5">
          <div className="grid h-[146px] flex-none grid-cols-4 gap-4" data-dashboard-summary="true">
            <StatCard label="总体状态" value={displayHealthLabel} hint={displayHealthHint} tone={displayHealthTone} icon={<IconShieldCheck className="h-20 w-20" />} iconFrame="plain" />
            <StatCard label="今日活动" value={`${displayTodayActivityCount}`} hint={displayTodayActivityHint} tone={displayTodayActivityCount > 0 ? "info" : "neutral"} icon={<IconActivity className="h-8 w-8" />} />
            <StatCard label="最近同步" value={displayLastSyncValue} hint={displayLastSyncHint} tone="success" icon={<IconClock className="h-14 w-14 text-[#12b8c8]" />} iconFrame="plain" valueClassName="text-[21px] tracking-[-0.02em]" />
            <StatCard label="待处理项" value={`${displayAttentionValue}`} hint={displayAttentionHint} tone={displayAttentionValue > 0 ? "warning" : "success"} icon={<IconAlertCircle className="h-14 w-14" />} iconFrame="plain" />
          </div>

          <Panel
            title="正在运行"
            className="h-[300px] flex-none"
            dataKey="running"
          >
            {taskLoading ? (
              <div className="space-y-3">{[1, 2, 3].map((i) => <div key={i} className="h-16 animate-pulse rounded-xl bg-[#eef5ff]" />)}</div>
            ) : tasks.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center text-center" data-dashboard-running-state="no-tasks">
                <span className="grid h-11 w-11 place-items-center rounded-full bg-[#eef5ff] text-[#6b83a7]">
                  <IconTasks className="h-6 w-6" />
                </span>
                <p className="mt-3 text-sm font-medium text-[#334762]">还没有同步任务</p>
                <p className="mt-1 text-xs text-[#6b7f96]">创建任务后，运行进度会显示在这里。</p>
                <button
                  className="mt-4 rounded-lg bg-[#3370ff] px-4 py-2 text-xs font-semibold text-white hover:bg-[#2563eb]"
                  onClick={() => onNavigate("tasks")}
                  type="button"
                >
                  创建任务
                </button>
              </div>
            ) : runningRows.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center text-center" data-dashboard-running-state="idle">
                <span className="grid h-11 w-11 place-items-center rounded-full bg-[#eef5ff] text-[#3370ff]">
                  <IconActivity className="h-6 w-6" />
                </span>
                <p className="mt-3 text-sm font-medium text-[#334762]">当前没有正在运行的任务</p>
                <p className="mt-1 text-xs text-[#6b7f96]">任务开始同步后，将在此处显示实时进度。</p>
                <button
                  className="mt-4 rounded-lg border border-[#bfd8ff] bg-white px-4 py-2 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]"
                  onClick={() => onNavigate("tasks")}
                  type="button"
                >
                  管理任务
                </button>
              </div>
            ) : (
              <div className="min-w-0 overflow-hidden">
                <table className="w-full table-fixed text-left text-sm">
                  <thead className="border-b border-[#d7e4f5] text-[11px] text-[#52657a]">
                    <tr>
                      <th className="w-[19%] py-2 pr-4 font-medium whitespace-nowrap">任务名称</th>
                      <th className="w-[20%] px-4 py-2 font-medium whitespace-nowrap">本地目录</th>
                      <th className="w-[16%] px-4 py-2 font-medium whitespace-nowrap">云端目录</th>
                      <th className="w-[13%] px-4 py-2 font-medium whitespace-nowrap">进度</th>
                      <th className="w-[9%] px-4 py-2 font-medium whitespace-nowrap">速度</th>
                      <th className="w-[9%] px-4 py-2 font-medium whitespace-nowrap">状态</th>
                      <th className="w-[8%] px-4 py-2 font-medium whitespace-nowrap">剩余时间</th>
                      <th className="w-[6%] py-2 pl-4 font-medium text-right"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#edf3fb]">
                    {runningRows.map((row) => {
                      const actionDisabled = !row.task;
                      return (
                        <tr key={row.id} className="text-[#334762]">
                          <td className="py-2.5 pr-4">
                            <div className="flex min-w-0 items-center gap-3">
                              <RunningRowIcon variant={row.iconVariant} />
                              <div className="min-w-0">
                                <p className="truncate font-semibold text-[#102033]">{row.name}</p>
                                <p className="mt-0.5 truncate text-xs text-[#6b7f96]">{row.subtitle}</p>
                              </div>
                            </div>
                          </td>
                          <td className="truncate px-4 py-2.5 font-mono text-xs" title={row.localPath}>{row.localPath}</td>
                          <td className="truncate px-4 py-2.5 text-xs" title={row.cloudPath}>{row.cloudPath}</td>
                          <td className="px-4 py-2.5">
                            <div className="flex min-w-0 flex-col gap-1.5">
                              <span className="text-xs text-[#52657a]">{row.progress}%</span>
                              <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#dce8f8]">
                                <div className="h-full rounded-full bg-[#3370ff]" style={{ width: `${row.progress}%` }} />
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-2.5">
                            <span className="whitespace-nowrap text-xs text-[#52657a]">{row.speedLabel}</span>
                          </td>
                          <td className="px-4 py-2.5">
                            <RunningInlineStatus label={row.stateLabel} tone={row.stateTone} />
                          </td>
                          <td className="px-4 py-2.5 text-xs text-[#52657a]">
                            {row.etaLabel}
                          </td>
                          <td className="py-2.5 pl-4">
                            <div className="flex items-center justify-end gap-2">
                              <button
                                className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-[#d7e4f5] bg-white text-[#3370ff] transition hover:border-[#bfd8ff] hover:bg-[#eef5ff] disabled:cursor-default disabled:opacity-100"
                                onClick={() => row.task ? runTask(row.task) : undefined}
                                type="button"
                                disabled={actionDisabled}
                                title="立即同步"
                              >
                                <IconPlay className="h-3 w-3" />
                              </button>
                              <button
                                className="inline-flex h-6 w-6 items-center justify-center text-[#52657a] transition hover:text-[#3370ff] disabled:cursor-default disabled:opacity-100"
                                onClick={() => row.task ? onNavigate("tasks") : undefined}
                                type="button"
                                disabled={actionDisabled}
                                title="查看任务"
                              >
                                <span className="text-xs leading-none">···</span>
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>

          <Panel
            title="最近同步"
            className="min-h-0 flex-1"
            dataKey="recent"
            contentClassName="flex flex-col"
          >
            {recentRows.length === 0 ? (
              <div className="rounded-xl border border-dashed border-[#c9d8ec] px-5 py-8 text-center text-sm text-[#6b7f96]">
                暂无同步历史。
              </div>
            ) : (
              <div className="min-h-0 min-w-0 flex-1 overflow-hidden">
                <table className="w-full table-fixed text-left text-sm">
                  <thead className="border-b border-[#d7e4f5] text-xs text-[#52657a]">
                    <tr>
                      <th className="w-[14%] py-1.5 pr-4 font-medium">时间</th>
                      <th className="w-[14%] px-4 py-1.5 font-medium">任务</th>
                      <th className="w-[8%] px-4 py-1.5 font-medium">方向</th>
                      <th className="w-[12%] px-4 py-1.5 font-medium">状态</th>
                      <th className="w-[12%] px-4 py-1.5 font-medium">变更文件</th>
                      <th className="w-[14%] px-4 py-1.5 font-medium">数据量</th>
                      <th className="w-[15%] px-4 py-1.5 font-medium">耗时</th>
                      <th className="w-[11%] py-1.5 pl-4 font-medium text-right"> </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#edf3fb]">
                    {recentRows.map((row) => (
                      <tr key={row.id} className="text-[#334762]" data-dashboard-recent-row="true">
                        <td className="py-1.5 pr-4 text-xs text-[#52657a]">{row.timeLabel}</td>
                        <td className="truncate px-4 py-1.5">{row.taskName}</td>
                        <td className="px-4 py-1.5 text-[#3370ff]">
                          {row.directionSymbol}
                        </td>
                        <td className="px-4 py-1.5">
                          <RecentInlineStatus label={row.statusLabel} tone={row.statusTone} />
                        </td>
                        <td className="truncate px-4 py-1.5 font-mono text-xs" title={row.path}>{row.path}</td>
                        <td className="px-4 py-1.5 text-xs text-[#52657a]">{row.volumeLabel}</td>
                        <td className="px-4 py-1.5 text-xs text-[#52657a]">{row.durationLabel}</td>
                        <td className="py-1.5 pl-4">
                          <button
                            className="inline-flex h-6 w-6 items-center justify-center text-[#52657a] transition hover:text-[#3370ff]"
                            onClick={() => onNavigate("activity")}
                            type="button"
                            title="查看历史"
                          >
                            <IconFolder className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <button
              className="mt-1.5 flex w-full flex-none items-center justify-between text-xs font-semibold text-[#3370ff] hover:text-[#1d4ed8]"
              onClick={() => onNavigate("activity")}
              type="button"
            >
              <span>查看全部历史记录</span>
              <IconChevronRight className="h-4 w-4" />
            </button>
          </Panel>
          </div>
        </div>

        <aside className="grid h-full min-h-0 min-w-0 w-[316px] grid-rows-[146px_300px_minmax(0,1fr)] gap-5 pt-9" data-dashboard-rail="aligned">
          <section className="flex h-full flex-col overflow-hidden rounded-lg border border-[#d7e4f5] bg-white p-4 shadow-[0_8px_24px_rgba(51,112,255,0.055)]">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-base font-semibold text-[#102033]">优先处理</h2>
              <span className="rounded-full bg-[#fff1f2] px-2 py-0.5 text-xs font-semibold text-[#be123c]">{displayAttentionValue}</span>
            </div>
            <div className="mt-3">
              {attentionPreviewEntries.length === 0 ? (
                <div className="flex h-[70px] items-center justify-center rounded-lg border border-dashed border-[#c9d8ec] px-4 text-center text-sm font-medium text-[#52657a]">
                  暂无待处理问题。
                </div>
              ) : (
                attentionPreviewEntries.map((entry, index) => (
                  <button
                    key={entry.id}
                    className={`flex h-[70px] w-full items-center gap-3 rounded-lg border p-3 text-left transition hover:brightness-[0.98] ${attentionCardStyles[entry.tone]}`}
                    data-dashboard-attention-card="summary"
                    data-dashboard-attention-tone={entry.tone}
                    onClick={() => onNavigate(hasConflictAttention ? "conflicts" : "activity")}
                    type="button"
                  >
                    <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white/70 ${inlineStatusStyles[entry.tone]}`}>
                      <IconAlertTriangle className="h-4 w-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className={`truncate text-xs font-semibold ${inlineStatusStyles[entry.tone]}`}>{entry.title}</p>
                      <p className="mt-1 truncate text-xs font-medium text-[#52657a]" title={`${entry.fileName} · ${entry.folderPath}`}>{entry.fileName}</p>
                    </div>
                    <span className="shrink-0 text-xs font-semibold text-[#52657a]">{index + 1}</span>
                    <IconChevronRight className="h-4 w-4 shrink-0 text-[#3370ff]" />
                  </button>
                ))
              )}
            </div>
          </section>

          <section className="h-full overflow-hidden rounded-lg border border-[#d7e4f5] bg-white p-4 shadow-[0_8px_24px_rgba(51,112,255,0.055)]" data-dashboard-task-status="true">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-base font-semibold text-[#102033]">任务状态</h2>
              <span className="text-xs font-medium text-[#52657a]">共 {displayTotalTasks} 个</span>
            </div>
            <div className="mt-4 rounded-lg border border-[#d7e4f5] bg-[#f8fbff] p-3.5">
              <div className="flex items-center justify-between text-xs font-medium text-[#52657a]">
                <span>启用覆盖率</span>
                <span className="font-semibold text-[#3370ff]">{taskCoverage}%</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-[#dce8f8]">
                <div className="h-full rounded-full bg-[#3370ff]" style={{ width: `${taskCoverage}%` }} />
              </div>
              <p className="mt-2 text-[11px] text-[#52657a]">{displayEnabledTasks} 个启用，{displayPausedTasks} 个暂停</p>
            </div>
            <div className="mt-3 grid gap-2 text-xs">
              <div className="flex h-10 items-center justify-between rounded-lg border border-[#d7e4f5] px-3"><span className="inline-flex items-center gap-2 font-medium text-[#52657a]"><span className="h-2 w-2 rounded-full bg-[#3370ff]" />正在运行</span><strong className="text-[#102033]">{displayRunningCount}</strong></div>
              <div className="flex h-10 items-center justify-between rounded-lg border border-[#d7e4f5] px-3"><span className="inline-flex items-center gap-2 font-medium text-[#52657a]"><span className="h-2 w-2 rounded-full bg-[#10b981]" />等待运行</span><strong className="text-[#102033]">{displayWaitingTasks}</strong></div>
              <div className="flex h-10 items-center justify-between rounded-lg border border-[#d7e4f5] px-3"><span className="inline-flex items-center gap-2 font-medium text-[#52657a]"><span className="h-2 w-2 rounded-full bg-[#94a3b8]" />已暂停</span><strong className="text-[#102033]">{displayPausedTasks}</strong></div>
            </div>
          </section>

          <section className="flex h-full flex-col overflow-hidden rounded-lg border border-[#d7e4f5] bg-white p-4 shadow-[0_8px_24px_rgba(51,112,255,0.055)]" data-dashboard-transfer="true">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-base font-semibold text-[#102033]">今日传输</h2>
              <span className="rounded-full bg-[#eef5ff] px-2.5 py-1 text-xs font-semibold text-[#3370ff]">{transferEventCount} 个事件</span>
            </div>
            <div className="mt-3 text-sm text-[#52657a]">
              <div className="flex h-10 items-center justify-between gap-3 border-b border-[#edf3fb]"><span>传输事件</span><span>{transferEventCount}</span></div>
              <div className="flex h-10 items-center justify-between gap-3 border-b border-[#edf3fb]">
                <span className="inline-flex items-center gap-1.5" data-dashboard-flow-direction="incoming"><IconArrowDown className="h-3.5 w-3.5 text-[#3370ff]" />数据流入</span>
                <span>{displayRealtimeMetrics.incomingEvents} 事件</span>
              </div>
              <div className="flex h-10 items-center justify-between gap-3">
                <span className="inline-flex items-center gap-1.5" data-dashboard-flow-direction="outgoing"><IconArrowUp className="h-3.5 w-3.5 text-[#10b981]" />数据流出</span>
                <span>{displayRealtimeMetrics.outgoingEvents} 事件</span>
              </div>
            </div>
            <RealtimeLineChart metrics={displayRealtimeMetrics} />
            <div className="mt-3 flex flex-none items-center justify-between border-t border-[#edf3fb] pt-3 text-xs font-medium text-[#52657a]">
              <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-[#3370ff]" /> 流入</span>
              <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-[#10b981]" /> 流出</span>
            </div>
          </section>
        </aside>
      </div>
    </section>
  );
}
