import { useEffect, useMemo, useState } from "react";
import type { SVGProps } from "react";

type ShortcutInfo = {
  target_token: string;
  target_type: string;
};

type DriveNode = {
  token: string;
  name: string;
  type: string;
  parent_token?: string | null;
  url?: string | null;
  created_time?: string | null;
  modified_time?: string | null;
  owner_id?: string | null;
  shortcut_info?: ShortcutInfo | null;
  children?: DriveNode[];
};

type ConflictItem = {
  id: string;
  local_path: string;
  cloud_token: string;
  local_hash: string;
  db_hash: string;
  cloud_version: number;
  db_version: number;
  local_preview?: string | null;
  cloud_preview?: string | null;
  created_at: number;
  resolved: boolean;
  resolved_action?: string | null;
};

type SyncTask = {
  id: string;
  name?: string | null;
  local_path: string;
  cloud_folder_token: string;
  base_path?: string | null;
  sync_mode: string;
  update_mode?: string | null;
  enabled: boolean;
  created_at: number;
  updated_at: number;
};

type SyncFileEvent = {
  path: string;
  status: string;
  message?: string | null;
  timestamp?: number | null;
};

type SyncTaskStatus = {
  task_id: string;
  state: "idle" | "running" | "success" | "failed" | "cancelled";
  started_at?: number | null;
  finished_at?: number | null;
  total_files: number;
  completed_files: number;
  failed_files: number;
  skipped_files: number;
  last_error?: string | null;
  last_files: SyncFileEvent[];
};

type CloudSelection = {
  token: string;
  name: string;
  path: string;
};

type NavKey = "dashboard" | "tasks" | "logcenter" | "settings";

type TreeNodeProps = {
  node: DriveNode;
  path?: string;
  selectable?: boolean;
  selectedToken?: string | null;
  onSelect?: (selection: CloudSelection) => void;
};

type IconProps = SVGProps<SVGSVGElement>;

const IconDashboard = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    <rect x="3" y="3" width="8" height="8" rx="1.6" />
    <rect x="13" y="3" width="8" height="5" rx="1.6" />
    <rect x="13" y="10" width="8" height="11" rx="1.6" />
    <rect x="3" y="13" width="8" height="8" rx="1.6" />
  </svg>
);

const IconTasks = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    <path d="M3 7.5h6l2 2h10v8.5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-10a2 2 0 0 1 2-2z" />
  </svg>
);

const IconConflicts = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    <path d="M12 3l9 16H3z" />
    <path d="M12 9v4" />
    <path d="M12 17h.01" />
  </svg>
);

const IconSettings = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    <circle cx="12" cy="12" r="3.5" />
    <path d="M19.4 15a1.6 1.6 0 0 0 .3 1.7l.1.1a2 2 0 0 1-1.4 3.4h-.2a1.6 1.6 0 0 0-1.6 1.1l-.1.2a2 2 0 0 1-3.6 0l-.1-.2a1.6 1.6 0 0 0-1.6-1.1H9.8a2 2 0 0 1-1.4-3.4l.1-.1a1.6 1.6 0 0 0 .3-1.7 1.6 1.6 0 0 0-1.3-1.1l-.2-.1a2 2 0 0 1 0-3.6l.2-.1a1.6 1.6 0 0 0 1.3-1.1 1.6 1.6 0 0 0-.3-1.7l-.1-.1A2 2 0 0 1 9.8 3h.2a1.6 1.6 0 0 0 1.6-1.1l.1-.2a2 2 0 0 1 3.6 0l.1.2A1.6 1.6 0 0 0 17 3h.2a2 2 0 0 1 1.4 3.4l-.1.1a1.6 1.6 0 0 0-.3 1.7 1.6 1.6 0 0 0 1.3 1.1l.2.1a2 2 0 0 1 0 3.6l-.2.1a1.6 1.6 0 0 0-1.3 1.1z" />
  </svg>
);

const IconPlus = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    <path d="M12 5v14" />
    <path d="M5 12h14" />
  </svg>
);

const IconRefresh = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    <path d="M20 12a8 8 0 1 1-2.3-5.6" />
    <path d="M20 4v6h-6" />
  </svg>
);

const IconPlay = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
    <path d="M8 5.5v13l10-6.5-10-6.5z" />
  </svg>
);

const IconPause = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
    <path d="M7 5h4v14H7zM13 5h4v14h-4z" />
  </svg>
);

const IconTrash = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    <path d="M3 6h18" />
    <path d="M8 6V4h8v2" />
    <path d="M6 6l1 14h10l1-14" />
  </svg>
);

const IconArrowRightLeft = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    <path d="M7 7h12l-3-3" />
    <path d="M17 17H5l3 3" />
  </svg>
);

const IconArrowDown = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    <path d="M12 4v12" />
    <path d="M8 12l4 4 4-4" />
  </svg>
);

const IconArrowUp = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    <path d="M12 20V8" />
    <path d="M8 12l4-4 4 4" />
  </svg>
);

const IconFolder = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    <path d="M3 7.5h6l2 2h10v8.5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-10a2 2 0 0 1 2-2z" />
  </svg>
);

const IconCloud = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    <path d="M7 18a4 4 0 0 1 .5-8 6 6 0 0 1 11.2 1.7A3.5 3.5 0 1 1 18 18H7z" />
  </svg>
);

const IconChevronDown = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    <path d="M6 9l6 6 6-6" />
  </svg>
);

const IconChevronRight = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    <path d="M9 6l6 6-6 6" />
  </svg>
);
const modeLabels: Record<string, string> = {
  bidirectional: "双向同步",
  download_only: "仅下载",
  upload_only: "仅上传"
};

const updateModeLabels: Record<string, string> = {
  auto: "自动",
  partial: "局部",
  full: "全量"
};

const intervalUnitLabels: Record<string, string> = {
  seconds: "秒",
  hours: "小时",
  days: "天"
};

const statusLabelMap: Record<string, string> = {
  downloaded: "下载",
  uploaded: "上传",
  failed: "失败",
  skipped: "跳过",
  started: "开始",
  success: "完成",
  cancelled: "取消"
};

const stateLabels: Record<string, string> = {
  idle: "空闲",
  running: "同步中",
  success: "完成",
  failed: "失败",
  cancelled: "已取消",
  paused: "已停用"
};

const stateTones: Record<string, "neutral" | "info" | "success" | "warning" | "danger"> = {
  idle: "neutral",
  running: "info",
  success: "success",
  failed: "danger",
  cancelled: "warning",
  paused: "warning"
};

const formatTimestamp = (ts?: number | null) => {
  if (!ts) return "未知时间";
  const date = new Date(ts * 1000);
  if (Number.isNaN(date.getTime())) return "未知时间";
  return date.toLocaleString();
};

const formatShortTime = (ts?: number | null) => {
  if (!ts) return "--:--";
  const date = new Date(ts * 1000);
  if (Number.isNaN(date.getTime())) return "--:--";
  return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
};

const isTimeValue = (value: string) => {
  const parts = value.split(":");
  if (parts.length !== 2) return false;
  const hour = Number(parts[0]);
  const minute = Number(parts[1]);
  if (Number.isNaN(hour) || Number.isNaN(minute)) return false;
  if (hour < 0 || hour > 23) return false;
  if (minute < 0 || minute > 59) return false;
  return true;
};

const formatIntervalLabel = (value: string, unit: string, timeValue: string) => {
  const safeValue = value || "1";
  const unitLabel = intervalUnitLabels[unit] || unit;
  if (unit === "days") {
    const safeTime = timeValue || "01:00";
    return `${safeValue} ${unitLabel} ${safeTime}`;
  }
  return `${safeValue} ${unitLabel}`;
};

const isSameDay = (ts: number, compare: Date) => {
  const date = new Date(ts * 1000);
  return (
    date.getFullYear() === compare.getFullYear() &&
    date.getMonth() === compare.getMonth() &&
    date.getDate() === compare.getDate()
  );
};

