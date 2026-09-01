import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as QRCode from "qrcode";

import { apiFetch } from "../lib/api";
import type { AppProfile } from "../types";
import { useAccounts } from "../hooks/useAccounts";

type Session = {
  session_id: string;
  status: string;
  brand: string;
  user_code: string;
  verification_uri: string;
  verification_uri_complete: string;
  expires_at: number;
  interval: number;
};

type Props = {
  onConnected?: () => void;
};

export function AccountConnectPanel({ onConnected }: Props) {
  const { refreshAccounts } = useAccounts();
  const profiles = useQuery<AppProfile[]>({
    queryKey: ["app-profiles"],
    queryFn: () => apiFetch<AppProfile[]>("/app-profiles"),
  });
  const [session, setSession] = useState<Session | null>(null);
  const [sessionKind, setSessionKind] = useState<"registration" | "device" | null>(null);
  const [qrData, setQrData] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);
  const [appId, setAppId] = useState("");
  const [appSecret, setAppSecret] = useState("");

  useEffect(() => {
    if (!session?.verification_uri_complete) {
      setQrData(null);
      return;
    }
    let cancelled = false;
    QRCode.toDataURL(session.verification_uri_complete, {
      width: 248,
      margin: 1,
      color: { dark: "#102033", light: "#ffffff" },
    }).then((value) => !cancelled && setQrData(value));
    return () => {
      cancelled = true;
    };
  }, [session]);

  useEffect(() => {
    if (!session || !sessionKind) return;
    let stopped = false;
    const endpoint =
      sessionKind === "device"
        ? `/auth/device-sessions/${session.session_id}`
        : `/app-profiles/registration-sessions/${session.session_id}`;
    const timer = window.setInterval(async () => {
      try {
        const result = await apiFetch<Record<string, unknown>>(endpoint);
        if (stopped) return;
        const status = String(result.status || "pending");
        if (status === "authorized") {
          stopped = true;
          window.clearInterval(timer);
          await refreshAccounts();
          onConnected?.();
        } else if (status === "registered") {
          stopped = true;
          window.clearInterval(timer);
          setSession(null);
          setSessionKind(null);
          await profiles.refetch();
          const profile = result.app_profile as AppProfile | undefined;
          if (profile?.id) await beginDevice(profile.id);
        } else if (status === "denied" || status === "expired") {
          stopped = true;
          window.clearInterval(timer);
          setError(status === "denied" ? "你取消了授权，请重新开始。" : "二维码已过期，请重新生成。 ");
          setSession(null);
        }
      } catch (err) {
        if (!stopped) setError(err instanceof Error ? err.message : "授权状态读取失败");
      }
    }, Math.max(1, session.interval) * 1_000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [session, sessionKind, onConnected, profiles, refreshAccounts]);

  const beginRegistration = async () => {
    setBusy(true);
    setError(null);
    try {
      const value = await apiFetch<Session>("/app-profiles/registration-sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brand: "feishu" }),
      });
      setSession(value);
      setSessionKind("registration");
    } catch (err) {
      setError(err instanceof Error ? err.message : "自动创建应用失败");
    } finally {
      setBusy(false);
    }
  };

  const beginDevice = async (profileId: string) => {
    setBusy(true);
    setError(null);
    try {
      const value = await apiFetch<Session>("/auth/device-sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ app_profile_id: profileId }),
      });
      setSession(value);
      setSessionKind("device");
    } catch (err) {
      setError(err instanceof Error ? err.message : "扫码登录启动失败");
    } finally {
      setBusy(false);
    }
  };

  const saveManual = async () => {
    if (!appId.trim() || !appSecret.trim()) {
      setError("请填写 App ID 和 App Secret。");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const profile = await apiFetch<AppProfile>("/app-profiles/manual", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ app_id: appId.trim(), app_secret: appSecret.trim(), brand: "feishu" }),
      });
      setAppSecret("");
      await profiles.refetch();
      await beginDevice(profile.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "应用配置保存失败");
    } finally {
      setBusy(false);
    }
  };

  if (session) {
    return (
      <div className="grid gap-5 md:grid-cols-[280px_minmax(0,1fr)]">
        <div className="rounded-2xl border border-[#d6e3f3] bg-white p-4 shadow-sm">
          <div className="grid aspect-square place-items-center rounded-xl bg-[#f5f9ff] p-3">
            {qrData ? <img src={qrData} alt="飞书扫码授权二维码" className="h-full w-full" /> : <span className="text-sm text-[#71869d]">正在生成二维码…</span>}
          </div>
        </div>
        <div className="flex flex-col justify-center">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#3370ff]">{sessionKind === "registration" ? "步骤 1 · 创建个人应用" : "步骤 2 · 登录账号"}</p>
          <h2 className="mt-2 text-2xl font-semibold text-[#102033]">使用飞书扫码确认</h2>
          <p className="mt-3 text-sm leading-6 text-[#52657a]">二维码由 LarkSync 按官方 lark-cli Device Flow 协议生成。确认后本页会自动完成，不需要复制授权码。</p>
          {session.user_code ? <div className="mt-4 rounded-xl border border-[#d6e3f3] bg-[#f7faff] px-4 py-3 font-mono text-sm text-[#102033]">备用验证码：{session.user_code}</div> : null}
          <button type="button" className="mt-4 w-fit rounded-lg border border-[#b9cce2] px-4 py-2 text-sm font-semibold text-[#3370ff] hover:bg-[#eef5ff]" onClick={() => window.open(session.verification_uri_complete, "_blank", "noopener,noreferrer")}>在浏览器中打开</button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="rounded-2xl border border-[#cfe0f5] bg-[linear-gradient(135deg,#f7fbff,#edf5ff)] p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#3370ff]">推荐</p>
        <h2 className="mt-2 text-xl font-semibold text-[#102033]">自动创建应用并扫码登录</h2>
        <p className="mt-2 text-sm leading-6 text-[#52657a]">无需安装 lark-cli，也无需手动复制回调地址。LarkSync 原生复用官方已验证协议，应用密钥和账号 Token 分开写入系统安全存储。</p>
        <button type="button" disabled={busy} onClick={() => void beginRegistration()} className="mt-4 rounded-xl bg-[#3370ff] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(51,112,255,0.22)] disabled:opacity-50">{busy ? "正在准备…" : "开始扫码连接"}</button>
      </div>

      {(profiles.data?.length ?? 0) > 0 ? (
        <div className="mt-4 rounded-2xl border border-[#d6e3f3] bg-white p-5">
          <h3 className="font-semibold text-[#102033]">使用已有应用配置</h3>
          <div className="mt-3 grid gap-2">
            {profiles.data?.map((profile) => (
              <button key={profile.id} type="button" disabled={busy} onClick={() => void beginDevice(profile.id)} className="flex items-center justify-between rounded-xl border border-[#d6e3f3] px-4 py-3 text-left hover:border-[#3370ff] hover:bg-[#f7faff]">
                <span><span className="block text-sm font-semibold text-[#102033]">{profile.display_name || profile.app_id}</span><span className="mt-1 block text-xs text-[#71869d]">{profile.source === "official_registration" ? "自动创建" : "手动配置"} · {profile.brand === "lark" ? "Lark" : "飞书"}</span></span>
                <span className="text-sm font-semibold text-[#3370ff]">扫码登录</span>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <button type="button" className="mt-4 text-sm font-semibold text-[#52657a] underline-offset-4 hover:text-[#3370ff] hover:underline" onClick={() => setManualOpen((value) => !value)}>高级：手动填写 App ID / Secret</button>
      {manualOpen ? (
        <div className="mt-3 grid gap-3 rounded-2xl border border-[#d6e3f3] bg-white p-5">
          <input aria-label="App ID" value={appId} onChange={(event) => setAppId(event.target.value)} placeholder="cli_xxx" className="rounded-xl border border-[#c7d7ea] px-4 py-2.5 text-sm outline-none focus:border-[#3370ff]" />
          <input aria-label="App Secret" type="password" value={appSecret} onChange={(event) => setAppSecret(event.target.value)} placeholder="App Secret" className="rounded-xl border border-[#c7d7ea] px-4 py-2.5 text-sm outline-none focus:border-[#3370ff]" />
          <button type="button" disabled={busy} onClick={() => void saveManual()} className="w-fit rounded-lg bg-[#102033] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">保存并扫码登录</button>
        </div>
      ) : null}
      {error ? <p className="mt-4 rounded-xl border border-[#fecdd3] bg-[#fff1f2] px-4 py-3 text-sm text-[#be123c]">{error}</p> : null}
    </div>
  );
}
