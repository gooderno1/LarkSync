import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as QRCode from "qrcode";

import { apiFetch } from "../lib/api";
import type { AppProfile } from "../types";
import { useAccounts } from "../hooks/useAccounts";
import { IconCircleCheck } from "./Icons";

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
  | "app_registered"
  | "preparing_account_auth"
  | "authorizing_account"
  | "authorized"
  | "credential_storage_failed"
  | "failed"
  | "expired"
  | "denied";

type Props = {
  onConnected?: () => void;
  onCancel?: () => void;
  mode?: "add" | "reauthorize";
  accountId?: string;
};

type AuthorizedAccount = {
  id?: string;
  account_name?: string | null;
  auth_protocol?: string;
  tenant_name?: string | null;
  account_alias?: string | null;
  brand?: string;
};

type ConnectPath = "automatic" | "existing" | "manual" | "reauthorize";

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
  const { accounts, refreshAccounts, switchAccount } = useAccounts();
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
  const [createdProfileAppId, setCreatedProfileAppId] = useState<string | null>(null);
  const [connectPath, setConnectPath] = useState<ConnectPath>(mode === "reauthorize" ? "reauthorize" : "automatic");
  const [authorizedAccount, setAuthorizedAccount] = useState<AuthorizedAccount | null>(null);
  const [organizationNameDraft, setOrganizationNameDraft] = useState("");
  const [runtimeReloadPending, setRuntimeReloadPending] = useState(false);
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
          const profile = result.app_profile as AppProfile | undefined;
          if (!profile?.id) throw new Error("应用创建成功，但未取得应用配置");
          setCreatedProfileId(profile.id);
          setCreatedProfileAppId(profile.app_id || null);
          setSession(null);
          setSessionKind(null);
          setPhase("app_registered");
          await completionRef.current.refetchProfiles();
          return;
        }
        if (status === "authorized") {
          const authorized = (result.account as AuthorizedAccount | undefined) ?? null;
          setAuthorizedAccount(authorized);
          setOrganizationNameDraft(
            authorized?.account_alias
              || authorized?.tenant_name
              || (authorized?.brand === "lark" ? "Lark 组织" : "飞书组织"),
          );
          setError(null);
          setRuntimeReloadPending(Boolean(result.runtime_reload_pending));
          setPhase("authorized");
          setSession(null);
          setSessionKind(null);
          await completionRef.current.refetchProfiles();
          return;
        }
        if (status === "denied" || status === "expired") {
          setPhase(status);
          setError(status === "denied" ? "你取消了授权，可以重新开始当前步骤。" : "二维码已过期，请重新生成。 ");
          setSession(null);
          setSessionKind(null);
          return;
        }
        if (status === "credential_storage_failed") {
          setPhase("credential_storage_failed");
          setError(String(result.message || "飞书授权已完成，但新凭据未能安全保存。原授权仍保留。"));
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

  const beginRegistration = () => {
    setConnectPath("automatic");
    setCreatedProfileId(null);
    setCreatedProfileAppId(null);
    return startSession(
      "/app-profiles/registration-sessions",
      { brand: "feishu" },
      "registration",
      "registering_app",
    );
  };

  const beginDevice = (profileId: string) => startSession(
    "/auth/device-sessions",
    { app_profile_id: profileId },
    "device",
    "authorizing_account",
  );

  const beginExistingDevice = (profileId: string) => {
    setConnectPath("existing");
    setCreatedProfileId(profileId);
    return beginDevice(profileId);
  };

  const continueSecondScan = async () => {
    if (!createdProfileId) {
      setError("应用配置不存在，请重新开始第 1 次扫码。");
      return;
    }
    setConnectPath("automatic");
    setPhase("preparing_account_auth");
    await beginDevice(createdProfileId);
  };

  const beginReauthorize = () => {
    if (!accountId) {
      setError("缺少需要重新授权的账号。");
      return Promise.resolve(null);
    }
    setConnectPath("reauthorize");
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

  const finishAuthorized = async () => {
    const organizationName = organizationNameDraft.trim();
    if (mode === "add" && !organizationName) {
      setError("请填写用于区分账号的组织名称。");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const currentOrganizationName = authorizedAccount?.account_alias || authorizedAccount?.tenant_name || "";
      if (
        mode === "add"
        && authorizedAccount?.id
        && organizationName !== currentOrganizationName
      ) {
        await apiFetch(`/accounts/${authorizedAccount.id}/display`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ account_alias: organizationName }),
        });
      }
      await completionRef.current.refreshAccounts();
      if (mode === "add" && authorizedAccount?.id) {
        await switchAccount(authorizedAccount.id);
      }
      completionRef.current.onConnected?.();
    } catch (err) {
      setError(
        mode === "add"
          ? `账号授权已成功，仅组织名称保存或账号刷新失败：${err instanceof Error ? err.message : "请重试"}`
          : err instanceof Error ? err.message : "账号状态刷新失败，请重试",
      );
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
      setCreatedProfileId(profile.id);
      setCreatedProfileAppId(profile.app_id);
      setConnectPath("manual");
      await profiles.refetch();
      await beginDevice(profile.id);
    } catch (err) {
      setPhase("failed");
      setError(err instanceof Error ? err.message : "应用配置保存失败");
    } finally {
      setBusy(false);
    }
  };

  if (phase === "authorized") {
    const organizationName = authorizedAccount?.account_alias || authorizedAccount?.tenant_name || targetAccount?.account_alias || targetAccount?.tenant_name;
    const accountName = authorizedAccount?.account_name || targetAccount?.account_name || "飞书账号";
    return (
      <div data-account-connect-root="true" data-connect-phase="authorized">
        <div data-testid="authorization-success" className="rounded-2xl border border-[#a7e2cf] bg-[linear-gradient(135deg,#f2fbf8,#f7fbff)] p-6 text-center shadow-[0_16px_40px_rgba(16,185,129,0.10)]">
          <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-[#dcfce7] text-[#059669]">
            <IconCircleCheck className="h-8 w-8" />
          </span>
          <p className="mt-4 text-xs font-semibold uppercase tracking-[0.14em] text-[#047857]">Device Flow V2</p>
          <h2 className="mt-2 text-2xl font-semibold text-[#102033]">授权成功</h2>
          <p className="mt-2 text-sm leading-6 text-[#52657a]">
            {mode === "reauthorize"
              ? `${accountName} 已完成重新授权，原账号、任务、状态和历史数据保持不变。`
              : `${organizationName ? `${organizationName} · ` : ""}${accountName} 已连接到 LarkSync，可以开始创建同步任务。`}
          </p>
          <div className="mx-auto mt-4 flex w-fit items-center gap-2 rounded-full border border-[#b9e8d8] bg-white px-3 py-1.5 text-xs font-semibold text-[#047857]">
            <span className="h-2 w-2 rounded-full bg-[#10b981]" />
            凭据已安全保存
          </div>
          {mode === "add" ? (
            <label className="mx-auto mt-5 block max-w-md text-left text-xs font-semibold text-[#294662]">
              组织名称
              <input
                aria-label="组织名称"
                value={organizationNameDraft}
                maxLength={120}
                onChange={(event) => setOrganizationNameDraft(event.target.value)}
                className="mt-2 h-10 w-full rounded-xl border border-[#b9cfee] bg-white px-3 text-sm font-medium text-[#102033] outline-none focus:border-[#3370ff] focus:ring-2 focus:ring-[#3370ff]/15"
              />
              <span className="mt-2 block font-normal leading-5 text-[#71869d]">只用于在 LarkSync 中区分账号，可随时在设置中修改；不会更改飞书组织或同步权限。</span>
            </label>
          ) : null}
          {runtimeReloadPending ? <p className="mt-3 text-xs text-[#b45309]">授权信息已保存；后台连接将在下次启动时自动加载。</p> : null}
          {error ? <p className="mx-auto mt-3 max-w-md rounded-lg border border-[#fecdd3] bg-[#fff1f2] px-3 py-2 text-left text-xs leading-5 text-[#be123c]">{error}</p> : null}
          <button type="button" disabled={busy} onClick={() => void finishAuthorized()} className="mt-5 rounded-xl bg-[#3370ff] px-7 py-2.5 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(51,112,255,0.22)] disabled:opacity-50">
            {busy ? "正在完成…" : mode === "add" ? "进入该组织" : "完成"}
          </button>
        </div>
      </div>
    );
  }

  if (phase === "app_registered" && createdProfileId) {
    return (
      <div data-account-connect-root="true" data-connect-phase="app_registered">
        <div className="rounded-2xl border border-[#a7e2cf] bg-[linear-gradient(135deg,#f2fbf8,#f7fbff)] p-6 text-center shadow-[0_16px_40px_rgba(16,185,129,0.10)]">
          <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-[#dcfce7] text-[#059669]"><IconCircleCheck className="h-8 w-8" /></span>
          <p className="mt-4 text-xs font-semibold uppercase tracking-[0.14em] text-[#047857]">步骤 1 / 2 · 创建应用</p>
          <h2 className="mt-2 text-2xl font-semibold text-[#102033]">第 1 步已完成</h2>
          <p className="mt-2 text-sm leading-6 text-[#52657a]">LarkSync 个人应用已经创建并安全保存。接下来还需要第 2 次扫码，授权飞书账号和文档范围。</p>
          {createdProfileAppId ? <p className="mx-auto mt-4 w-fit rounded-full border border-[#b9e8d8] bg-white px-3 py-1.5 font-mono text-xs text-[#047857]">应用：{createdProfileAppId.slice(0, 8)}••••</p> : null}
          <p className="mt-3 text-xs leading-5 text-[#71869d]">飞书后台可能将官方快速注册应用显示为“CLI应用”，不影响 LarkSync 登录和同步。</p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            <button type="button" disabled={busy} onClick={() => void continueSecondScan()} className="rounded-xl bg-[#3370ff] px-6 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{busy ? "正在准备…" : "继续第 2 次扫码"}</button>
            <button type="button" onClick={() => setPhase("choose_method")} className="rounded-xl border border-[#cbd9ea] px-5 py-2.5 text-sm font-semibold text-[#52657a]">稍后继续</button>
          </div>
        </div>
      </div>
    );
  }

  if (session) {
    return (
      <div data-account-connect-root="true" data-connect-phase={phase} className="grid gap-5 md:grid-cols-[280px_minmax(0,1fr)]">
        <div className="rounded-2xl border border-[#d6e3f3] bg-white p-4 shadow-sm">
          <div data-testid="device-flow-qr-panel" data-qr-state={qrData ? "ready" : "loading"} className="grid aspect-square place-items-center rounded-xl bg-[#f5f9ff] p-3">
            {qrData ? <img data-testid="device-flow-qr-image" src={qrData} alt="飞书扫码授权二维码" className="h-full w-full" /> : <span className="text-sm text-[#71869d]">正在生成二维码…</span>}
          </div>
        </div>
        <div className="flex flex-col justify-center">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#3370ff]">{sessionKind === "registration" ? "步骤 1 / 2 · 创建应用" : connectPath === "automatic" ? "步骤 2 / 2 · 授权账号" : connectPath === "reauthorize" ? "重新授权 · 本次只扫码 1 次" : "账号授权 · 本次只扫码 1 次"}</p>
          <h2 className="mt-2 text-2xl font-semibold text-[#102033]">{sessionKind === "registration" ? "第 1 次扫码：创建 LarkSync 个人应用" : connectPath === "automatic" ? "第 2 次扫码：授权飞书账号" : connectPath === "reauthorize" ? "扫码重新授权飞书账号" : "扫码授权飞书账号"}</h2>
          {connectPath === "automatic" && sessionKind === "device" ? <p className="mt-3 rounded-lg bg-[#ecfdf5] px-3 py-2 text-xs font-semibold text-[#047857]">✓ 第 1 步已完成：个人应用已创建</p> : null}
          <p className="mt-3 text-sm leading-6 text-[#52657a]">{sessionKind === "registration" ? "本次扫码只用于创建应用配置，还没有授权你的文档。成功后仍需进行第 2 次扫码。" : "确认账号身份和权限后，本页会自动完成，不需要复制授权码。"}</p>
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
        {error ? <ErrorPanel message={error} busy={busy} storageFailure={phase === "credential_storage_failed"} onRetry={() => void retryCurrent()} /> : null}
      </div>
    );
  }

  return (
    <div data-account-connect-root="true" data-connect-phase={phase}>
      <div className="rounded-2xl border border-[#cfe0f5] bg-[linear-gradient(135deg,#f7fbff,#edf5ff)] p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#3370ff]">推荐 · 明确的两次扫码</p>
        <h2 className="mt-2 text-xl font-semibold text-[#102033]">自动创建应用并登录账号</h2>
        <div className="mt-3 grid gap-2 text-sm leading-6 text-[#52657a]"><p><strong className="text-[#102033]">第 1 次：</strong>创建供 LarkSync 使用的个人应用。</p><p><strong className="text-[#102033]">第 2 次：</strong>授权当前飞书账号和文档权限。</p></div>
        <p className="mt-2 text-xs text-[#71869d]">两次扫码用途不同。已有应用和手动配置都只需要扫码 1 次。</p>
        <button data-testid="start-two-step-connect" type="button" disabled={busy} onClick={() => void beginRegistration()} className="mt-4 rounded-xl bg-[#3370ff] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(51,112,255,0.22)] disabled:opacity-50">{busy ? "正在准备…" : "开始第 1 次扫码"}</button>
      </div>

      {(profiles.data?.length ?? 0) > 0 ? (
        <div className="mt-4 rounded-2xl border border-[#d6e3f3] bg-white p-5">
          <h3 className="font-semibold text-[#102033]">使用已有应用配置</h3>
          <p className="mt-1 text-xs text-[#71869d]">跳过应用创建，直接进入账号扫码。</p>
          <div className="mt-3 grid gap-2">
            {profiles.data?.map((profile) => (
              <button key={profile.id} type="button" disabled={busy} onClick={() => void beginExistingDevice(profile.id)} className="flex items-center justify-between rounded-xl border border-[#d6e3f3] px-4 py-3 text-left hover:border-[#3370ff] hover:bg-[#f7faff] disabled:opacity-50">
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
      {error ? <ErrorPanel message={error} busy={busy} storageFailure={phase === "credential_storage_failed"} onRetry={() => void retryCurrent()} /> : null}
    </div>
  );
}

function ErrorPanel({ message, busy, storageFailure, onRetry }: { message: string; busy: boolean; storageFailure: boolean; onRetry: () => void }) {
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#fecdd3] bg-[#fff1f2] px-4 py-3 text-sm text-[#be123c]">
      <span>{storageFailure ? <strong className="mb-1 block">飞书授权已完成</strong> : null}{message}</span>
      <button type="button" disabled={busy} onClick={onRetry} className="rounded-lg border border-[#fda4af] bg-white px-3 py-1.5 text-xs font-semibold disabled:opacity-50">{storageFailure ? "重新扫码授权" : "重试当前步骤"}</button>
    </div>
  );
}
