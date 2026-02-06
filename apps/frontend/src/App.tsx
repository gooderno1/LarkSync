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

type WatchEvent = {
  event_type: string;
  src_path: string;
  dest_path?: string | null;
  timestamp: number;
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

type NavKey = "dashboard" | "tasks" | "conflicts" | "settings" | "about";

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

const IconInfo = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5" />
    <path d="M12 7h.01" />
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

  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [expiresAt, setExpiresAt] = useState<number | null>(null);
  const [tree, setTree] = useState<DriveNode | null>(null);
  const [treeLoading, setTreeLoading] = useState(false);
  const [treeError, setTreeError] = useState<string | null>(null);
  const [watchPath, setWatchPath] = useState("");
  const [watcherRunning, setWatcherRunning] = useState(false);
  const [watcherError, setWatcherError] = useState<string | null>(null);
  const [events, setEvents] = useState<WatchEvent[]>([]);
  const [wsStatus, setWsStatus] = useState<"connecting" | "open" | "closed">(
    "connecting"
  );
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
  const [uploadDocumentId, setUploadDocumentId] = useState("");
  const [uploadMarkdownPath, setUploadMarkdownPath] = useState("");
  const [uploadTaskId, setUploadTaskId] = useState("");
  const [uploadBasePath, setUploadBasePath] = useState("");
  const [uploadUpdateMode, setUploadUpdateMode] = useState("auto");
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [configAuthorizeUrl, setConfigAuthorizeUrl] = useState("");
  const [configTokenUrl, setConfigTokenUrl] = useState("");
  const [configClientId, setConfigClientId] = useState("");
  const [configClientSecret, setConfigClientSecret] = useState("");
  const [configRedirectUri, setConfigRedirectUri] = useState("");
  const [configScopes, setConfigScopes] = useState("");
  const [configSyncMode, setConfigSyncMode] = useState("bidirectional");
  const [configTokenStore, setConfigTokenStore] = useState("keyring");
  const [configUploadInterval, setConfigUploadInterval] = useState("2");
  const [configDownloadTime, setConfigDownloadTime] = useState("01:00");
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
    fetch(apiUrl("/watcher/status"))
      .then((res) => res.json())
      .then((data) => {
        setWatcherRunning(Boolean(data.running));
        if (data.path) {
          setWatchPath(data.path);
        }
      })
      .catch(() => {
        setWatcherRunning(false);
      });
  }, []);

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(
      `${protocol}://${window.location.host}${apiUrl("/ws/events")}`
    );
    setWsStatus("connecting");

    socket.onopen = () => setWsStatus("open");
    socket.onclose = () => setWsStatus("closed");
    socket.onerror = () => setWsStatus("closed");
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as WatchEvent;
        setEvents((prev) => [payload, ...prev].slice(0, 50));
      } catch {
        // ignore malformed payload
      }
    };

    return () => {
      socket.close();
    };
  }, []);

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
        setConfigScopes(Array.isArray(data.auth_scopes) ? data.auth_scopes.join(", ") : "");
        setConfigSyncMode(data.sync_mode || "bidirectional");
        setConfigTokenStore(data.token_store || "keyring");
        if (typeof data.upload_interval_seconds === "number") {
          setConfigUploadInterval(String(data.upload_interval_seconds));
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
    const scopes = configScopes
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    const uploadIntervalRaw = configUploadInterval.trim();
    const uploadInterval = uploadIntervalRaw ? Number.parseFloat(uploadIntervalRaw) : null;
    if (uploadIntervalRaw && (Number.isNaN(uploadInterval) || uploadInterval <= 0)) {
      setConfigLoading(false);
      setConfigError("上传间隔必须是大于 0 的数值（秒）。");
      return;
    }
    const downloadTime = configDownloadTime.trim();
    fetch(apiUrl("/config"), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        auth_authorize_url: configAuthorizeUrl.trim() || null,
        auth_token_url: configTokenUrl.trim() || null,
        auth_client_id: configClientId.trim() || null,
        auth_client_secret: configClientSecret.trim() || null,
        auth_redirect_uri: configRedirectUri.trim() || null,
        auth_scopes: scopes.length > 0 ? scopes : null,
        sync_mode: configSyncMode,
        token_store: configTokenStore,
        upload_interval_seconds: uploadInterval,
        download_daily_time: downloadTime || null
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

  const uploadMarkdown = () => {
    if (!uploadDocumentId.trim() || !uploadMarkdownPath.trim()) {
      setUploadError("请填写文档 token 与 Markdown 路径。");
      return;
    }
    setUploadLoading(true);
    setUploadError(null);
    setUploadStatus(null);
    fetch(apiUrl("/sync/markdown/replace"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document_id: uploadDocumentId.trim(),
        markdown_path: uploadMarkdownPath.trim(),
        task_id: uploadTaskId.trim() || null,
        base_path: uploadBasePath.trim() || null,
        update_mode: uploadUpdateMode
      })
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "上传失败");
        }
        return res.json();
      })
      .then(() => {
        setUploadStatus("上传完成");
      })
      .catch((err: Error) => setUploadError(err.message))
      .finally(() => setUploadLoading(false));
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

  const startWatcher = () => {
    if (!watchPath.trim()) {
      setWatcherError("请先填写需要监听的本地路径。");
      return;
    }
    setWatcherError(null);
    fetch(apiUrl("/watcher/start"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: watchPath.trim() })
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "启动监听失败");
        }
        return res.json();
      })
      .then(() => {
        setWatcherRunning(true);
      })
      .catch((err: Error) => {
        setWatcherError(err.message);
      });
  };

  const stopWatcher = () => {
    fetch(apiUrl("/watcher/stop"), { method: "POST" })
      .then(() => {
        setWatcherRunning(false);
      })
      .catch(() => {
        setWatcherError("停止监听失败");
      });
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

  const today = new Date();
  const todayCount = syncLogEntries.filter((entry) => isSameDay(entry.timestamp, today)).length;
  const lastSync = syncLogEntries[0];
  const enabledTasks = tasks.filter((task) => task.enabled).length;
  const runningTasks = tasks.filter((task) => taskStatusMap[task.id]?.state === "running").length;
  const unresolvedConflicts = conflicts.filter((conflict) => !conflict.resolved).length;

  const navItems: Array<{ id: NavKey; label: string; icon: (props: IconProps) => JSX.Element; badge?: number }> = [
    { id: "dashboard", label: "仪表盘", icon: IconDashboard },
    { id: "tasks", label: "同步任务", icon: IconTasks },
    { id: "conflicts", label: "冲突中心", icon: IconConflicts, badge: unresolvedConflicts || undefined },
    { id: "settings", label: "设置", icon: IconSettings },
    { id: "about", label: "关于", icon: IconInfo }
  ];

  const tabMeta: Record<NavKey, { title: string; desc: string }> = {
    dashboard: { title: "仪表盘", desc: "同步概览、实时日志与快捷操作" },
    tasks: { title: "同步任务", desc: "创建任务、管理模式与同步状态" },
    conflicts: { title: "冲突中心", desc: "云端与本地冲突处理" },
    settings: { title: "设置", desc: "OAuth 配置、调度策略与高级工具" },
    about: { title: "关于", desc: "产品信息与默认策略说明" }
  };

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
              <li>本地 -> 云端：{configUploadInterval || "2"} 秒</li>
              <li>云端 -> 本地：每日 {configDownloadTime || "01:00"}</li>
              <li>默认同步：{modeLabels[configSyncMode] || configSyncMode}</li>
            </ul>
          </div>
        </aside>

        <main className="flex-1 space-y-6">
          <header className="glass-panel flex flex-wrap items-center justify-between gap-4 rounded-3xl p-6">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
                {tabMeta[activeTab].title}
              </p>
              <h1 className="mt-2 text-2xl font-semibold text-slate-50">
                {tabMeta[activeTab].title}
              </h1>
              <p className="mt-2 text-sm text-slate-400">
                {tabMeta[activeTab].desc}
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
                    <h2 className="text-lg font-semibold text-slate-50">同步任务列表</h2>
                    <p className="mt-1 text-xs text-slate-400">
                      管理任务的同步模式、更新策略与执行状态。
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
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
                    return (
                      <div
                        key={task.id}
                        className="soft-panel rounded-3xl border border-slate-800/60 p-6"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-4">
                          <div className="space-y-2">
                            <p className="text-lg font-semibold text-slate-50">
                              {task.name || "未命名任务"}
                            </p>
                            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
                              <span className="inline-flex items-center gap-2">
                                <IconFolder className="h-3.5 w-3.5" />
                                {task.local_path}
                              </span>
                              <span className="text-slate-600">|</span>
                              <span className="inline-flex items-center gap-2">
                                <IconCloud className="h-3.5 w-3.5" />
                                {task.cloud_folder_token}
                              </span>
                            </div>
                            {task.base_path ? (
                              <p className="text-xs text-slate-500">base_path：{task.base_path}</p>
                            ) : null}
                          </div>
                          <div className="flex flex-col items-end gap-2">
                            <StatusPill
                              label={stateLabels[stateKey] || stateKey}
                              tone={stateTones[stateKey] || "neutral"}
                              dot
                            />
                            {status?.last_error ? (
                              <span className="text-xs text-rose-300">{status.last_error}</span>
                            ) : null}
                          </div>
                        </div>

                        <div className="mt-4 grid gap-4 lg:grid-cols-3">
                          <div className="rounded-2xl border border-slate-800 bg-white/5 p-4">
                            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">同步模式</p>
                            <div className="mt-2 flex items-center gap-2 text-sm text-slate-200">
                              {renderModeIcon(task.sync_mode)}
                              <span>{modeLabels[task.sync_mode] || task.sync_mode}</span>
                            </div>
                            <p className="mt-3 text-xs text-slate-400">更新模式：{updateModeLabels[task.update_mode || "auto"]}</p>
                          </div>
                          <div className="rounded-2xl border border-slate-800 bg-white/5 p-4">
                            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">同步进度</p>
                            {progress !== null ? (
                              <>
                                <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
                                  <span>{progress}%</span>
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
                              </>
                            ) : (
                              <p className="mt-2 text-xs text-slate-500">暂无进度数据</p>
                            )}
                          </div>
                          <div className="rounded-2xl border border-slate-800 bg-white/5 p-4">
                            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">统计</p>
                            <div className="mt-2 space-y-1 text-xs text-slate-300">
                              <p>完成：{status?.completed_files ?? 0}</p>
                              <p>失败：{status?.failed_files ?? 0}</p>
                              <p>跳过：{status?.skipped_files ?? 0}</p>
                            </div>
                          </div>
                        </div>

                        <div className="mt-4 flex flex-wrap gap-3">
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
                            onClick={() =>
                              updateTaskMode(task, taskUpdateModeMap[task.id] || task.update_mode || "auto")
                            }
                            type="button"
                          >
                            应用更新模式
                          </button>
                        </div>

                        <div className="mt-4 flex flex-wrap gap-3">
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
                            {task.enabled ? (
                              <>
                                <IconPause className="h-3.5 w-3.5" />
                                停用
                              </>
                            ) : (
                              <>
                                <IconPlay className="h-3.5 w-3.5" />
                                启用
                              </>
                            )}
                          </button>
                          <button
                            className="inline-flex items-center gap-2 rounded-full border border-rose-400/40 px-4 py-2 text-xs font-semibold text-rose-200 transition hover:border-rose-400"
                            onClick={() => deleteTask(task)}
                            type="button"
                          >
                            <IconTrash className="h-3.5 w-3.5" />
                            删除
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </section>
          ) : null}

          {activeTab === "conflicts" ? (
            <section className="space-y-6 fade-up">
              <div className="soft-panel rounded-3xl p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-slate-50">冲突中心</h2>
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

              <div className="space-y-4">
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
            </section>
          ) : null}
          {activeTab === "settings" ? (
            <section className="space-y-6 fade-up">
              <div className="soft-panel rounded-3xl p-6">
                <div>
                  <h2 className="text-lg font-semibold text-slate-50">OAuth 配置</h2>
                  <p className="mt-1 text-xs text-slate-400">
                    参考 docs/OAUTH_GUIDE.md 获取参数，并确保保存成功。
                  </p>
                </div>
                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  <input
                    className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                    placeholder="授权地址 auth_authorize_url"
                    value={configAuthorizeUrl}
                    onChange={(event) => setConfigAuthorizeUrl(event.target.value)}
                  />
                  <input
                    className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                    placeholder="Token 地址 auth_token_url"
                    value={configTokenUrl}
                    onChange={(event) => setConfigTokenUrl(event.target.value)}
                  />
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
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <textarea
                    className="min-h-[90px] w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200 md:col-span-2"
                    placeholder="Scopes（逗号分隔）"
                    value={configScopes}
                    onChange={(event) => setConfigScopes(event.target.value)}
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
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <button
                    className="rounded-full bg-blue-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-blue-400 disabled:cursor-not-allowed disabled:opacity-60"
                    onClick={saveConfig}
                    disabled={configLoading}
                    type="button"
                  >
                    {configLoading ? "保存中..." : "保存配置"}
                  </button>
                  {configStatus ? <span className="text-sm text-emerald-300">{configStatus}</span> : null}
                  {configError ? <span className="text-sm text-rose-300">错误：{configError}</span> : null}
                </div>
              </div>

              <div className="soft-panel rounded-3xl p-6">
                <div>
                  <h2 className="text-lg font-semibold text-slate-50">同步策略</h2>
                  <p className="mt-1 text-xs text-slate-400">
                    默认：本地变更每 {configUploadInterval || "2"} 秒上行，云端每日 {configDownloadTime || "01:00"} 下行。
                  </p>
                </div>
                <div className="mt-5 grid gap-4 md:grid-cols-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-400">本地上行</p>
                    <input
                      className="mt-2 w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                      type="number"
                      min="0"
                      step="0.5"
                      placeholder="上传间隔（秒）"
                      value={configUploadInterval}
                      onChange={(event) => setConfigUploadInterval(event.target.value)}
                    />
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-400">云端下行</p>
                    <input
                      className="mt-2 w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                      type="time"
                      value={configDownloadTime}
                      onChange={(event) => setConfigDownloadTime(event.target.value)}
                    />
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-400">默认同步模式</p>
                    <select
                      className="mt-2 w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
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

              <div className="grid gap-6 lg:grid-cols-2">
                <div className="soft-panel rounded-3xl p-6">
                  <h2 className="text-lg font-semibold text-slate-50">手动上传 Markdown</h2>
                  <p className="mt-1 text-xs text-slate-400">
                    用于快速验证 Docx 全量覆盖与图片上传链路。
                  </p>
                  <div className="mt-4 space-y-3">
                    <input
                      className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                      placeholder="Docx 文档 token"
                      value={uploadDocumentId}
                      onChange={(event) => setUploadDocumentId(event.target.value)}
                    />
                    <input
                      className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                      placeholder="Markdown 文件路径，例如 D:\\Docs\\note.md"
                      value={uploadMarkdownPath}
                      onChange={(event) => setUploadMarkdownPath(event.target.value)}
                    />
                    <select
                      className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                      value={uploadTaskId}
                      onChange={(event) => setUploadTaskId(event.target.value)}
                    >
                      <option value="">选择任务（可选）</option>
                      {tasks.map((task) => (
                        <option key={task.id} value={task.id}>
                          {task.name || task.local_path}
                        </option>
                      ))}
                    </select>
                    <input
                      className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                      placeholder="base_path（可选）"
                      value={uploadBasePath}
                      onChange={(event) => setUploadBasePath(event.target.value)}
                    />
                    <select
                      className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                      value={uploadUpdateMode}
                      onChange={(event) => setUploadUpdateMode(event.target.value)}
                    >
                      <option value="auto">更新模式：自动</option>
                      <option value="partial">更新模式：局部</option>
                      <option value="full">更新模式：全量</option>
                    </select>
                    <button
                      className="rounded-full bg-emerald-500/20 px-5 py-2 text-sm font-semibold text-emerald-200 transition hover:bg-emerald-500/30 disabled:cursor-not-allowed disabled:opacity-60"
                      onClick={uploadMarkdown}
                      disabled={uploadLoading}
                      type="button"
                    >
                      {uploadLoading ? "上传中..." : "开始上传"}
                    </button>
                    {uploadStatus ? <p className="text-sm text-emerald-300">{uploadStatus}</p> : null}
                    {uploadError ? <p className="text-sm text-rose-300">错误：{uploadError}</p> : null}
                  </div>
                </div>

                <div className="soft-panel rounded-3xl p-6">
                  <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold text-slate-50">本地监听</h2>
                    <StatusPill label={`WS ${wsStatus}`} tone={wsStatus === "open" ? "success" : "warning"} />
                  </div>
                  <p className="mt-1 text-xs text-slate-400">
                    监听本地目录变更并推送事件。
                  </p>
                  <div className="mt-4 space-y-3">
                    <input
                      className="w-full rounded-2xl border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200"
                      placeholder="输入需要监听的本地路径"
                      value={watchPath}
                      onChange={(event) => setWatchPath(event.target.value)}
                    />
                    <div className="flex flex-wrap gap-2">
                      <button
                        className="rounded-full bg-emerald-500/20 px-4 py-2 text-xs font-semibold text-emerald-200 transition hover:bg-emerald-500/30 disabled:cursor-not-allowed disabled:opacity-60"
                        disabled={watcherRunning}
                        onClick={startWatcher}
                        type="button"
                      >
                        启动监听
                      </button>
                      <button
                        className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                        disabled={!watcherRunning}
                        onClick={stopWatcher}
                        type="button"
                      >
                        停止监听
                      </button>
                      <span className="self-center text-xs text-slate-400">
                        状态：{watcherRunning ? "运行中" : "未启动"}
                      </span>
                    </div>
                    {watcherError ? <p className="text-sm text-rose-300">错误：{watcherError}</p> : null}
                  </div>
                  <div className="mt-4 max-h-40 space-y-2 overflow-auto rounded-2xl border border-slate-800 bg-black/30 p-3 text-xs text-slate-300">
                    {events.length === 0 ? (
                      <p className="text-slate-500">暂无监听事件。</p>
                    ) : (
                      events.map((evt, index) => (
                        <div key={`${evt.timestamp}-${index}`}>
                          <p className="text-slate-400">{evt.event_type}</p>
                          <p className="break-all">{evt.src_path}</p>
                          {evt.dest_path ? <p className="text-slate-500">-> {evt.dest_path}</p> : null}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              <div className="soft-panel rounded-3xl p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-slate-50">云端目录预览</h2>
                    <p className="mt-1 text-xs text-slate-400">用于校验云端目录结构与选择范围。</p>
                  </div>
                  <button
                    className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
                    onClick={loadTree}
                    type="button"
                  >
                    <IconRefresh className="h-3.5 w-3.5" />
                    刷新目录
                  </button>
                </div>
                <div className="mt-4 rounded-2xl border border-slate-800 bg-black/30 p-4">
                  {treeLoading ? (
                    <p className="text-sm text-slate-400">目录加载中...</p>
                  ) : treeError ? (
                    <p className="text-sm text-rose-300">{treeError}</p>
                  ) : tree ? (
                    <ul className="space-y-3">
                      <TreeNode node={tree} />
                    </ul>
                  ) : (
                    <p className="text-sm text-slate-400">尚未加载目录树。</p>
                  )}
                </div>
              </div>
            </section>
          ) : null}

          {activeTab === "about" ? (
            <section className="space-y-6 fade-up">
              <div className="soft-panel rounded-3xl p-6">
                <h2 className="text-lg font-semibold text-slate-50">关于 LarkSync</h2>
                <p className="mt-2 text-sm text-slate-400">
                  LarkSync 旨在打通飞书云端文档与本地 Markdown 的双向协作，提供可靠的同步、转码与冲突处理能力。
                </p>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl border border-slate-800 bg-white/5 p-4">
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-400">默认策略</p>
                    <ul className="mt-3 space-y-2 text-sm text-slate-200">
                      <li>本地 -> 云端：每 2 秒触发上传队列</li>
                      <li>云端 -> 本地：每日 01:00 自动下载</li>
                      <li>支持手动触发与任务级别配置</li>
                    </ul>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-white/5 p-4">
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-400">参考文档</p>
                    <ul className="mt-3 space-y-2 text-sm text-slate-200">
                      <li>docs/SYNC_LOGIC.md</li>
                      <li>docs/USAGE.md</li>
                      <li>docs/OAUTH_GUIDE.md</li>
                    </ul>
                  </div>
                </div>
              </div>
            </section>
          ) : null}
        </main>
      </div>

      {showTaskModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 px-4 py-6">
          <div className="max-h-[90vh] w-full max-w-4xl overflow-auto rounded-3xl bg-[#0f1524] p-6 text-slate-100 shadow-2xl">
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
