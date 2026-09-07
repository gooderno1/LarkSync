import { useState } from "react";
import type { ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../lib/api";

type KeychainStatus = {
  supported: boolean;
  blocked: boolean;
  retrying: boolean;
  message?: string | null;
};

export function KeychainAccessBoundary({ children }: { children: ReactNode }) {
  const client = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const status = useQuery<KeychainStatus>({
    queryKey: ["keychain-status"],
    queryFn: () => apiFetch<KeychainStatus>("/auth/keychain/status"),
    retry: false,
    refetchInterval: (query) => query.state.data?.supported ? 3_000 : false,
    refetchIntervalInBackground: true,
  });

  const retry = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await apiFetch<KeychainStatus>("/auth/keychain/retry", { method: "POST" });
      await client.invalidateQueries({
        predicate: (query) => ["accounts-summary", "app-profiles", "auth-status"].includes(String(query.queryKey[0])),
      });
      client.setQueryData(["keychain-status"], result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "钥匙串访问未恢复，请再试一次。");
      await status.refetch();
    } finally {
      setBusy(false);
    }
  };

  if (!busy && !status.data?.blocked && !status.data?.retrying) return children;

  return (
    <div className="grid min-h-screen place-items-center overflow-y-auto bg-[#f5f9ff] px-6 py-10 text-[#102033]">
      <section role="alert" className="w-full max-w-xl rounded-2xl border border-[#d6e3f3] bg-white p-7 shadow-lg">
        <img src="/logo-horizontal.png" alt="LarkSync" className="h-9 w-auto" />
        <h1 className="mt-6 text-2xl font-semibold">需要恢复钥匙串访问</h1>
        <p className="mt-3 text-sm leading-6 text-[#52657a]">LarkSync 暂时无法读取 Mac 保存的登录凭据，已暂停重复请求。你的账号、同步任务和文件仍然保留。</p>
        <p className="mt-3 text-sm leading-6 text-[#52657a]">点击下方按钮后，按 macOS 提示输入“登录”钥匙串密码，并为 LarkSync 选择“始终允许”。旧版凭据可能需要逐项授权。</p>
        <p className="mt-3 text-sm leading-6 text-[#52657a]">如果没有系统提示，请先在“钥匙串访问”中解锁“登录”钥匙串，再重试。仅删除并重装应用通常不会清除这些凭据。</p>
        {error ? <p className="mt-4 text-sm text-red-700">{error}</p> : null}
        <button type="button" disabled={busy || status.data?.retrying} onClick={() => void retry()}
          className="mt-6 rounded-lg bg-[#3370ff] px-5 py-3 text-sm font-semibold text-white disabled:opacity-60">
          {busy || status.data?.retrying ? "正在等待系统授权…" : "重试钥匙串访问"}
        </button>
      </section>
    </div>
  );
}