const StatusPill = ({
  label,
  tone = "neutral",
  dot = false
}: {
  label: string;
  tone?: "neutral" | "info" | "success" | "warning" | "danger";
  dot?: boolean;
}) => {
  const toneStyles: Record<string, string> = {
    neutral: "border-slate-700 text-slate-300 bg-white/5",
    info: "border-blue-400/40 text-blue-200 bg-blue-500/15",
    success: "border-emerald-400/40 text-emerald-200 bg-emerald-500/15",
    warning: "border-amber-400/40 text-amber-200 bg-amber-500/15",
    danger: "border-rose-400/40 text-rose-200 bg-rose-500/15"
  };

  return (
    <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${toneStyles[tone]}`}>
      {dot ? <span className="h-2 w-2 rounded-full bg-current" /> : null}
      {label}
    </span>
  );
};

const StatCard = ({
  label,
  value,
  hint,
  tone = "neutral",
  icon
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "neutral" | "info" | "success" | "warning" | "danger";
  icon?: JSX.Element;
}) => {
  const toneStyles: Record<string, string> = {
    neutral: "border-slate-700/70",
    info: "border-blue-500/40",
    success: "border-emerald-500/40",
    warning: "border-amber-500/40",
    danger: "border-rose-500/40"
  };

  return (
    <div className={`soft-panel rounded-2xl p-4 ${toneStyles[tone]}`}>
      <div className="flex items-center justify-between">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">{label}</p>
        {icon ? <span className="text-slate-400">{icon}</span> : null}
      </div>
      <p className="mt-3 text-2xl font-semibold text-slate-50">{value}</p>
      {hint ? <p className="mt-2 text-xs text-slate-400">{hint}</p> : null}
    </div>
  );
};

function TreeNode({
  node,
  path = "",
  selectable = false,
  selectedToken = null,
  onSelect
}: TreeNodeProps) {
  const [open, setOpen] = useState(true);
  const isFolder = node.type === "folder";
  const hasChildren = Boolean(node.children && node.children.length);
  const currentPath = path ? `${path}/${node.name}` : node.name;
  const isSelected = selectedToken === node.token;

  return (
    <li className="space-y-2">
      <div className="flex items-center gap-2">
        {isFolder ? (
          <button
            className="flex h-6 w-6 items-center justify-center rounded-full border border-slate-700 text-slate-300"
            onClick={() => setOpen((prev) => !prev)}
            type="button"
          >
            {open ? (
              <IconChevronDown className="h-3.5 w-3.5" />
            ) : (
              <IconChevronRight className="h-3.5 w-3.5" />
            )}
          </button>
        ) : (
          <span className="h-2 w-2 rounded-full bg-slate-600" />
        )}
        <button
          className={`flex items-center gap-2 text-left text-sm ${
            isSelected ? "font-semibold text-emerald-300" : "text-slate-200"
          }`}
          disabled={!selectable || !isFolder}
          onClick={() => {
            if (!selectable || !isFolder) return;
            onSelect?.({ token: node.token, name: node.name, path: currentPath });
          }}
          type="button"
        >
          <IconFolder className="h-4 w-4" />
          <span className="truncate">{node.name}</span>
        </button>
        <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[10px] uppercase tracking-[0.2em] text-slate-400">
          {node.type}
        </span>
        {selectable && isFolder ? (
          <button
            className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
              isSelected
                ? "border-emerald-400/40 bg-emerald-500/15 text-emerald-200"
                : "border-slate-700 text-slate-400 hover:border-slate-600"
            }`}
            onClick={() => onSelect?.({ token: node.token, name: node.name, path: currentPath })}
            type="button"
          >
            选择
          </button>
        ) : null}
      </div>
      {isFolder && hasChildren && open ? (
        <ul className="ml-4 space-y-2 border-l border-slate-800 pl-4">
          {node.children?.map((child) => (
            <TreeNode
              key={child.token}
              node={child}
              path={currentPath}
              selectable={selectable}
              selectedToken={selectedToken}
              onSelect={onSelect}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}
export default function App() {
  const apiBase = import.meta.env.PROD ? "/api" : "";
  const apiUrl = (path: string) => `${apiBase}${path}`;
  const redirectTarget = typeof window !== "undefined" ? window.location.origin : "";
  const loginUrl = redirectTarget
    ? `${apiUrl("/auth/login")}?redirect=${encodeURIComponent(redirectTarget)}`
    : apiUrl("/auth/login");

  const [activeTab, setActiveTab] = useState<NavKey>("dashboard");
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [globalPaused, setGlobalPaused] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">("light");
  const [expandedTasks, setExpandedTasks] = useState<Record<string, boolean>>({});
  const [logTab, setLogTab] = useState<"logs" | "conflicts">("logs");
  const [logFilterStatus, setLogFilterStatus] = useState("all");
  const [logFilterText, setLogFilterText] = useState("");
  const [logLimit, setLogLimit] = useState(60);

  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [expiresAt, setExpiresAt] = useState<number | null>(null);
  const [tree, setTree] = useState<DriveNode | null>(null);
  const [treeLoading, setTreeLoading] = useState(false);
  const [treeError, setTreeError] = useState<string | null>(null);
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [conflictLoading, setConflictLoading] = useState(false);
  const [conflictError, setConflictError] = useState<string | null>(null);
  const [tasks, setTasks] = useState<SyncTask[]>([]);
  const [taskLoading, setTaskLoading] = useState(false);
  const [taskError, setTaskError] = useState<string | null>(null);
  const [taskName, setTaskName] = useState("");
  const [taskLocalPath, setTaskLocalPath] = useState("");
  const [taskBasePath, setTaskBasePath] = useState("");
  const [taskCloudToken, setTaskCloudToken] = useState("");
  const [taskSyncMode, setTaskSyncMode] = useState("bidirectional");
  const [taskUpdateMode, setTaskUpdateMode] = useState("auto");
  const [taskEnabled, setTaskEnabled] = useState(true);
  const [taskUpdateModeMap, setTaskUpdateModeMap] = useState<Record<string, string>>(
    {}
  );
  const [taskSyncModeMap, setTaskSyncModeMap] = useState<Record<string, string>>(
    {}
  );
  const [configAuthorizeUrl, setConfigAuthorizeUrl] = useState("");
  const [configTokenUrl, setConfigTokenUrl] = useState("");
  const [configClientId, setConfigClientId] = useState("");
  const [configClientSecret, setConfigClientSecret] = useState("");
  const [configRedirectUri, setConfigRedirectUri] = useState("");
  const [configSyncMode, setConfigSyncMode] = useState("bidirectional");
  const [configTokenStore, setConfigTokenStore] = useState("keyring");
  const [configUploadValue, setConfigUploadValue] = useState("2");
  const [configUploadUnit, setConfigUploadUnit] = useState("seconds");
  const [configUploadTime, setConfigUploadTime] = useState("01:00");
  const [configDownloadValue, setConfigDownloadValue] = useState("1");
  const [configDownloadUnit, setConfigDownloadUnit] = useState("days");
  const [configDownloadTime, setConfigDownloadTime] = useState("01:00");
  const [showAuthAdvanced, setShowAuthAdvanced] = useState(false);
  const [configLoading, setConfigLoading] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [configStatus, setConfigStatus] = useState<string | null>(null);
  const [selectedCloud, setSelectedCloud] = useState<CloudSelection | null>(null);
  const [folderPickLoading, setFolderPickLoading] = useState(false);
  const [folderPickError, setFolderPickError] = useState<string | null>(null);
  const [taskStatusMap, setTaskStatusMap] = useState<Record<string, SyncTaskStatus>>(
    {}
  );

  useEffect(() => {
    let active = true;
    fetch(apiUrl("/auth/status"))
      .then((res) => res.json())
      .then((data) => {
        if (!active) return;
        setConnected(Boolean(data.connected));
        setExpiresAt(data.expires_at ?? null);
      })
      .catch(() => {
        if (!active) return;
        setConnected(false);
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = window.localStorage.getItem("larksync-theme");
    if (saved === "light" || saved === "dark") {
      setTheme(saved);
    }
  }, []);

  useEffect(() => {
    if (typeof document === "undefined") return;
    document.documentElement.dataset.theme = theme;
    try {
      window.localStorage.setItem("larksync-theme", theme);
    } catch {
      // ignore storage errors
    }
  }, [theme]);

  const loadTasks = () => {
    setTaskLoading(true);
    setTaskError(null);
    fetch(apiUrl("/sync/tasks"))
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "获取任务失败");
        }
        return res.json();
      })
      .then((data) => {
        setTasks(Array.isArray(data) ? data : []);
      })
      .catch((err: Error) => setTaskError(err.message))
      .finally(() => setTaskLoading(false));
  };

  const loadTaskStatus = () => {
    fetch(apiUrl("/sync/tasks/status"))
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "获取任务状态失败");
        }
        return res.json();
      })
      .then((data) => {
        if (!Array.isArray(data)) {
          setTaskStatusMap({});
          return;
        }
        const mapped: Record<string, SyncTaskStatus> = {};
        data.forEach((item: SyncTaskStatus) => {
          if (item?.task_id) {
            mapped[item.task_id] = item;
          }
        });
        setTaskStatusMap(mapped);
      })
      .catch(() => {
        // ignore status errors
      });
  };

  const pickLocalFolder = () => {
    setFolderPickLoading(true);
    setFolderPickError(null);
    fetch(apiUrl("/system/select-folder"), { method: "POST" })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "选择文件夹失败");
        }
        return res.json();
      })
      .then((data) => {
        if (data?.path) {
          setTaskLocalPath(data.path);
          if (!taskBasePath.trim()) {
            setTaskBasePath(data.path);
          }
        }
      })
      .catch((err: Error) => setFolderPickError(err.message))
      .finally(() => setFolderPickLoading(false));
  };

  const selectCloudFolder = (selection: CloudSelection) => {
    setSelectedCloud(selection);
    setTaskCloudToken(selection.token);
  };

  const createTask = () => {
    if (!taskLocalPath.trim() || !taskCloudToken.trim()) {
      setTaskError("请填写本地路径与云端文件夹 token。");
      return;
    }
    setTaskError(null);
    fetch(apiUrl("/sync/tasks"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: taskName.trim() || null,
        local_path: taskLocalPath.trim(),
        cloud_folder_token: taskCloudToken.trim(),
        base_path: taskBasePath.trim() || null,
        sync_mode: taskSyncMode,
        update_mode: taskUpdateMode,
        enabled: taskEnabled
      })
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "创建任务失败");
        }
        return res.json();
      })
      .then(() => {
        setTaskName("");
        setTaskBasePath("");
        setTaskCloudToken("");
        setTaskLocalPath("");
        setTaskSyncMode("bidirectional");
        setTaskUpdateMode("auto");
        setTaskEnabled(true);
        setSelectedCloud(null);
        setShowTaskModal(false);
        loadTasks();
        loadTaskStatus();
      })
      .catch((err: Error) => setTaskError(err.message));
  };

  const toggleTask = (task: SyncTask) => {
    fetch(apiUrl(`/sync/tasks/${task.id}`), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !task.enabled })
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "更新任务失败");
        }
        return res.json();
      })
      .then(() => {
        loadTasks();
        loadTaskStatus();
      })
      .catch((err: Error) => setTaskError(err.message));
  };

  const updateTaskSyncMode = (task: SyncTask, mode: string) => {
    setTaskError(null);
    fetch(apiUrl(`/sync/tasks/${task.id}`), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sync_mode: mode })
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "更新同步模式失败");
        }
        return res.json();
      })
      .then((item: SyncTask) => {
        setTasks((prev) => prev.map((taskItem) => (taskItem.id === item.id ? item : taskItem)));
        setTaskSyncModeMap((prev) => {
          const next = { ...prev };
          delete next[item.id];
          return next;
        });
      })
      .catch((err: Error) => setTaskError(err.message));
  };

  const updateTaskMode = (task: SyncTask, mode: string) => {
    fetch(apiUrl(`/sync/tasks/${task.id}`), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ update_mode: mode })
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "更新任务失败");
        }
        return res.json();
      })
      .then(() => {
        loadTasks();
        loadTaskStatus();
      })
      .catch((err: Error) => setTaskError(err.message));
  };

  const runTask = (task: SyncTask) => {
    setTaskError(null);
    fetch(apiUrl(`/sync/tasks/${task.id}/run`), { method: "POST" })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "触发同步失败");
        }
        return res.json();
      })
      .then(() => {
        loadTaskStatus();
      })
      .catch((err: Error) => setTaskError(err.message));
  };

  const deleteTask = (task: SyncTask) => {
    setTaskError(null);
    fetch(apiUrl(`/sync/tasks/${task.id}`), { method: "DELETE" })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "删除任务失败");
        }
        return res.json();
      })
      .then(() => {
        loadTasks();
        loadTaskStatus();
      })
      .catch((err: Error) => setTaskError(err.message));
  };

  const loadConfig = () => {
    setConfigLoading(true);
    setConfigError(null);
    fetch(apiUrl("/config"))
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "加载配置失败");
        }
        return res.json();
      })
        .then((data) => {
          setConfigAuthorizeUrl(data.auth_authorize_url || "");
          setConfigTokenUrl(data.auth_token_url || "");
          setConfigClientId(data.auth_client_id || "");
          setConfigRedirectUri(data.auth_redirect_uri || "");
          setConfigSyncMode(data.sync_mode || "bidirectional");
          setConfigTokenStore(data.token_store || "keyring");
          if (typeof data.upload_interval_value === "number") {
            setConfigUploadValue(String(data.upload_interval_value));
          }
          if (typeof data.upload_interval_unit === "string") {
            setConfigUploadUnit(data.upload_interval_unit);
          }
          if (typeof data.upload_daily_time === "string") {
            setConfigUploadTime(data.upload_daily_time);
          }
          if (typeof data.download_interval_value === "number") {
            setConfigDownloadValue(String(data.download_interval_value));
          }
          if (typeof data.download_interval_unit === "string") {
            setConfigDownloadUnit(data.download_interval_unit);
          }
          if (typeof data.download_daily_time === "string") {
            setConfigDownloadTime(data.download_daily_time);
          }
        })
        .catch((err: Error) => setConfigError(err.message))
        .finally(() => setConfigLoading(false));
    };

  const saveConfig = () => {
    setConfigLoading(true);
    setConfigError(null);
    setConfigStatus(null);
    const uploadValueRaw = configUploadValue.trim();
    const uploadValue = uploadValueRaw ? Number.parseFloat(uploadValueRaw) : null;
    if (uploadValueRaw && (Number.isNaN(uploadValue) || uploadValue <= 0)) {
      setConfigLoading(false);
      setConfigError("本地上行间隔必须是大于 0 的数值。");
      return;
    }
    const downloadValueRaw = configDownloadValue.trim();
    const downloadValue = downloadValueRaw ? Number.parseFloat(downloadValueRaw) : null;
    if (downloadValueRaw && (Number.isNaN(downloadValue) || downloadValue <= 0)) {
      setConfigLoading(false);
      setConfigError("云端下行间隔必须是大于 0 的数值。");
      return;
    }
    const uploadTime = configUploadTime.trim();
    if (configUploadUnit === "days" && !isTimeValue(uploadTime)) {
      setConfigLoading(false);
      setConfigError("本地上行设置为按天时必须填写有效时间（HH:MM）。");
      return;
    }
    const downloadTime = configDownloadTime.trim();
    if (configDownloadUnit === "days" && !isTimeValue(downloadTime)) {
      setConfigLoading(false);
      setConfigError("云端下行设置为按天时必须填写有效时间（HH:MM）。");
      return;
    }
    fetch(apiUrl("/config"), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        auth_authorize_url: configAuthorizeUrl.trim() || null,
        auth_token_url: configTokenUrl.trim() || null,
        auth_client_id: configClientId.trim() || null,
        auth_client_secret: configClientSecret.trim() || null,
        auth_redirect_uri: configRedirectUri.trim() || null,
        sync_mode: configSyncMode,
        token_store: configTokenStore,
        upload_interval_value: uploadValue,
        upload_interval_unit: configUploadUnit,
        upload_daily_time: configUploadUnit === "days" ? uploadTime || null : null,
        download_interval_value: downloadValue,
        download_interval_unit: configDownloadUnit,
        download_daily_time: configDownloadUnit === "days" ? downloadTime || null : null
      })
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "保存配置失败");
        }
        return res.json();
      })
      .then(() => {
        setConfigClientSecret("");
        setConfigStatus("已保存");
        loadConfig();
      })
      .catch((err: Error) => setConfigError(err.message))
      .finally(() => setConfigLoading(false));
  };

  const loadTree = () => {
    if (!connected) return;
    setTreeLoading(true);
    setTreeError(null);
    fetch(apiUrl("/drive/tree"))
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "获取目录失败");
        }
        return res.json();
      })
      .then((data) => {
        setTree(data);
      })
      .catch((err: Error) => {
        setTreeError(err.message);
      })
      .finally(() => {
        setTreeLoading(false);
      });
  };

  const loadConflicts = () => {
    setConflictLoading(true);
    setConflictError(null);
    fetch(apiUrl("/conflicts"))
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "获取冲突失败");
        }
        return res.json();
      })
      .then((data) => {
        setConflicts(Array.isArray(data) ? data : []);
      })
      .catch((err: Error) => {
        setConflictError(err.message);
      })
      .finally(() => {
        setConflictLoading(false);
      });
  };

  const resolveConflict = (id: string, action: "use_local" | "use_cloud") => {
    fetch(apiUrl(`/conflicts/${id}/resolve`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action })
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "处理冲突失败");
        }
        return res.json();
      })
      .then(() => loadConflicts())
      .catch((err: Error) => setConflictError(err.message));
  };

  const logout = () => {
    fetch(apiUrl("/auth/logout"), { method: "POST" }).finally(() => {
      setConnected(false);
      setExpiresAt(null);
    });
  };

  useEffect(() => {
    loadConflicts();
  }, []);

  useEffect(() => {
    loadTasks();
  }, []);

  useEffect(() => {
    loadTaskStatus();
    if (tasks.length === 0) {
      return;
    }
    const timer = window.setInterval(loadTaskStatus, 5000);
    return () => window.clearInterval(timer);
  }, [tasks.length]);

  useEffect(() => {
    setTaskUpdateModeMap((prev) => {
      const next = { ...prev };
      tasks.forEach((task) => {
        if (!next[task.id]) {
          next[task.id] = task.update_mode || "auto";
        }
      });
      return next;
    });
    setTaskSyncModeMap((prev) => {
      const next = { ...prev };
      tasks.forEach((task) => {
        if (!next[task.id]) {
          next[task.id] = task.sync_mode || "bidirectional";
        }
      });
      return next;
    });
  }, [tasks]);

  useEffect(() => {
    loadConfig();
  }, []);

  useEffect(() => {
    if (!showTaskModal || !connected) return;
    if (!tree && !treeLoading) {
      loadTree();
    }
  }, [showTaskModal, connected, tree, treeLoading]);

  const syncLogEntries = useMemo(() => {
    return Object.values(taskStatusMap)
      .flatMap((status) =>
        (status.last_files || []).map((file) => ({
          taskId: status.task_id,
          taskName: tasks.find((task) => task.id === status.task_id)?.name || "未命名任务",
          timestamp:
            file.timestamp ??
            status.finished_at ??
            status.started_at ??
            Math.floor(Date.now() / 1000),
          status: file.status,
          path: file.path,
          message: file.message
        }))
      )
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, 200);
  }, [taskStatusMap, tasks]);

  const filteredLogs = useMemo(() => {
    const text = logFilterText.trim().toLowerCase();
    return syncLogEntries.filter((entry) => {
      if (logFilterStatus !== "all" && entry.status !== logFilterStatus) {
        return false;
      }
      if (!text) return true;
      return (
        entry.path.toLowerCase().includes(text) ||
        entry.taskName.toLowerCase().includes(text) ||
        (entry.message || "").toLowerCase().includes(text)
      );
    });
  }, [syncLogEntries, logFilterStatus, logFilterText]);

  useEffect(() => {
    setLogLimit(60);
  }, [logFilterStatus, logFilterText]);

  const today = new Date();
  const todayCount = syncLogEntries.filter((entry) => isSameDay(entry.timestamp, today)).length;
  const lastSync = syncLogEntries[0];
  const enabledTasks = tasks.filter((task) => task.enabled).length;
  const runningTasks = tasks.filter((task) => taskStatusMap[task.id]?.state === "running").length;
  const unresolvedConflicts = conflicts.filter((conflict) => !conflict.resolved).length;

    const navItems: Array<{ id: NavKey; label: string; icon: (props: IconProps) => JSX.Element; badge?: number }> = [
      { id: "dashboard", label: "仪表盘", icon: IconDashboard },
      { id: "tasks", label: "同步任务", icon: IconTasks },
      { id: "logcenter", label: "日志中心", icon: IconConflicts, badge: unresolvedConflicts || undefined },
      { id: "settings", label: "设置", icon: IconSettings }
    ];

    const headerCopy: Record<NavKey, { eyebrow: string; title: string; subtitle: string }> = {
      dashboard: {
        eyebrow: "仪表盘",
        title: "保持本地与云端一致的同步节奏",
        subtitle: "连接状态、任务调度与日志都集中在这里，随时掌握同步进度。"
      },
      tasks: {
        eyebrow: "同步任务",
        title: "让每个同步任务都清晰可控",
        subtitle: "集中管理路径、状态、进度与同步策略，支持快速操作。"
      },
      logcenter: {
        eyebrow: "日志中心",
        title: "用时间线追踪每一次同步",
        subtitle: "统一查看同步日志与冲突处理结果，快速定位问题。"
      },
      settings: {
        eyebrow: "设置",
        title: "配置授权与同步节奏",
        subtitle: "填写应用凭证并调整同步策略，确保授权与调度一致。"
      }
    };
    const activeHeader = headerCopy[activeTab];

  const renderModeIcon = (mode: string) => {
    if (mode === "download_only") {
      return <IconArrowDown className="h-4 w-4" />;
    }
    if (mode === "upload_only") {
      return <IconArrowUp className="h-4 w-4" />;
    }
    return <IconArrowRightLeft className="h-4 w-4" />;
  };

  return (
    <div className="min-h-screen text-slate-100">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 lg:flex-row">
        <aside className="glass-panel flex w-full flex-col gap-6 rounded-3xl p-5 lg:sticky lg:top-6 lg:h-[calc(100vh-3rem)] lg:w-72">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-500/20 text-blue-200">
              <IconArrowRightLeft className="h-5 w-5" />
            </div>
            <div>
              <p className="text-lg font-semibold text-slate-50">LarkSync</p>
              <p className="text-xs text-slate-400">Sync Studio Console</p>
            </div>
          </div>

          <nav className="grid gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  className={`flex items-center justify-between rounded-2xl border px-3 py-2 text-sm transition ${
                    isActive
                      ? "border-blue-400/40 bg-blue-500/15 text-blue-100"
                      : "border-transparent text-slate-300 hover:border-slate-700 hover:bg-white/5"
                  }`}
                  onClick={() => setActiveTab(item.id)}
                  type="button"
                >
                  <span className="flex items-center gap-3">
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </span>
                  {item.badge ? (
                    <span className="rounded-full bg-rose-500/20 px-2 py-0.5 text-xs font-semibold text-rose-200">
                      {item.badge}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </nav>

          <div className="soft-panel rounded-2xl p-4">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">连接状态</p>
            <div className="mt-3 flex items-center justify-between">
              <StatusPill
                label={loading ? "检测中" : connected ? "已连接" : "未连接"}
                tone={loading ? "info" : connected ? "success" : "danger"}
                dot
              />
              <span className="text-xs text-slate-400">
                {expiresAt ? formatTimestamp(expiresAt) : "—"}
              </span>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <a
                className="inline-flex items-center justify-center rounded-full bg-blue-500 px-4 py-2 text-xs font-semibold text-white transition hover:bg-blue-400"
                href={loginUrl}
              >
                {connected ? "重新授权" : "连接飞书"}
              </a>
              <button
                className="inline-flex items-center justify-center rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
                onClick={logout}
                type="button"
              >
                断开连接
              </button>
            </div>
          </div>

          <div className="soft-panel rounded-2xl p-4 text-xs text-slate-400">
              <p className="font-semibold text-slate-200">当前策略</p>
              <ul className="mt-3 space-y-2">
                <li>
                  本地 {"->"} 云端：每 {formatIntervalLabel(configUploadValue || "2", configUploadUnit, configUploadTime)}
                </li>
                <li>
                  云端 {"->"} 本地：每 {formatIntervalLabel(configDownloadValue || "1", configDownloadUnit, configDownloadTime)}
                </li>
                <li>默认同步：{modeLabels[configSyncMode] || configSyncMode}</li>
              </ul>
            </div>
        </aside>

        <main className="flex-1 space-y-6">
          <header className="glass-panel flex flex-wrap items-center justify-between gap-4 rounded-3xl p-6">
            <div className="space-y-2">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-400">{activeHeader.eyebrow}</p>
              <p className="text-xl font-semibold text-slate-50">{activeHeader.title}</p>
              <p className="text-sm text-slate-400">
                {activeHeader.subtitle}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <StatusPill
                label={connected ? "已连接" : loading ? "检测中" : "未连接"}
                tone={connected ? "success" : loading ? "info" : "danger"}
                dot
              />
              <button
                className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-semibold transition ${
                  globalPaused
                    ? "bg-amber-500/20 text-amber-200"
                    : "bg-emerald-500/20 text-emerald-200"
                }`}
                onClick={() => setGlobalPaused((prev) => !prev)}
                type="button"
              >
                {globalPaused ? (
                  <IconPlay className="h-3.5 w-3.5" />
                ) : (
                  <IconPause className="h-3.5 w-3.5" />
                )}
                {globalPaused ? "已暂停" : "运行中"}
              </button>
              <button
                className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
                onClick={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))}
                type="button"
              >
                {theme === "dark" ? "明亮模式" : "深色模式"}
              </button>
            </div>
          </header>

          {activeTab === "dashboard" ? (
            <section className="space-y-6 fade-up">
              {!connected ? (
                <div className="glass-panel rounded-3xl p-6">
                  <h2 className="text-xl font-semibold text-slate-50">连接飞书账号</h2>
                  <p className="mt-2 text-sm text-slate-400">
                    首次使用请完成 OAuth 授权。未配置参数时请先前往设置页填写 App ID 与 Secret。
                  </p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <a
                      className="inline-flex items-center gap-2 rounded-full bg-blue-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-blue-400"
                      href={loginUrl}
                    >
                      <IconCloud className="h-4 w-4" />
                      连接飞书
                    </a>
                    <button
                      className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-5 py-2 text-sm font-semibold text-slate-200 transition hover:border-slate-500"
                      onClick={() => setActiveTab("settings")}
                      type="button"
                    >
                      <IconSettings className="h-4 w-4" />
                      打开配置
                    </button>
                  </div>
                </div>
              ) : null}

              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <StatCard
                  label="今日同步"
                  value={`${todayCount}`}
                  hint="按日志统计"
                  tone="success"
                  icon={<IconRefresh className="h-4 w-4" />}
                />
                <StatCard
                  label="启用任务"
                  value={`${enabledTasks}`}
                  hint={runningTasks ? `运行中 ${runningTasks} 个` : "当前无运行任务"}
                  tone="info"
                  icon={<IconTasks className="h-4 w-4" />}
                />
                <StatCard
                  label="最近同步"
                  value={lastSync ? formatShortTime(lastSync.timestamp) : "暂无"}
                  hint={lastSync ? lastSync.taskName : "等待任务触发"}
                  tone="neutral"
                  icon={<IconArrowRightLeft className="h-4 w-4" />}
                />
                <StatCard
                  label="待处理冲突"
                  value={`${unresolvedConflicts}`}
                  hint={unresolvedConflicts ? "请尽快处理" : "暂无冲突"}
                  tone={unresolvedConflicts ? "warning" : "neutral"}
                  icon={<IconConflicts className="h-4 w-4" />}
                />
              </div>

              <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
                <div className="soft-panel rounded-3xl p-6">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h2 className="text-lg font-semibold text-slate-50">活跃任务</h2>
                      <p className="mt-1 text-xs text-slate-400">
                        展示最近活跃的同步任务与状态摘要。
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
                        onClick={loadTasks}
                        type="button"
                      >
                        <IconRefresh className="h-3.5 w-3.5" />
                        刷新
                      </button>
                      <button
                        className="inline-flex items-center gap-2 rounded-full bg-blue-500 px-4 py-2 text-xs font-semibold text-white transition hover:bg-blue-400"
                        onClick={() => setActiveTab("tasks")}
                        type="button"
                      >
                        <IconTasks className="h-3.5 w-3.5" />
                        管理任务
                      </button>
                    </div>
                  </div>
                  <div className="mt-5 space-y-4">
                    {taskLoading ? (
                      <p className="text-sm text-slate-400">加载任务中...</p>
                    ) : tasks.length === 0 ? (
                      <p className="text-sm text-slate-400">暂无同步任务，请先创建。</p>
                    ) : (
                      tasks.slice(0, 4).map((task) => {
                        const status = taskStatusMap[task.id];
                        const isRunning = status?.state === "running";
                        const stateKey = !task.enabled ? "paused" : status?.state || "idle";
                        const progress =
                          status && status.total_files > 0
                            ? Math.round((status.completed_files / status.total_files) * 100)
                            : null;
                        return (
                          <div
                            key={task.id}
                            className="rounded-2xl border border-slate-800 bg-white/5 p-4"
                          >
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div className="space-y-1">
                                <p className="text-sm font-semibold text-slate-100">
                                  {task.name || task.local_path}
                                </p>
                                <p className="text-xs text-slate-400">
                                  本地：{task.local_path}
                                </p>
                                <p className="text-xs text-slate-500">
                                  云端：{task.cloud_folder_token}
                                </p>
                              </div>
                              <StatusPill
                                label={stateLabels[stateKey] || stateKey}
                                tone={stateTones[stateKey] || "neutral"}
                              />
                            </div>
                            <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-300">
                              <span className="inline-flex items-center gap-2">
                                {renderModeIcon(task.sync_mode)}
                                {modeLabels[task.sync_mode] || task.sync_mode}
                              </span>
                              <span className="text-slate-500">|</span>
                              <span>更新：{updateModeLabels[task.update_mode || "auto"]}</span>
                              {isRunning ? <span className="text-emerald-200">同步中</span> : null}
                            </div>
                            {progress !== null ? (
                              <div className="mt-3">
                                <div className="flex items-center justify-between text-xs text-slate-400">
                                  <span>进度 {progress}%</span>
                                  <span>
                                    {status?.completed_files ?? 0}/{status?.total_files ?? 0}
                                  </span>
                                </div>
                                <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-800">
                                  <div
                                    className="h-full rounded-full bg-emerald-400"
                                    style={{ width: `${progress}%` }}
                                  />
                                </div>
                              </div>
                            ) : null}
                            {status?.last_error ? (
                              <p className="mt-3 text-xs text-rose-300">
                                最近错误：{status.last_error}
                              </p>
                            ) : null}
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>

                <div className="soft-panel rounded-3xl p-6">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h2 className="text-lg font-semibold text-slate-50">同步日志</h2>
                      <p className="mt-1 text-xs text-slate-400">
                        实时记录任务与文件动作。
                      </p>
                    </div>
                    <button
                      className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
                      onClick={loadTaskStatus}
                      type="button"
                    >
                      <IconRefresh className="h-3.5 w-3.5" />
                      刷新
                    </button>
                  </div>
                  <div className="mt-5 max-h-96 space-y-3 overflow-auto pr-2">
                    {syncLogEntries.length === 0 ? (
                      <p className="text-sm text-slate-400">暂无同步日志。</p>
                    ) : (
                      syncLogEntries.slice(0, 12).map((entry, index) => (
                        <div
                          key={`${entry.taskId}-${entry.timestamp}-${index}`}
                          className="rounded-2xl border border-slate-800 bg-white/5 p-3"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div className="space-y-1">
                              <p className="text-xs text-slate-400">
                                {formatTimestamp(entry.timestamp)}
                              </p>
                              <p className="text-sm text-slate-200">
                                {entry.taskName}
                              </p>
                            </div>
                            <StatusPill
                              label={statusLabelMap[entry.status] || entry.status}
                              tone={entry.status === "failed" ? "danger" : entry.status === "skipped" ? "warning" : "success"}
                            />
                          </div>
                          <p className="mt-2 text-xs text-slate-400 break-all">{entry.path}</p>
                          {entry.message ? (
                            <p className="mt-2 text-xs text-slate-500">{entry.message}</p>
                          ) : null}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </section>
          ) : null}
          {activeTab === "tasks" ? (
            <section className="space-y-6 fade-up">
              <div className="soft-panel rounded-3xl p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-slate-50">同步任务</h2>
                    <p className="mt-1 text-xs text-slate-400">
                      管理任务的同步模式、更新策略与执行状态。
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
                      onClick={loadTasks}
                      type="button"
                    >
                      <IconRefresh className="h-3.5 w-3.5" />
                      刷新
                    </button>
                    <button
                      className="inline-flex items-center gap-2 rounded-full bg-blue-500 px-4 py-2 text-xs font-semibold text-white transition hover:bg-blue-400"
                      onClick={() => setShowTaskModal(true)}
                      type="button"
                    >
                      <IconPlus className="h-3.5 w-3.5" />
                      新建任务
                    </button>
                  </div>
                </div>
                {taskError ? (
                  <p className="mt-4 text-sm text-rose-300">错误：{taskError}</p>
                ) : null}
              </div>

              <div className="space-y-4">
                {taskLoading ? (
                  <p className="text-sm text-slate-400">任务加载中...</p>
                ) : tasks.length === 0 ? (
                  <p className="text-sm text-slate-400">暂无同步任务，请点击“新建任务”。</p>
                ) : (
                  tasks.map((task) => {
                    const status = taskStatusMap[task.id];
                    const stateKey = !task.enabled ? "paused" : status?.state || "idle";
                    const progress =
                      status && status.total_files > 0
                        ? Math.round((status.completed_files / status.total_files) * 100)
                        : null;
                    const isRunning = status?.state === "running";
                    const isExpanded = Boolean(expandedTasks[task.id]);
                    const lastSyncTime = status?.finished_at ?? status?.started_at ?? null;
                    return (
                      <div
                        key={task.id}
                        className="soft-panel rounded-3xl border border-slate-800/60 p-6"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-4">
                          <div className="space-y-2">
                            <div className="flex flex-wrap items-center gap-3">
                              <StatusPill
                                label={stateLabels[stateKey] || stateKey}
                                tone={stateTones[stateKey] || "neutral"}
                                dot
                              />
                              <p className="text-lg font-semibold text-slate-50">
                                {task.name || "未命名任务"}
                              </p>
                            </div>
                            <p className="text-xs text-slate-400">任务 ID：{task.id}</p>
                          </div>
                          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                            <span className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-3 py-1">
                              {renderModeIcon(task.sync_mode)}
                              {modeLabels[task.sync_mode] || task.sync_mode}
                            </span>
                            <span className="rounded-full border border-slate-700 px-3 py-1">
                              更新：{updateModeLabels[task.update_mode || "auto"]}
                            </span>
                          </div>
                        </div>

                        <div className="mt-4 rounded-2xl border border-slate-800 bg-white/5 p-4">
                          <div className="grid gap-4 lg:grid-cols-[1fr_auto_1fr]">
                            <div className="flex items-center gap-3">
                              <div className="rounded-2xl bg-emerald-500/20 p-2 text-emerald-200">
                                <IconFolder className="h-4 w-4" />
                              </div>
                              <div className="min-w-0">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                                  本地目录
                                </p>
                                <p className="mt-1 truncate font-mono text-sm text-slate-200">
                                  {task.local_path}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center justify-center">
                              <span className="rounded-full border border-slate-700 bg-white/5 p-2 text-slate-300">
                                {renderModeIcon(task.sync_mode)}
                              </span>
                            </div>
                            <div className="flex items-center justify-end gap-3 text-right">
                              <div className="min-w-0">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                                  云端目录
                                </p>
                                <p className="mt-1 truncate font-mono text-sm text-slate-200">
                                  {task.cloud_folder_token}
                                </p>
                              </div>
                              <div className="rounded-2xl bg-blue-500/15 p-2 text-blue-200">
                                <IconCloud className="h-4 w-4" />
                              </div>
                            </div>
                          </div>
                          {task.base_path ? (
                            <p className="mt-3 text-xs text-slate-500">
                              base_path：{task.base_path}
                            </p>
                          ) : null}
                        </div>

                        <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-slate-400">
                          <span>最近同步：{lastSyncTime ? formatTimestamp(lastSyncTime) : "暂无"}</span>
                          {status ? (
                            <span>
                              完成 {status.completed_files}/{status.total_files}，失败{" "}
                              {status.failed_files}，跳过 {status.skipped_files}
                            </span>
                          ) : null}
                          {progress !== null ? <span>完成率：{progress}%</span> : null}
                        </div>

                        {status?.last_error ? (
                          <p className="mt-2 text-xs text-rose-300">
                            错误：{status.last_error}
                          </p>
                        ) : null}

                        {progress !== null ? (
                          <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
                            <div
                              className="h-full rounded-full bg-emerald-400"
                              style={{ width: `${progress}%` }}
                            />
                          </div>
                        ) : null}

                        <div className="mt-4 flex flex-wrap items-center gap-2">
                          <button
                            className="inline-flex items-center gap-2 rounded-full bg-emerald-500/20 px-4 py-2 text-xs font-semibold text-emerald-200 transition hover:bg-emerald-500/30 disabled:cursor-not-allowed disabled:opacity-60"
                            onClick={() => runTask(task)}
                            disabled={isRunning}
                            type="button"
                          >
                            <IconPlay className="h-3.5 w-3.5" />
                            {isRunning ? "同步中" : "立即同步"}
                          </button>
                          <button
                            className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
                            onClick={() => toggleTask(task)}
                            type="button"
                          >
                            {task.enabled ? "停用" : "启用"}
                          </button>
                          <button
                            className="inline-flex items-center gap-2 rounded-full border border-rose-400/40 px-4 py-2 text-xs font-semibold text-rose-200 transition hover:border-rose-400"
                            onClick={() => deleteTask(task)}
                            type="button"
                          >
                            <IconTrash className="h-3.5 w-3.5" />
                            删除
                          </button>
                          <button
                            className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
                            onClick={() =>
                              setExpandedTasks((prev) => ({
                                ...prev,
                                [task.id]: !prev[task.id]
                              }))
                            }
                            type="button"
                          >
                            {isExpanded ? "收起管理" : "任务管理"}
                          </button>
                        </div>

                        {isExpanded ? (
                          <div className="mt-4 grid gap-4 lg:grid-cols-2">
                            <div className="rounded-2xl border border-slate-800 bg-white/5 p-4">
                              <p className="text-xs uppercase tracking-[0.3em] text-slate-400">同步模式</p>
                              <div className="mt-3 flex flex-wrap items-center gap-2">
                                <select
                                  className="rounded-full border border-slate-700 bg-transparent px-4 py-2 text-xs text-slate-200"
                                  value={taskSyncModeMap[task.id] || task.sync_mode}
                                  onChange={(event) =>
                                    setTaskSyncModeMap((prev) => ({
                                      ...prev,
                                      [task.id]: event.target.value
                                    }))
                                  }
                                >
                                  <option value="bidirectional">双向同步</option>
                                  <option value="download_only">仅下载</option>
                                  <option value="upload_only">仅上传</option>
                                </select>
                                <button
                                  className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
                                  onClick={() => updateTaskSyncMode(task, taskSyncModeMap[task.id] || task.sync_mode)}
                                  type="button"
                                >
                                  应用同步模式
                                </button>
                              </div>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-white/5 p-4">
                              <p className="text-xs uppercase tracking-[0.3em] text-slate-400">更新模式</p>
                              <div className="mt-3 flex flex-wrap items-center gap-2">
                                <select
                                  className="rounded-full border border-slate-700 bg-transparent px-4 py-2 text-xs text-slate-200"
                                  value={taskUpdateModeMap[task.id] || task.update_mode || "auto"}
                                  onChange={(event) =>
                                    setTaskUpdateModeMap((prev) => ({
                                      ...prev,
                                      [task.id]: event.target.value
                                    }))
                                  }
                                >
                                  <option value="auto">自动更新</option>
                                  <option value="partial">局部更新</option>
                                  <option value="full">全量覆盖</option>
                                </select>
                                <button
                                  className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
                                  onClick={() => updateTaskMode(task, taskUpdateModeMap[task.id] || task.update_mode || "auto")}
                                  type="button"
                                >
                                  应用更新模式
                                </button>
                              </div>
                            </div>
                          </div>
                        ) : null}
                      </div>
                    );
                  })
                )}
              </div>
            </section>
          ) : null}
          {activeTab === "logcenter" ? (
            <section className="space-y-6 fade-up">
              <div className="soft-panel rounded-3xl p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-slate-50">日志中心</h2>
                    <p className="mt-1 text-xs text-slate-400">
                      同步日志与冲突处理统一管理。
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      className={`rounded-full border px-4 py-2 text-xs font-semibold transition ${
                        logTab === "logs"
                          ? "border-blue-400/40 bg-blue-500/15 text-blue-100"
                          : "border-slate-700 text-slate-200 hover:border-slate-500"
                      }`}
                      onClick={() => setLogTab("logs")}
                      type="button"
                    >
                      同步日志
                    </button>
                    <button
                      className={`rounded-full border px-4 py-2 text-xs font-semibold transition ${
                        logTab === "conflicts"
                          ? "border-amber-400/40 bg-amber-500/15 text-amber-200"
                          : "border-slate-700 text-slate-200 hover:border-slate-500"
                      }`}
                      onClick={() => setLogTab("conflicts")}
                      type="button"
                    >
                      冲突管理
                    </button>
                  </div>
                </div>
              </div>

              {logTab === "logs" ? (
                <div className="soft-panel rounded-3xl p-6">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h3 className="text-lg font-semibold text-slate-50">同步日志流</h3>
                      <p className="mt-1 text-xs text-slate-400">
                        支持筛选、搜索与批量查看。
                      </p>
                    </div>
                    <button
                      className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
                      onClick={loadTaskStatus}
                      type="button"
                    >
                      <IconRefresh className="h-3.5 w-3.5" />
                      刷新日志
                    </button>
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-[1.2fr_0.6fr_0.6fr]">
                    <input
                      className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                      placeholder="搜索任务名、路径或错误信息"
                      value={logFilterText}
                      onChange={(event) => setLogFilterText(event.target.value)}
                    />
                    <select
                      className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                      value={logFilterStatus}
                      onChange={(event) => setLogFilterStatus(event.target.value)}
                    >
                      <option value="all">全部状态</option>
                      <option value="downloaded">下载</option>
                      <option value="uploaded">上传</option>
                      <option value="success">成功</option>
                      <option value="failed">失败</option>
                      <option value="skipped">跳过</option>
                      <option value="started">开始</option>
                    </select>
                    <button
                      className="rounded-full border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-slate-500"
                      onClick={() => setLogLimit(60)}
                      type="button"
                    >
                      重置视图
                    </button>
                  </div>
                  <div className="mt-5 space-y-3">
                    {filteredLogs.length === 0 ? (
                      <p className="text-sm text-slate-400">暂无匹配日志。</p>
                    ) : (
                      filteredLogs.slice(0, logLimit).map((entry, index) => (
                        <div
                          key={`${entry.taskId}-${entry.timestamp}-${index}`}
                          className="rounded-2xl border border-slate-800 bg-white/5 p-4"
                        >
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div className="space-y-1">
                              <p className="text-xs text-slate-400">
                                {formatTimestamp(entry.timestamp)}
                              </p>
                              <p className="text-sm font-semibold text-slate-200">
                                {entry.taskName}
                              </p>
                              <p className="text-xs text-slate-400 break-all">{entry.path}</p>
                            </div>
                            <StatusPill
                              label={statusLabelMap[entry.status] || entry.status}
                              tone={
                                entry.status === "failed"
                                  ? "danger"
                                  : entry.status === "skipped"
                                    ? "warning"
                                    : "success"
                              }
                            />
                          </div>
                          {entry.message ? (
                            <p className="mt-3 text-xs text-slate-500">{entry.message}</p>
                          ) : null}
                        </div>
                      ))
                    )}
                  </div>
                  {filteredLogs.length > logLimit ? (
                    <div className="mt-4 flex justify-center">
                      <button
                        className="rounded-full border border-slate-700 px-5 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
                        onClick={() => setLogLimit((prev) => prev + 60)}
                        type="button"
                      >
                        加载更多
                      </button>
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="soft-panel rounded-3xl p-6">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="text-lg font-semibold text-slate-50">冲突管理</h3>
                        <p className="mt-1 text-xs text-slate-400">
                          处理云端与本地同时修改产生的冲突。
                        </p>
                      </div>
                      <button
                        className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
                        onClick={loadConflicts}
                        disabled={conflictLoading}
                        type="button"
                      >
                        <IconRefresh className="h-3.5 w-3.5" />
                        {conflictLoading ? "加载中..." : "刷新"}
                      </button>
                    </div>
                    {conflictError ? (
                      <p className="mt-4 text-sm text-rose-300">加载失败：{conflictError}</p>
                    ) : null}
                  </div>

                  {conflicts.length === 0 ? (
                    <p className="text-sm text-slate-400">暂无冲突记录。</p>
                  ) : (
                    conflicts.map((conflict) => (
                      <div
                        key={conflict.id}
                        className="soft-panel rounded-3xl border border-slate-800/60 p-6"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-4">
                          <div className="space-y-1">
                            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">本地路径</p>
                            <p className="text-sm text-slate-200">{conflict.local_path}</p>
                            <p className="text-xs text-slate-500">云端 token：{conflict.cloud_token}</p>
                            <p className="text-xs text-slate-500">
                              哈希：{conflict.local_hash.slice(0, 8)} / {conflict.db_hash.slice(0, 8)}
                            </p>
                          </div>
                          <StatusPill
                            label={conflict.resolved ? "已处理" : "待处理"}
                            tone={conflict.resolved ? "success" : "warning"}
                          />
                        </div>
                        <div className="mt-4 grid gap-4 lg:grid-cols-2">
                          <div>
                            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">本地版本</p>
                            <pre className="mt-2 max-h-56 overflow-auto rounded-2xl border border-slate-800 bg-black/30 p-3 text-xs text-slate-300">
                              {conflict.local_preview || "暂无本地预览。"}
                            </pre>
                          </div>
                          <div>
                            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">云端版本</p>
                            <pre className="mt-2 max-h-56 overflow-auto rounded-2xl border border-slate-800 bg-black/30 p-3 text-xs text-slate-300">
                              {conflict.cloud_preview || "暂无云端预览。"}
                            </pre>
                          </div>
                        </div>
                        <div className="mt-4 flex flex-wrap gap-3">
                          <button
                            className="rounded-full bg-emerald-500/20 px-4 py-2 text-xs font-semibold text-emerald-200 transition hover:bg-emerald-500/30 disabled:cursor-not-allowed disabled:opacity-60"
                            disabled={conflict.resolved}
                            onClick={() => resolveConflict(conflict.id, "use_local")}
                            type="button"
                          >
                            使用本地
                          </button>
                          <button
                            className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                            disabled={conflict.resolved}
                            onClick={() => resolveConflict(conflict.id, "use_cloud")}
                            type="button"
                          >
                            使用云端
                          </button>
                          {conflict.resolved ? (
                            <span className="self-center text-xs text-slate-400">
                              已处理：{conflict.resolved_action}
                            </span>
                          ) : null}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </section>
          ) : null}
          
          {activeTab === "settings" ? (
            <section className="space-y-6 fade-up">
              <div className="soft-panel rounded-3xl p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-slate-50">OAuth 配置</h2>
                    <p className="mt-1 text-xs text-slate-400">
                      仅填写 App ID / Secret / Redirect URI 即可完成授权。
                    </p>
                  </div>
                </div>
                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  <input
                    className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                    placeholder="App ID"
                    value={configClientId}
                    onChange={(event) => setConfigClientId(event.target.value)}
                  />
                  <input
                    className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                    placeholder="App Secret（保存后自动清空）"
                    type="password"
                    value={configClientSecret}
                    onChange={(event) => setConfigClientSecret(event.target.value)}
                  />
                  <input
                    className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200 md:col-span-2"
                    placeholder="Redirect URI"
                    value={configRedirectUri}
                    onChange={(event) => setConfigRedirectUri(event.target.value)}
                  />
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <button
                    className="rounded-full bg-blue-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-blue-400 disabled:cursor-not-allowed disabled:opacity-60"
                    onClick={saveConfig}
                    disabled={configLoading}
                    type="button"
                  >
                    {configLoading ? "保存中..." : "保存配置"}
                  </button>
                  <button
                    className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
                    onClick={() => setShowAuthAdvanced((prev) => !prev)}
                    type="button"
                  >
                    {showAuthAdvanced ? "收起可选设置" : "展开可选设置"}
                  </button>
                  {configStatus ? <span className="text-sm text-emerald-300">{configStatus}</span> : null}
                  {configError ? <span className="text-sm text-rose-300">错误：{configError}</span> : null}
                </div>
                {showAuthAdvanced ? (
                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <input
                      className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                      placeholder="授权地址 auth_authorize_url（默认可空）"
                      value={configAuthorizeUrl}
                      onChange={(event) => setConfigAuthorizeUrl(event.target.value)}
                    />
                    <input
                      className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                      placeholder="Token 地址 auth_token_url（默认可空）"
                      value={configTokenUrl}
                      onChange={(event) => setConfigTokenUrl(event.target.value)}
                    />
                    <select
                      className="rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                      value={configTokenStore}
                      onChange={(event) => setConfigTokenStore(event.target.value)}
                    >
                      <option value="keyring">密钥库存储</option>
                      <option value="file">文件存储</option>
                    </select>
                  </div>
                ) : null}
              </div>

              <div className="soft-panel rounded-3xl p-6">
                <div>
                  <h2 className="text-lg font-semibold text-slate-50">同步策略</h2>
                  <p className="mt-1 text-xs text-slate-400">
                    默认：本地上行每 {formatIntervalLabel(configUploadValue || "2", configUploadUnit, configUploadTime)}，云端下行每{" "}
                    {formatIntervalLabel(configDownloadValue || "1", configDownloadUnit, configDownloadTime)}。
                  </p>
                </div>
                <div className="mt-5 grid gap-4 lg:grid-cols-3">
                  <div className="rounded-2xl border border-slate-800 bg-white/5 p-4">
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-400">本地上行</p>
                    <div className="mt-3 grid gap-2 md:grid-cols-[1fr_auto]">
                      <input
                        className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                        type="number"
                        min="0"
                        step="0.5"
                        placeholder="间隔值"
                        value={configUploadValue}
                        onChange={(event) => setConfigUploadValue(event.target.value)}
                      />
                      <select
                        className="rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                        value={configUploadUnit}
                        onChange={(event) => setConfigUploadUnit(event.target.value)}
                      >
                        <option value="seconds">秒</option>
                        <option value="hours">小时</option>
                        <option value="days">天</option>
                      </select>
                    </div>
                    {configUploadUnit === "days" ? (
                      <input
                        className="mt-3 w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                        type="time"
                        value={configUploadTime}
                        onChange={(event) => setConfigUploadTime(event.target.value)}
                      />
                    ) : null}
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-white/5 p-4">
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-400">云端下行</p>
                    <div className="mt-3 grid gap-2 md:grid-cols-[1fr_auto]">
                      <input
                        className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                        type="number"
                        min="0"
                        step="0.5"
                        placeholder="间隔值"
                        value={configDownloadValue}
                        onChange={(event) => setConfigDownloadValue(event.target.value)}
                      />
                      <select
                        className="rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                        value={configDownloadUnit}
                        onChange={(event) => setConfigDownloadUnit(event.target.value)}
                      >
                        <option value="seconds">秒</option>
                        <option value="hours">小时</option>
                        <option value="days">天</option>
                      </select>
                    </div>
                    {configDownloadUnit === "days" ? (
                      <input
                        className="mt-3 w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                        type="time"
                        value={configDownloadTime}
                        onChange={(event) => setConfigDownloadTime(event.target.value)}
                      />
                    ) : null}
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-white/5 p-4">
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-400">默认同步模式</p>
                    <select
                      className="mt-3 w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                      value={configSyncMode}
                      onChange={(event) => setConfigSyncMode(event.target.value)}
                    >
                      <option value="bidirectional">双向同步</option>
                      <option value="download_only">仅下载</option>
                      <option value="upload_only">仅上传</option>
                    </select>
                  </div>
                </div>
              </div>

              
            </section>
          ) : null}

        </main>
      </div>

      {showTaskModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[color:var(--overlay)] px-4 py-6">
          <div className="max-h-[90vh] w-full max-w-4xl overflow-auto rounded-3xl bg-[color:var(--panel-strong)] p-6 text-slate-100 shadow-2xl">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold">新建同步任务</h2>
                <p className="mt-1 text-xs text-slate-400">依次选择本地目录、云端目录与同步策略。</p>
              </div>
              <button
                className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
                onClick={() => setShowTaskModal(false)}
                type="button"
              >
                关闭
              </button>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-slate-800 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">步骤 1</p>
                <p className="mt-2 text-sm font-semibold text-slate-200">选择本地目录</p>
                <p className="mt-2 text-xs text-slate-400">用于监听与写入文件。</p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">步骤 2</p>
                <p className="mt-2 text-sm font-semibold text-slate-200">选择云端目录</p>
                <p className="mt-2 text-xs text-slate-400">用于同步的飞书文件夹。</p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">步骤 3</p>
                <p className="mt-2 text-sm font-semibold text-slate-200">设置同步策略</p>
                <p className="mt-2 text-xs text-slate-400">选择模式与更新策略。</p>
              </div>
            </div>

            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <div className="space-y-4">
                <input
                  className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                  placeholder="任务名称（可选）"
                  value={taskName}
                  onChange={(event) => setTaskName(event.target.value)}
                />
                <div className="space-y-2">
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-400">本地目录</p>
                  <div className="flex gap-2">
                    <input
                      className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                      placeholder="请选择本地目录"
                      value={taskLocalPath}
                      onChange={(event) => setTaskLocalPath(event.target.value)}
                    />
                    <button
                      className="rounded-2xl border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
                      onClick={pickLocalFolder}
                      type="button"
                    >
                      {folderPickLoading ? "选择中" : "选择"}
                    </button>
                  </div>
                  {folderPickError ? <p className="text-xs text-rose-300">{folderPickError}</p> : null}
                </div>
                <input
                  className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                  placeholder="base_path（可选，默认本地目录）"
                  value={taskBasePath}
                  onChange={(event) => setTaskBasePath(event.target.value)}
                />
                <div className="grid gap-3 md:grid-cols-2">
                  <select
                    className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                    value={taskSyncMode}
                    onChange={(event) => setTaskSyncMode(event.target.value)}
                  >
                    <option value="bidirectional">双向同步</option>
                    <option value="download_only">仅下载</option>
                    <option value="upload_only">仅上传</option>
                  </select>
                  <select
                    className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                    value={taskUpdateMode}
                    onChange={(event) => setTaskUpdateMode(event.target.value)}
                  >
                    <option value="auto">更新模式：自动</option>
                    <option value="partial">更新模式：局部</option>
                    <option value="full">更新模式：全量</option>
                  </select>
                </div>
                <label className="flex items-center gap-2 text-sm text-slate-200">
                  <input
                    type="checkbox"
                    checked={taskEnabled}
                    onChange={(event) => setTaskEnabled(event.target.checked)}
                  />
                  创建后立即启用
                </label>
                {selectedCloud ? (
                  <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-200">
                    已选择：{selectedCloud.path} ({selectedCloud.token})
                  </div>
                ) : null}
                {taskError ? <p className="text-sm text-rose-300">错误：{taskError}</p> : null}
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-400">云端目录</p>
                  <button
                    className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
                    onClick={loadTree}
                    type="button"
                  >
                    <IconRefresh className="h-3.5 w-3.5" />
                    刷新
                  </button>
                </div>
                <div className="max-h-[420px] overflow-auto rounded-2xl border border-slate-800 bg-black/30 p-4">
                  {treeLoading ? (
                    <p className="text-sm text-slate-400">目录加载中...</p>
                  ) : treeError ? (
                    <p className="text-sm text-rose-300">{treeError}</p>
                  ) : tree ? (
                    <ul className="space-y-3">
                      <TreeNode
                        node={tree}
                        selectable
                        selectedToken={taskCloudToken}
                        onSelect={selectCloudFolder}
                      />
                    </ul>
                  ) : (
                    <p className="text-sm text-slate-400">暂无目录数据，请先刷新。</p>
                  )}
                </div>
              </div>
            </div>

            <div className="mt-6 flex flex-wrap justify-end gap-3">
              <button
                className="rounded-full border border-slate-700 px-5 py-2 text-sm font-semibold text-slate-200 transition hover:border-slate-500"
                onClick={() => setShowTaskModal(false)}
                type="button"
              >
                取消
              </button>
              <button
                className="rounded-full bg-blue-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-blue-400"
                onClick={createTask}
                type="button"
              >
                创建任务
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
