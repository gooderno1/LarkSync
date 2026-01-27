import { useEffect, useState } from "react";

const statusText: Record<boolean, string> = {
  true: "已连接",
  false: "未连接"
};

export default function App() {
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [expiresAt, setExpiresAt] = useState<number | null>(null);

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
      </section>
    </main>
  );
}
