import { useEffect, useState } from "react";

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
  enabled: boolean;
  created_at: number;
  updated_at: number;
};

function TreeNode({ node }: { node: DriveNode }) {
  const [open, setOpen] = useState(true);
  const isFolder = node.type === "folder";
  const hasChildren = Boolean(node.children && node.children.length);

  return (
    <li className="space-y-2">
      <div className="flex items-center gap-2">
        {isFolder ? (
          <button
            className="flex h-6 w-6 items-center justify-center rounded-full border border-slate-700 text-xs text-slate-200"
            onClick={() => setOpen((prev) => !prev)}
            type="button"
          >
            {open ? "▾" : "▸"}
          </button>
        ) : (
          <span className="text-slate-500">•</span>
        )}
        <span className="text-sm text-slate-100">{node.name}</span>
        <span className="rounded-full border border-slate-700 px-2 py-0.5 text-xs uppercase tracking-widest text-slate-400">
          {node.type}
        </span>
      </div>
      {isFolder && hasChildren && open ? (
        <ul className="ml-4 space-y-2 border-l border-slate-800 pl-4">
          {node.children?.map((child) => (
            <TreeNode key={child.token} node={child} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

export default function App() {
  const apiBase = import.meta.env.PROD ? "/api" : "";
  const apiUrl = (path: string) => `${apiBase}${path}`;
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
  const [taskEnabled, setTaskEnabled] = useState(true);
  const [uploadDocumentId, setUploadDocumentId] = useState("");
  const [uploadMarkdownPath, setUploadMarkdownPath] = useState("");
  const [uploadTaskId, setUploadTaskId] = useState("");
  const [uploadBasePath, setUploadBasePath] = useState("");
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
  const [configLoading, setConfigLoading] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [configStatus, setConfigStatus] = useState<string | null>(null);

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
        setTaskEnabled(true);
        loadTasks();
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
      .then(() => loadTasks())
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
        token_store: configTokenStore
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
        base_path: uploadBasePath.trim() || null
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

  useEffect(() => {
    loadConflicts();
  }, []);

  useEffect(() => {
    loadTasks();
  }, []);

  useEffect(() => {
    loadConfig();
  }, []);

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

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <section className="mx-auto flex min-h-screen w-full max-w-5xl flex-col items-start justify-center px-6 py-16">
        <span className="text-sm uppercase tracking-[0.3em] text-slate-400">
          LarkSync OAuth
        </span>
        <h1 className="mt-4 text-4xl font-semibold">飞书账号连接</h1>
        <p className="mt-4 max-w-2xl text-base text-slate-300">
          当前状态：
          <span className="ml-2 font-medium text-white">
            {loading ? "检测中..." : connected ? "已连接" : "未连接"}
          </span>
        </p>
        {expiresAt ? (
          <p className="mt-2 text-sm text-slate-500">
            令牌过期时间：{new Date(expiresAt * 1000).toLocaleString()}
          </p>
        ) : null}
        <div className="mt-8 flex flex-wrap gap-4">
          <a
            className="inline-flex items-center justify-center rounded-full border border-slate-500 px-6 py-2 text-sm font-medium text-slate-100 transition hover:border-slate-300"
            href={apiUrl("/auth/login")}
          >
            登录飞书
          </a>
          <button
            className="inline-flex items-center justify-center rounded-full bg-slate-100 px-6 py-2 text-sm font-semibold text-slate-900 transition hover:bg-white"
            onClick={() => {
              fetch(apiUrl("/auth/logout"), { method: "POST" }).then(() => {
                setConnected(false);
                setExpiresAt(null);
              });
            }}
          >
            断开连接
          </button>
        </div>
        <div className="mt-10 grid gap-4 text-sm text-slate-400">
          <p>请在环境变量或 data/config.json 中配置 OAuth 参数。</p>
          <ul className="list-disc space-y-1 pl-4">
            <li>LARKSYNC_AUTH_AUTHORIZE_URL</li>
            <li>LARKSYNC_AUTH_TOKEN_URL</li>
            <li>LARKSYNC_AUTH_CLIENT_ID</li>
            <li>LARKSYNC_AUTH_CLIENT_SECRET</li>
            <li>LARKSYNC_AUTH_REDIRECT_URI</li>
          </ul>
        </div>

        <section className="mt-10 w-full rounded-3xl border border-slate-800 bg-slate-900/60 p-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold">OAuth 配置向导</h2>
              <p className="mt-2 text-sm text-slate-400">
                通过网页填写 App ID/Secret 与回调地址，保存到本地配置文件。
              </p>
            </div>
            <button
              className="rounded-full border border-slate-600 px-5 py-2 text-sm font-medium text-slate-100 transition hover:border-slate-300 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={configLoading}
              onClick={loadConfig}
              type="button"
            >
              {configLoading ? "加载中..." : "刷新配置"}
            </button>
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="space-y-4">
              <input
                className="w-full rounded-2xl border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none transition focus:border-slate-400"
                placeholder="授权地址（Authorize URL）"
                value={configAuthorizeUrl}
                onChange={(event) => setConfigAuthorizeUrl(event.target.value)}
              />
              <input
                className="w-full rounded-2xl border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none transition focus:border-slate-400"
                placeholder="Token 地址（Access Token URL）"
                value={configTokenUrl}
                onChange={(event) => setConfigTokenUrl(event.target.value)}
              />
              <input
                className="w-full rounded-2xl border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none transition focus:border-slate-400"
                placeholder="App ID"
                value={configClientId}
                onChange={(event) => setConfigClientId(event.target.value)}
              />
              <input
                className="w-full rounded-2xl border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none transition focus:border-slate-400"
                placeholder="App Secret（留空则不更新）"
                value={configClientSecret}
                onChange={(event) => setConfigClientSecret(event.target.value)}
                type="password"
              />
              <input
                className="w-full rounded-2xl border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none transition focus:border-slate-400"
                placeholder="回调地址，例如 http://localhost:8000/auth/callback"
                value={configRedirectUri}
                onChange={(event) => setConfigRedirectUri(event.target.value)}
              />
              <input
                className="w-full rounded-2xl border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none transition focus:border-slate-400"
                placeholder="权限 scopes，逗号分隔"
                value={configScopes}
                onChange={(event) => setConfigScopes(event.target.value)}
              />
              <div className="flex flex-wrap gap-3">
                <select
                  className="rounded-full border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none"
                  value={configSyncMode}
                  onChange={(event) => setConfigSyncMode(event.target.value)}
                >
                  <option value="bidirectional">双向同步</option>
                  <option value="download_only">仅下载</option>
                  <option value="upload_only">仅上传</option>
                </select>
                <select
                  className="rounded-full border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none"
                  value={configTokenStore}
                  onChange={(event) => setConfigTokenStore(event.target.value)}
                >
                  <option value="keyring">keyring</option>
                  <option value="memory">memory</option>
                </select>
              </div>
              <button
                className="rounded-full bg-slate-100 px-5 py-2 text-sm font-semibold text-slate-900 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
                onClick={saveConfig}
                disabled={configLoading}
                type="button"
              >
                {configLoading ? "保存中..." : "保存配置"}
              </button>
              {configStatus ? (
                <p className="text-sm text-emerald-300">{configStatus}</p>
              ) : null}
              {configError ? (
                <p className="text-sm text-rose-300">错误：{configError}</p>
              ) : null}
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-4 text-sm text-slate-300">
              <p className="text-slate-200">配置步骤（按顺序）</p>
              <ol className="mt-3 list-decimal space-y-2 pl-4 text-xs text-slate-400">
                <li>登录飞书开放平台控制台，创建“企业自建应用”。</li>
                <li>进入“应用凭证”，复制 App ID 与 App Secret。</li>
                <li>进入“安全设置 / OAuth 回调”，添加回调地址（需与下方填写一致）。</li>
                <li>进入“权限管理”，添加需要的 scopes（最少权限原则）。</li>
                <li>从飞书 OAuth2 文档确认授权地址与 Token 地址，填入本表单。</li>
                <li>保存配置后，再点击“登录飞书”完成授权。</li>
              </ol>
              <div className="mt-4 space-y-2 text-xs text-slate-500">
                <p>常用地址示例（仅示例，以官方文档为准）：</p>
                <p>授权地址：`https://open.feishu.cn/open-apis/authen/v1/index`</p>
                <p>Token 地址：`https://open.feishu.cn/open-apis/authen/v1/access_token`</p>
                <p>开发回调：`http://localhost:8000/auth/callback`</p>
                <p>生产回调：`http://localhost:8080/api/auth/callback`</p>
                <p>详细步骤见 `docs/OAUTH_GUIDE.md`。</p>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-16 w-full rounded-3xl border border-slate-800 bg-slate-900/60 p-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold">同步任务配置</h2>
              <p className="mt-2 text-sm text-slate-400">
                配置本地目录、云端目录与同步模式，作为后续同步任务的基础。
              </p>
            </div>
            <button
              className="rounded-full border border-slate-600 px-5 py-2 text-sm font-medium text-slate-100 transition hover:border-slate-300 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={taskLoading}
              onClick={loadTasks}
              type="button"
            >
              {taskLoading ? "加载中..." : "刷新任务"}
            </button>
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="space-y-4">
              <input
                className="w-full rounded-2xl border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none transition focus:border-slate-400"
                placeholder="任务名称（可选）"
                value={taskName}
                onChange={(event) => setTaskName(event.target.value)}
              />
              <input
                className="w-full rounded-2xl border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none transition focus:border-slate-400"
                placeholder="本地同步路径，例如 C:\\\\Docs"
                value={taskLocalPath}
                onChange={(event) => setTaskLocalPath(event.target.value)}
              />
              <input
                className="w-full rounded-2xl border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none transition focus:border-slate-400"
                placeholder="Markdown base_path（可选）"
                value={taskBasePath}
                onChange={(event) => setTaskBasePath(event.target.value)}
              />
              <input
                className="w-full rounded-2xl border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none transition focus:border-slate-400"
                placeholder="云端文件夹 token"
                value={taskCloudToken}
                onChange={(event) => setTaskCloudToken(event.target.value)}
              />
              <div className="flex flex-wrap gap-3">
                <select
                  className="rounded-full border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none"
                  value={taskSyncMode}
                  onChange={(event) => setTaskSyncMode(event.target.value)}
                >
                  <option value="bidirectional">双向同步</option>
                  <option value="download_only">仅下载</option>
                  <option value="upload_only">仅上传</option>
                </select>
                <button
                  className="rounded-full border border-slate-600 px-5 py-2 text-sm font-medium text-slate-100 transition hover:border-slate-300"
                  type="button"
                  onClick={() => setTaskEnabled((prev) => !prev)}
                >
                  {taskEnabled ? "启用中" : "已停用"}
                </button>
              </div>
              <button
                className="rounded-full bg-slate-100 px-5 py-2 text-sm font-semibold text-slate-900 transition hover:bg-white"
                onClick={createTask}
                type="button"
              >
                保存任务
              </button>
              {taskError ? (
                <p className="text-sm text-rose-300">错误：{taskError}</p>
              ) : null}
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-4 text-sm text-slate-300">
              {tasks.length === 0 ? (
                <p className="text-slate-500">暂无同步任务。</p>
              ) : (
                <ul className="space-y-3">
                  {tasks.map((task) => (
                    <li
                      key={task.id}
                      className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-sm text-slate-100">
                            {task.name || "未命名任务"}
                          </p>
                          <p className="text-xs text-slate-500">
                            本地：{task.local_path}
                          </p>
                          <p className="text-xs text-slate-500">
                            云端：{task.cloud_folder_token}
                          </p>
                          <p className="text-xs text-slate-500">
                            模式：{task.sync_mode}
                          </p>
                          {task.base_path ? (
                            <p className="text-xs text-slate-500">
                              base_path：{task.base_path}
                            </p>
                          ) : null}
                        </div>
                        <button
                          className="rounded-full border border-slate-600 px-4 py-2 text-xs font-medium text-slate-100 transition hover:border-slate-300"
                          onClick={() => toggleTask(task)}
                          type="button"
                        >
                          {task.enabled ? "停用" : "启用"}
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </section>

        <section className="mt-12 w-full rounded-3xl border border-slate-800 bg-slate-900/60 p-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold">手动上传 Markdown</h2>
              <p className="mt-2 text-sm text-slate-400">
                用于快速验证图片上传与 Docx 全量覆盖链路。
              </p>
            </div>
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="space-y-4">
              <input
                className="w-full rounded-2xl border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none transition focus:border-slate-400"
                placeholder="Docx 文档 token"
                value={uploadDocumentId}
                onChange={(event) => setUploadDocumentId(event.target.value)}
              />
              <input
                className="w-full rounded-2xl border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none transition focus:border-slate-400"
                placeholder="Markdown 文件路径，例如 C:\\\\Docs\\\\note.md"
                value={uploadMarkdownPath}
                onChange={(event) => setUploadMarkdownPath(event.target.value)}
              />
              <select
                className="rounded-full border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none"
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
                className="w-full rounded-2xl border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none transition focus:border-slate-400"
                placeholder="base_path（可选）"
                value={uploadBasePath}
                onChange={(event) => setUploadBasePath(event.target.value)}
              />
              <button
                className="rounded-full bg-slate-100 px-5 py-2 text-sm font-semibold text-slate-900 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
                onClick={uploadMarkdown}
                disabled={uploadLoading}
                type="button"
              >
                {uploadLoading ? "上传中..." : "开始上传"}
              </button>
              {uploadStatus ? (
                <p className="text-sm text-emerald-300">{uploadStatus}</p>
              ) : null}
              {uploadError ? (
                <p className="text-sm text-rose-300">错误：{uploadError}</p>
              ) : null}
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-4 text-sm text-slate-300">
              <p className="text-slate-400">
                说明：
              </p>
              <ul className="mt-3 space-y-2 text-xs text-slate-400">
                <li>如果选择任务，后端会优先使用任务的 base_path。</li>
                <li>未选择任务时，可手动填写 base_path（Markdown 所在目录）。</li>
                <li>上传会执行 Docx 全量覆盖，请谨慎操作。</li>
              </ul>
            </div>
          </div>
        </section>

        <section className="mt-12 w-full rounded-3xl border border-slate-800 bg-slate-900/60 p-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold">云端目录树</h2>
              <p className="mt-2 text-sm text-slate-400">
                递归展示飞书云空间的文件夹与文档结构。
              </p>
            </div>
            <button
              className="rounded-full border border-slate-600 px-5 py-2 text-sm font-medium text-slate-100 transition hover:border-slate-300 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!connected || treeLoading}
              onClick={loadTree}
              type="button"
            >
              {treeLoading ? "加载中..." : "刷新目录"}
            </button>
          </div>
          <div className="mt-6">
            {!connected ? (
              <p className="text-sm text-slate-500">请先完成登录后再加载目录。</p>
            ) : treeError ? (
              <p className="text-sm text-rose-300">加载失败：{treeError}</p>
            ) : tree ? (
              <ul className="space-y-3">
                <TreeNode node={tree} />
              </ul>
            ) : (
              <p className="text-sm text-slate-500">尚未加载目录。</p>
            )}
          </div>
        </section>

        <section className="mt-12 w-full rounded-3xl border border-slate-800 bg-slate-900/60 p-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold">本地文件监听</h2>
              <p className="mt-2 text-sm text-slate-400">
                监听本地目录变更并通过 WebSocket 推送事件。
              </p>
            </div>
            <span className="text-xs uppercase tracking-[0.3em] text-slate-500">
              WS {wsStatus}
            </span>
          </div>
          <div className="mt-6 flex flex-col gap-4">
            <input
              className="w-full rounded-2xl border border-slate-700 bg-slate-950/40 px-4 py-2 text-sm text-slate-100 outline-none transition focus:border-slate-400"
              placeholder="输入需要监听的本地路径，例如 C:\\\\Docs"
              value={watchPath}
              onChange={(event) => setWatchPath(event.target.value)}
            />
            <div className="flex flex-wrap gap-3">
              <button
                className="rounded-full bg-slate-100 px-5 py-2 text-sm font-semibold text-slate-900 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
                disabled={watcherRunning}
                onClick={startWatcher}
                type="button"
              >
                启动监听
              </button>
              <button
                className="rounded-full border border-slate-600 px-5 py-2 text-sm font-medium text-slate-100 transition hover:border-slate-300 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={!watcherRunning}
                onClick={stopWatcher}
                type="button"
              >
                停止监听
              </button>
              <span className="self-center text-sm text-slate-400">
                状态：{watcherRunning ? "运行中" : "未启动"}
              </span>
            </div>
            {watcherError ? (
              <p className="text-sm text-rose-300">错误：{watcherError}</p>
            ) : null}
          </div>
          <div className="mt-6 max-h-60 overflow-auto rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-300">
            {events.length === 0 ? (
              <p className="text-slate-500">暂无监听事件。</p>
            ) : (
              <ul className="space-y-2">
                {events.map((evt, index) => (
                  <li key={`${evt.timestamp}-${index}`} className="flex flex-col gap-1">
                    <span className="text-xs uppercase tracking-[0.2em] text-slate-500">
                      {evt.event_type}
                    </span>
                    <span>{evt.src_path}</span>
                    {evt.dest_path ? (
                      <span className="text-slate-500">
                        → {evt.dest_path}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <section className="mt-12 w-full rounded-3xl border border-slate-800 bg-slate-900/60 p-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold">冲突中心</h2>
              <p className="mt-2 text-sm text-slate-400">
                当云端与本地同时被修改时，将在此处展示冲突详情。
              </p>
            </div>
            <button
              className="rounded-full border border-slate-600 px-5 py-2 text-sm font-medium text-slate-100 transition hover:border-slate-300 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={conflictLoading}
              onClick={loadConflicts}
              type="button"
            >
              {conflictLoading ? "加载中..." : "刷新冲突"}
            </button>
          </div>
          <div className="mt-6 space-y-4">
            {conflictError ? (
              <p className="text-sm text-rose-300">加载失败：{conflictError}</p>
            ) : conflicts.length === 0 ? (
              <p className="text-sm text-slate-500">暂无冲突记录。</p>
            ) : (
              conflicts.map((conflict) => (
                <div
                  key={conflict.id}
                  className="rounded-2xl border border-slate-800 bg-slate-950/40 p-5"
                >
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="space-y-1">
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                        本地路径
                      </p>
                      <p className="text-sm text-slate-100">{conflict.local_path}</p>
                      <p className="text-xs text-slate-500">
                        云端 Token：{conflict.cloud_token}
                      </p>
                      <p className="text-xs text-slate-500">
                        哈希：{conflict.local_hash.slice(0, 8)} /{" "}
                        {conflict.db_hash.slice(0, 8)}
                      </p>
                    </div>
                    <div className="text-xs text-slate-500">
                      云端版本 {conflict.cloud_version} ｜ DB 版本{" "}
                      {conflict.db_version}
                    </div>
                  </div>
                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <p className="text-sm font-semibold text-slate-200">
                        本地版本
                      </p>
                      <pre className="max-h-48 overflow-auto rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-xs text-slate-300">
                        {conflict.local_preview || "暂无本地预览。"}
                      </pre>
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm font-semibold text-slate-200">
                        云端版本
                      </p>
                      <pre className="max-h-48 overflow-auto rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-xs text-slate-300">
                        {conflict.cloud_preview || "暂无云端预览。"}
                      </pre>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <button
                      className="rounded-full bg-slate-100 px-5 py-2 text-sm font-semibold text-slate-900 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={conflict.resolved}
                      onClick={() => resolveConflict(conflict.id, "use_local")}
                      type="button"
                    >
                      使用本地
                    </button>
                    <button
                      className="rounded-full border border-slate-600 px-5 py-2 text-sm font-medium text-slate-100 transition hover:border-slate-300 disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={conflict.resolved}
                      onClick={() => resolveConflict(conflict.id, "use_cloud")}
                      type="button"
                    >
                      使用云端
                    </button>
                    {conflict.resolved ? (
                      <span className="self-center text-xs uppercase tracking-[0.2em] text-slate-500">
                        已处理：{conflict.resolved_action}
                      </span>
                    ) : null}
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </section>
    </main>
  );
}
