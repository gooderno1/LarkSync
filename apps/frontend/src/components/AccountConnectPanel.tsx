import { useEffect, useRef, useState } from "react";
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

type ConnectPhase =
  | "choose_method"
  | "registering_app"
  | "preparing_account_auth"
  | "authorizing_account"
  | "authorized"
  | "failed"
  | "expired"
  | "denied";

type Props = {
  onConnected?: () => void;
  onCancel?: () => void;
  mode?: "add" | "reauthorize";
  accountId?: string;
};

function sessionEndpoint(kind: "registration" | "device", sessionId: string) {
  return kind === "device"
    ? `/auth/device-sessions/${sessionId}`
    : `/app-profiles/registration-sessions/${sessionId}`;
}

export function AccountConnectPanel({
  onConnected,
  onCancel,
  mode = "add",
  accountId,
}: Props) {
  const { accounts, refreshAccounts } = useAccounts();
  const profiles = useQuery<AppProfile[]>({
    queryKey: ["app-profiles"],
    queryFn: () => apiFetch<AppProfile[]>("/app-profiles"),
  });
  const targetAccount = accounts.find((item) => item.id === accountId) ?? null;
  const [phase, setPhase] = useState<ConnectPhase>("choose_method");
  const [session, setSession] = useState<Session | null>(null);
  const [sessionKind, setSessionKind] = useState<"registration" | "device" | null>(null);
  const sessionRef = useRef<{ session: Session; kind: "registration" | "device" } | null>(null);
  const [qrData, setQrData] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);
  const [appId, setAppId] = useState("");
  const [appSecret, setAppSecret] = useState("");
  const [createdProfileId, setCreatedProfileId] = useState<string | null>(null);
  const beginDeviceRef = useRef<(profileId: string) => Promise<Session | null>>(async () => null);
  const completionRef = useRef({ refreshAccounts, refetchProfiles: profiles.refetch, onConnected });
  completionRef.current = { refreshAccounts, refetchProfiles: profiles.refetch, onConnected };

  useEffect(() => {
    sessionRef.current = session && sessionKind ? { session, kind: sessionKind } : null;
  }, [session, sessionKind]);

  useEffect(() => () => {
    const current = sessionRef.current;
    if (!current) return;
    void apiFetch(sessionEndpoint(current.kind, current.session.session_id), {
      method: "DELETE",
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!session?.verification_uri_complete) {
      setQrData(null);
      return;
    }
    let cancelled = false;
    setQrData(null);
    QRCode.toDataURL(session.verification_uri_complete, {
      width: 248,
      margin: 1,
      color: { dark: "#102033", light: "#ffffff" },
    })
      .then((value) => !cancelled && setQrData(value))
      .catch(() => !cancelled && setError("二维码生成失败，请使用浏览器打开授权页面。"));
    return () => {
      cancelled = true;
    };
  }, [session?.verification_uri_complete]);

  useEffect(() => {
    if (!session || !sessionKind) return;
    let stopped = false;
    let timer: number | null = null;
    const endpoint = sessionEndpoint(sessionKind, session.session_id);

    const schedule = (seconds: number) => {
      if (stopped) return;
      timer = window.setTimeout(() => void poll(), Math.max(1, seconds) * 1_000);
    };
    const poll = async () => {
      try {
        const result = await apiFetch<Record<string, unknown>>(endpoint);
        if (stopped) return;
        const status = String(result.status || "pending");
        if (["pending", "slow_down", "brand_switched"].includes(status)) {
          schedule(Number(result.retry_after) || session.interval);
          return;
        }
        if (status === "registered") {
          setPhase("preparing_account_auth");
          const profile = result.app_profile as AppProfile | undefined;
          if (profile?.id) setCreatedProfileId(profile.id);
          const nextSession = result.next_session as Session | undefined;
          if (nextSession?.session_id) {
            setSessionKind("device");
            setSession(nextSession);
            setPhase("authorizing_account");
            return;
          }
          if (profile?.id) {
            await beginDeviceRef.current(profile.id);
            return;
          }
          throw new Error("应用创建成功，但未取得账号登录会话");
        }
        if (status === "authorized") {
          setPhase("authorized");
          setSession(null);
          setSessionKind(null);
          await Promise.all([
            completionRef.current.refreshAccounts(),
            completionRef.current.refetchProfiles(),
          ]);
          completionRef.current.onConnected?.();
          return;
        }
        if (status === "denied" || status === "expired") {
          setPhase(status);
          setError(status === "denied" ? "你取消了授权，可以重新开始当前步骤。" : "二维码已过期，请重新生成。 ");
          setSession(null);
          setSessionKind(null);
          return;
        }
        throw new Error(String(result.message || "授权状态无法识别"));
      } catch (err) {
        if (stopped) return;
        setPhase("failed");
        setError(err instanceof Error ? err.message : "授权状态读取失败");
        setSession(null);
        setSessionKind(null);
      }
    };

    schedule(session.interval);
    return () => {
      stopped = true;
      if (timer != null) window.clearTimeout(timer);
    };
  }, [session, sessionKind]);

  const startSession = async (
    endpoint: string,
    body: Record<string, unknown> | null,
    kind: "registration" | "device",
    nextPhase: ConnectPhase,
  ) => {
    setBusy(true);
    setError(null);
    try {
      const value = await apiFetch<Session>(endpoint, {
        method: "POST",
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      setSessionKind(kind);
      setSession(value);
      setPhase(nextPhase);
      return value;
    } catch (err) {
      setPhase("failed");
      setError(err instanceof Error ? err.message : "授权会话启动失败");
      return null;
    } finally {
      setBusy(false);
    }
  };

  const beginRegistration = () => startSession(
    "/app-profiles/registration-sessions",
    { brand: "feishu" },
    "registration",
    "registering_app",
  );

  const beginDevice = (profileId: string) => startSession(
    "/auth/device-sessions",
    { app_profile_id: profileId },
    "device",
    "authorizing_account",
  );
  beginDeviceRef.current = beginDevice;

  const beginReauthorize = () => {
    if (!accountId) {
      setError("缺少需要重新授权的账号。");
      return Promise.resolve(null);
    }
    return startSession(
      `/accounts/${accountId}/reauthorize-sessions`,
      null,
      "device",
      "authorizing_account",
    );
  };

  const cancelCurrent = async () => {
    if (session && sessionKind) {
      await apiFetch(sessionEndpoint(sessionKind, session.session_id), { method: "DELETE" }).catch(() => undefined);
    }
    setSession(null);
    setSessionKind(null);
    setPhase("choose_method");
    setError(null);
    onCancel?.();
  };

  const retryCurrent = () => {
    if (mode === "reauthorize") return beginReauthorize();
    if (createdProfileId) return beginDevice(createdProfileId);
    setPhase("choose_method");
    setError(null);
    return Promise.resolve(null);
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
      setCreatedProfileId(profile.id);
      await profiles.refetch();
      await beginDevice(profile.id);
    } catch (err) {
      setPhase("failed");
      setError(err instanceof Error ? err.message : "应用配置保存失败");
    } finally {
      setBusy(false);
    }
  };

  if (session) {
    return (
      <div data-account-connect-root="true" data-connect-phase={phase} className="grid gap-5 md:grid-cols-[280px_minmax(0,1fr)]">
        <div className="rounded-2xl border border-[#d6e3f3] bg-white p-4 shadow-sm">
          <div data-testid="device-flow-qr-panel" data-qr-state={qrData ? "ready" : "loading"} className="grid aspect-square place-items-center rounded-xl bg-[#f5f9ff] p-3">
            {qrData ? <img data-testid="device-flow-qr-image" src={qrData} alt="飞书扫码授权二维码" className="h-full w-full" /> : <span className="text-sm text-[#71869d]">正在生成二维码…</span>}
          </div>
        </div>
        <div className="flex flex-col justify-center">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#3370ff]">{sessionKind === "registration" ? "步骤 1 / 2 · 创建个人应用" : mode === "reauthorize" ? "重新授权账号" : "步骤 2 / 2 · 登录账号"}</p>
          <h2 className="mt-2 text-2xl font-semibold text-[#102033]">使用飞书扫码确认</h2>
          <p className="mt-3 text-sm leading-6 text-[#52657a]">{sessionKind === "registration" ? "第一次扫码用于创建 LarkSync 个人应用，完成后会自动显示第二个登录二维码。" : "确认后本页会自动完成，不需要复制授权码。"}</p>
          {session.user_code ? <div className="mt-4 rounded-xl border border-[#d6e3f3] bg-[#f7faff] px-4 py-3 font-mono text-sm text-[#102033]">备用验证码：{session.user_code}</div> : null}
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" className="rounded-lg border border-[#b9cce2] px-4 py-2 text-sm font-semibold text-[#3370ff] hover:bg-[#eef5ff]" onClick={() => window.open(session.verification_uri_complete, "_blank", "noopener,noreferrer")}>在浏览器中打开</button>
            <button type="button" className="rounded-lg border border-[#cbd9ea] px-4 py-2 text-sm font-semibold text-[#52657a] hover:bg-white" onClick={() => void cancelCurrent()}>取消当前步骤</button>
          </div>
        </div>
      </div>
    );
  }

  if (mode === "reauthorize") {
    return (
      <div data-account-connect-root="true" data-connect-phase={phase}>
        <div className="rounded-2xl border border-[#cfe0f5] bg-[linear-gradient(135deg,#f7fbff,#edf5ff)] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#3370ff]">账号授权升级</p>
          <h2 className="mt-2 text-xl font-semibold text-[#102033]">重新授权 {targetAccount?.account_name || "飞书账号"}</h2>
          <p className="mt-2 text-sm leading-6 text-[#52657a]">将使用当前账号绑定的应用配置重新扫码。成功后原账号、任务和历史数据保持不变；如果扫码身份不同，LarkSync 会停止覆盖并提示处理。</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" disabled={busy} onClick={() => void beginReauthorize()} className="rounded-xl bg-[#3370ff] px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{busy ? "正在准备…" : "开始重新授权"}</button>
            {onCancel ? <button type="button" onClick={onCancel} className="rounded-xl border border-[#cbd9ea] px-5 py-2.5 text-sm font-semibold text-[#52657a]">取消</button> : null}
          </div>
        </div>
        {error ? <ErrorPanel message={error} busy={busy} onRetry={() => void retryCurrent()} /> : null}
      </div>
    );
  }

  return (
    <div data-account-connect-root="true" data-connect-phase={phase}>
      <div className="rounded-2xl border border-[#cfe0f5] bg-[linear-gradient(135deg,#f7fbff,#edf5ff)] p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#3370ff]">推荐 · 两步扫码</p>
        <h2 className="mt-2 text-xl font-semibold text-[#102033]">自动创建应用并登录账号</h2>
        <p className="mt-2 text-sm leading-6 text-[#52657a]">第一次扫码创建个人应用，第二次扫码登录账号。两个步骤会在当前窗口连续完成。</p>
        <button type="button" disabled={busy} onClick={() => void beginRegistration()} className="mt-4 rounded-xl bg-[#3370ff] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(51,112,255,0.22)] disabled:opacity-50">{busy ? "正在准备…" : "开始两步扫码"}</button>
      </div>

      {(profiles.data?.length ?? 0) > 0 ? (
        <div className="mt-4 rounded-2xl border border-[#d6e3f3] bg-white p-5">
          <h3 className="font-semibold text-[#102033]">使用已有应用配置</h3>
          <p className="mt-1 text-xs text-[#71869d]">跳过应用创建，直接进入账号扫码。</p>
          <div className="mt-3 grid gap-2">
            {profiles.data?.map((profile) => (
              <button key={profile.id} type="button" disabled={busy} onClick={() => void beginDevice(profile.id)} className="flex items-center justify-between rounded-xl border border-[#d6e3f3] px-4 py-3 text-left hover:border-[#3370ff] hover:bg-[#f7faff] disabled:opacity-50">
                <span><span className="block text-sm font-semibold text-[#102033]">{profile.display_name || profile.app_id}</span><span className="mt-1 block text-xs text-[#71869d]">{profile.source === "official_registration" ? "自动创建" : profile.source === "legacy" ? "升级迁移" : "手动配置"} · {profile.brand === "lark" ? "Lark" : "飞书"}</span></span>
                <span className="text-sm font-semibold text-[#3370ff]">扫码登录</span>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <button type="button" className="mt-4 text-sm font-semibold text-[#52657a] underline-offset-4 hover:text-[#3370ff] hover:underline" onClick={() => setManualOpen((value) => !value)}>高级：手动填写或更新 App ID / Secret</button>
      {manualOpen ? (
        <div className="mt-3 grid gap-3 rounded-2xl border border-[#d6e3f3] bg-white p-5">
          <input aria-label="App ID" value={appId} onChange={(event) => setAppId(event.target.value)} placeholder="cli_xxx" className="rounded-xl border border-[#c7d7ea] px-4 py-2.5 text-sm outline-none focus:border-[#3370ff]" />
          <input aria-label="App Secret" type="password" value={appSecret} onChange={(event) => setAppSecret(event.target.value)} placeholder="App Secret" className="rounded-xl border border-[#c7d7ea] px-4 py-2.5 text-sm outline-none focus:border-[#3370ff]" />
          <button type="button" disabled={busy} onClick={() => void saveManual()} className="w-fit rounded-lg bg-[#102033] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">保存并扫码登录</button>
        </div>
      ) : null}
      {error ? <ErrorPanel message={error} busy={busy} onRetry={() => void retryCurrent()} /> : null}
    </div>
  );
}

function ErrorPanel({ message, busy, onRetry }: { message: string; busy: boolean; onRetry: () => void }) {
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#fecdd3] bg-[#fff1f2] px-4 py-3 text-sm text-[#be123c]">
      <span>{message}</span>
      <button type="button" disabled={busy} onClick={onRetry} className="rounded-lg border border-[#fda4af] bg-white px-3 py-1.5 text-xs font-semibold disabled:opacity-50">重试当前步骤</button>
    </div>
  );
}
