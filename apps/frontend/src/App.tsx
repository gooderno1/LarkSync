import { useEffect, useState } from "react";

const statusText: Record<boolean, string> = {
  true: "已连接",
  false: "未连接"
};

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
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [expiresAt, setExpiresAt] = useState<number | null>(null);
  const [tree, setTree] = useState<DriveNode | null>(null);
  const [treeLoading, setTreeLoading] = useState(false);
  const [treeError, setTreeError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/auth/status")
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

  const loadTree = () => {
    if (!connected) return;
    setTreeLoading(true);
    setTreeError(null);
    fetch("/drive/tree")
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
            {loading ? "检测中..." : statusText[connected]}
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
            href="/auth/login"
          >
            登录飞书
          </a>
          <button
            className="inline-flex items-center justify-center rounded-full bg-slate-100 px-6 py-2 text-sm font-semibold text-slate-900 transition hover:bg-white"
            onClick={() => {
              fetch("/auth/logout", { method: "POST" }).then(() => {
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

        <section className="mt-16 w-full rounded-3xl border border-slate-800 bg-slate-900/60 p-8">
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
      </section>
    </main>
  );
}
