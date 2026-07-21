/* ------------------------------------------------------------------ */
/*  连接飞书工作区 — 启动状态 + OAuth 配置 + 授权二维码                    */
/* ------------------------------------------------------------------ */

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as QRCode from "qrcode";
import { useConfig } from "../hooks/useConfig";
import { useAuth } from "../hooks/useAuth";
import { useDesktopStatus } from "../hooks/useDesktopStatus";
import { apiFetch, getCurrentAppUrl, getLoginUrl } from "../lib/api";
import { useToast } from "./ui/toast";
import {
  IconBrowser,
  IconCloud,
  IconCopy,
  IconExternalLink,
  IconRefresh,
  IconSettings,
} from "./Icons";
import { ThemeToggle } from "./ThemeToggle";
import { cn } from "../lib/utils";

const FEISHU_AUTHORIZE_URL = "https://open.feishu.cn/open-apis/authen/v1/index";
const FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v1/access_token";

type Props = {
  oauthConfigured: boolean;
  connected: boolean;
};

type AuthorizeUrlResponse = {
  authorize_url: string;
  state: string;
  expires_in: number;
  local_callback: boolean;
};

type LarkCliUserStatus = {
  available: boolean;
  verified: boolean;
  status?: string | null;
  token_status?: string | null;
  user_name?: string | null;
  open_id_present: boolean;
  scope_count: number;
  docs_scope_detected: boolean;
  drive_scope_detected: boolean;
  expires_at?: string | null;
  refresh_expires_at?: string | null;
};

type LarkCliAuthStatus = {
  installed: boolean;
  executable?: string | null;
  brand?: string | null;
  identity?: string | null;
  verified: boolean;
  user?: LarkCliUserStatus | null;
  can_assist_oauth: boolean;
  message: string;
  last_error?: string | null;
  status_command: string;
  login_command: string;
  qrcode_command: string;
};

type StatusTone = "success" | "warning" | "danger" | "info" | "neutral";

function getRedirectUri(): string {
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  return `${origin}/auth/callback`;
}

function getLoginRedirect(): string {
  return getCurrentAppUrl() || "/";
}

export function OnboardingWizard({ oauthConfigured, connected }: Props) {
  const { config, saveConfig, saving } = useConfig();
  const { accountName, deviceId } = useAuth();
  const {
    status: desktopStatus,
    error: desktopStatusError,
    isFetching: desktopStatusFetching,
    refetch: refetchDesktopStatus,
  } = useDesktopStatus();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const loginUrl = getLoginUrl();
  const redirectUri = useMemo(() => getRedirectUri(), []);
  const loginRedirect = useMemo(() => getLoginRedirect(), []);
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(!oauthConfigured);
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [qrError, setQrError] = useState<string | null>(null);

  useEffect(() => {
    if (config.auth_client_id?.trim() && !clientId.trim()) {
      setClientId(config.auth_client_id.trim());
    }
  }, [clientId, config.auth_client_id]);

  useEffect(() => {
    if (!oauthConfigured) setAdvancedOpen(true);
  }, [oauthConfigured]);

  const authorizeQuery = useQuery<AuthorizeUrlResponse>({
    queryKey: ["auth-authorize-url", loginRedirect],
    queryFn: () => {
      const params = new URLSearchParams();
      params.set("redirect", loginRedirect);
      return apiFetch<AuthorizeUrlResponse>(`/auth/authorize-url?${params.toString()}`);
    },
    enabled: oauthConfigured && !connected,
    retry: false,
    staleTime: 60_000,
  });
  const larkCliQuery = useQuery<LarkCliAuthStatus>({
    queryKey: ["auth-cli-status"],
    queryFn: () => apiFetch<LarkCliAuthStatus>("/auth/cli/status"),
    retry: false,
    staleTime: 30_000,
  });

  const authorizeUrl = authorizeQuery.data?.authorize_url ?? "";
  const larkCliStatus = larkCliQuery.data;

  useEffect(() => {
    let cancelled = false;
    setQrError(null);
    if (!authorizeUrl) {
      setQrDataUrl(null);
      return;
    }
    QRCode.toDataURL(authorizeUrl, {
      errorCorrectionLevel: "M",
      margin: 1,
      width: 236,
      color: {
        dark: "#102033",
        light: "#ffffff",
      },
    })
      .then((value) => {
        if (!cancelled) setQrDataUrl(value);
      })
      .catch((err) => {
        if (!cancelled) {
          setQrDataUrl(null);
          setQrError(err instanceof Error ? err.message : "二维码生成失败");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [authorizeUrl]);

  const authState = connected ? "ready" : oauthConfigured ? "authorize" : "configure";

  const handleSaveOAuth = async () => {
    if (!clientId.trim()) {
      setSaveError("请填写 App ID。");
      return;
    }
    if (!clientSecret.trim() && !oauthConfigured) {
      setSaveError("请填写 App Secret。");
      return;
    }
    setSaveError(null);
    try {
      const payload: Record<string, unknown> = {
        auth_client_id: clientId.trim(),
        auth_redirect_uri: redirectUri,
        auth_authorize_url: FEISHU_AUTHORIZE_URL,
        auth_token_url: FEISHU_TOKEN_URL,
      };
      if (clientSecret.trim()) {
        payload.auth_client_secret = clientSecret.trim();
      }
      await saveConfig(payload);
      setClientSecret("");
      setAdvancedOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["config"] });
      await queryClient.invalidateQueries({ queryKey: ["auth-authorize-url"] });
      toast("OAuth 配置已保存", "success");
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "保存失败");
    }
  };

  const copyText = async (text: string, successMessage: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast(successMessage, "success");
    } catch {
      toast("复制失败", "danger");
    }
  };

  const refreshAuth = async () => {
    await queryClient.invalidateQueries({ queryKey: ["auth-status"] });
    await queryClient.invalidateQueries({ queryKey: ["auth-authorize-url"] });
    await refetchDesktopStatus();
    toast("已刷新授权状态", "info");
  };

  const frontendRuntime = getFrontendRuntimeStatus(
    desktopStatus.runtime.frontend_static_available,
    desktopStatus.runtime.packaged
  );
  const windowHost = getWindowHostStatus();

  return (
    <div className="grid h-full grid-rows-[64px_minmax(0,1fr)] overflow-hidden bg-[linear-gradient(180deg,#f5f9ff_0%,#eef5ff_100%)] text-[#102033]">
      <header className="flex h-16 items-center justify-between border-b border-[#d7e6ff] bg-white/88 px-6 backdrop-blur-xl">
        <div className="flex min-w-0 items-center gap-4">
          <img src="/logo-horizontal.png" alt="LarkSync" className="h-8 w-auto object-contain" draggable={false} />
          <div className="h-6 w-px bg-[#d7e6ff]" />
          <div className="min-w-0">
            <h1 className="truncate text-lg font-semibold text-[#102033]">连接飞书工作区</h1>
            <p className="truncate text-xs text-[#6b7f96]">配置 OAuth 并完成飞书账号授权</p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <StatusBadge label={connected ? "飞书已连接" : "飞书未连接"} tone={connected ? "success" : "warning"} />
          <ThemeToggle />
        </div>
      </header>

      <main className="grid min-h-0 grid-cols-[310px_minmax(0,1fr)_360px] gap-5 overflow-hidden px-6 py-6">
        <aside className="showcase-scroll-region min-h-0 min-w-0 space-y-4 overflow-y-auto pr-1" data-onboarding-scroll-column="status">
          <Panel
            title="启动状态"
            hint="逐项确认桌面应用卡在哪一步。"
            action={
              <button
                className="inline-flex items-center gap-1.5 rounded-lg border border-[#c9d8ec] px-2.5 py-1 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]"
                onClick={() => void refetchDesktopStatus()}
                type="button"
              >
                <IconRefresh className={cn("h-3.5 w-3.5", desktopStatusFetching && "animate-spin")} />
                诊断
              </button>
            }
          >
            <div className="space-y-3">
              <StatusRow label="窗口宿主" value={windowHost.value} tone={windowHost.tone} />
              <StatusRow label="后端服务" value={desktopStatus.runtime.backend_running ? "运行中" : "启动失败"} tone={desktopStatus.runtime.backend_running ? "success" : "danger"} />
              <StatusRow label="前端资源" value={frontendRuntime.value} tone={frontendRuntime.tone} />
              <StatusRow label="运行模式" value={desktopStatus.runtime.packaged ? "安装版" : "开发模式"} tone="info" />
              <StatusRow label="OAuth 应用" value={oauthConfigured ? "已配置" : "待配置"} tone={oauthConfigured ? "success" : "warning"} />
              <StatusRow label="授权连接" value={connected ? "已连接" : "待授权"} tone={connected ? "success" : "warning"} />
              <StatusRow label="当前设备" value={deviceId || "待识别"} tone="info" mono />
              <StatusRow label="数据目录" value={shortRuntimePath(desktopStatus.runtime.data_dir || "待识别")} tone="neutral" mono />
            </div>
            {desktopStatusError ? (
              <p className="mt-3 rounded-lg border border-[#f43f5e]/30 bg-[#fff1f2] px-3 py-2 text-xs leading-5 text-[#be123c]">
                桌面诊断读取失败：{desktopStatusError}
              </p>
            ) : null}
          </Panel>

          <Panel title="当前结论">
            <div className="rounded-xl border border-[#d7e4f5] bg-[#f6faff] p-3">
              <p className="text-sm font-semibold text-[#102033]">{getStateTitle(authState)}</p>
              <p className="mt-2 text-xs leading-5 text-[#52657a]">{getStateHint(authState)}</p>
            </div>
          </Panel>
        </aside>

        <section className="showcase-scroll-region min-h-0 min-w-0 space-y-5 overflow-y-auto pr-1" data-onboarding-scroll-column="authorization">
          <Panel
            title="扫码授权"
            hint="二维码承载 LarkSync 原生 OAuth 授权 URL；浏览器打开是可靠 fallback。"
            action={
              <button
                className="inline-flex items-center gap-2 rounded-lg border border-[#c9d8ec] px-3 py-1.5 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]"
                onClick={refreshAuth}
                type="button"
              >
                <IconRefresh className="h-3.5 w-3.5" />
                刷新状态
              </button>
            }
          >
            <div className="grid grid-cols-[280px_minmax(0,1fr)] gap-5">
              <div className="rounded-lg border border-[#d7e4f5] bg-[#f8fbff] p-4">
                <div className="grid aspect-square place-items-center rounded-xl border border-[#d7e4f5] bg-white p-3">
                  {!oauthConfigured ? (
                    <QrPlaceholder title="待配置" hint="保存 App ID 和 App Secret 后生成二维码" />
                  ) : authorizeQuery.isLoading ? (
                    <QrPlaceholder title="生成中" hint="正在获取授权 URL" loading />
                  ) : authorizeQuery.error ? (
                    <QrPlaceholder title="生成失败" hint={authorizeQuery.error.message} tone="danger" />
                  ) : qrDataUrl ? (
                    <img src={qrDataUrl} alt="飞书 OAuth 授权二维码" className="h-full w-full object-contain" draggable={false} />
                  ) : (
                    <QrPlaceholder title="暂无二维码" hint={qrError || "授权 URL 尚未生成"} tone={qrError ? "danger" : "neutral"} />
                  )}
                </div>
                {authorizeQuery.data?.local_callback ? (
                  <p className="mt-3 rounded-lg border border-[#f59e0b]/35 bg-[#fffbeb] px-3 py-2 text-xs leading-5 text-[#92400e]">
                    当前回调地址是本机地址。若手机扫码后无法回跳，请使用本机浏览器打开授权。
                  </p>
                ) : null}
              </div>

              <div className="min-w-0 space-y-4">
                <div className="rounded-lg border border-[#d7e4f5] bg-white p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase tracking-widest text-[#7a8da3]">Primary Action</p>
                      <h2 className="mt-2 text-2xl font-semibold text-[#102033]">连接飞书工作区</h2>
                      <p className="mt-2 max-w-2xl text-sm leading-6 text-[#52657a]">
                        不创建 LarkSync 账号。授权成功后，本机通过加密凭证访问你允许的飞书云文档范围。
                      </p>
                    </div>
                    <StatusBadge label={getStateBadge(authState)} tone={getStateTone(authState)} />
                  </div>

                  <div className="mt-5 flex flex-wrap gap-2">
                    <a
                      className="inline-flex h-10 items-center gap-2 rounded-lg bg-[#3370ff] px-5 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(51,112,255,0.22)] hover:bg-[#1d4ed8]"
                      href={authorizeUrl || loginUrl}
                    >
                      <IconBrowser className="h-4 w-4" />
                      在浏览器打开
                    </a>
                    <button
                      className="inline-flex h-10 items-center gap-2 rounded-lg border border-[#c9d8ec] bg-white px-4 text-sm font-semibold text-[#3370ff] hover:bg-[#eef5ff] disabled:opacity-50"
                      disabled={!authorizeUrl}
                      onClick={() => authorizeUrl && copyText(authorizeUrl, "授权链接已复制")}
                      type="button"
                    >
                      <IconCopy className="h-4 w-4" />
                      复制授权链接
                    </button>
                    <button
                      className="inline-flex h-10 items-center gap-2 rounded-lg border border-[#c9d8ec] bg-white px-4 text-sm font-semibold text-[#334762] hover:bg-[#f6faff]"
                      onClick={() => setAdvancedOpen(true)}
                      type="button"
                    >
                      <IconSettings className="h-4 w-4" />
                      OAuth 配置
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <StepCard title="1. 配置应用" state={oauthConfigured ? "完成" : "待处理"} done={oauthConfigured} />
                  <StepCard title="2. 扫码授权" state={connected ? "完成" : "等待"} done={connected} />
                  <StepCard title="3. 进入工作台" state={connected ? "就绪" : "等待"} done={connected} />
                </div>
              </div>
            </div>
          </Panel>

          {connected ? (
            <Panel title="授权完成">
              <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-[#10b981]/25 bg-[#ecfdf5] p-4">
                <div>
                  <p className="text-sm font-semibold text-[#047857]">飞书连接可用</p>
                  <p className="mt-1 text-xs text-[#52657a]">账号：{accountName || "已连接（昵称未同步）"}</p>
                </div>
                <button
                  className="rounded-lg bg-[#3370ff] px-4 py-2 text-sm font-semibold text-white hover:bg-[#1d4ed8]"
                  onClick={() => window.location.reload()}
                  type="button"
                >
                  进入总览
                </button>
              </div>
            </Panel>
          ) : null}
        </section>

        <aside className="showcase-scroll-region min-h-0 min-w-0 space-y-4 overflow-y-auto pr-1" data-onboarding-scroll-column="advanced">
          <Panel
            title="高级 OAuth 配置"
            hint={advancedOpen ? "填写飞书企业自建应用参数。" : "配置已收起，可随时修改。"}
            action={
              <button
                className="text-xs font-semibold text-[#3370ff]"
                onClick={() => setAdvancedOpen((value) => !value)}
                type="button"
              >
                {advancedOpen ? "收起" : "展开"}
              </button>
            }
          >
            {advancedOpen ? (
              <div className="space-y-4">
                <Field label="App ID">
                  <input
                    className={inputClassName}
                    placeholder="cli_xxxxxxxxxxxx"
                    value={clientId}
                    onChange={(event) => setClientId(event.target.value)}
                  />
                </Field>
                <Field label="App Secret">
                  <input
                    className={inputClassName}
                    placeholder={oauthConfigured ? "留空则不修改已保存密钥" : "输入后保存到本地加密存储"}
                    type="password"
                    value={clientSecret}
                    onChange={(event) => setClientSecret(event.target.value)}
                  />
                </Field>
                <Field label="Redirect URI">
                  <div className="flex gap-2">
                    <input className={`${inputClassName} font-mono text-xs`} value={redirectUri} readOnly />
                    <button
                      className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-[#c9d8ec] px-3 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]"
                      onClick={() => copyText(redirectUri, "Redirect URI 已复制")}
                      type="button"
                    >
                      <IconCopy className="h-3.5 w-3.5" />
                      复制
                    </button>
                  </div>
                </Field>
                {saveError ? <p className="rounded-lg border border-[#f43f5e]/30 bg-[#fff1f2] px-3 py-2 text-xs text-[#be123c]">{saveError}</p> : null}
                <button
                  className="h-10 w-full rounded-lg bg-[#3370ff] text-sm font-semibold text-white hover:bg-[#1d4ed8] disabled:opacity-50"
                  disabled={saving}
                  onClick={handleSaveOAuth}
                  type="button"
                >
                  {saving ? "保存中..." : "保存配置"}
                </button>
              </div>
            ) : (
              <div className="rounded-xl border border-[#d7e4f5] bg-[#f6faff] p-3 text-xs leading-5 text-[#52657a]">
                当前 App ID：<span className="font-mono text-[#102033]">{config.auth_client_id || "未配置"}</span>
              </div>
            )}
          </Panel>

          <Panel
            title="CLI 辅助授权"
            hint="读取本机 lark-cli 登录态，只做辅助诊断，不导入 CLI token。"
            action={
              <button
                className="inline-flex items-center gap-1.5 rounded-lg border border-[#c9d8ec] px-2.5 py-1 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]"
                onClick={() => void larkCliQuery.refetch()}
                type="button"
              >
                <IconRefresh className={cn("h-3.5 w-3.5", larkCliQuery.isFetching && "animate-spin")} />
                检测
              </button>
            }
          >
            <div className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[#d7e4f5] bg-[#f8fbff] px-3 py-3">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-[#102033]">{getLarkCliTitle(larkCliStatus, larkCliQuery.isLoading, larkCliQuery.error)}</p>
                  <p className="mt-1 text-xs leading-5 text-[#52657a]">
                    {larkCliQuery.error instanceof Error ? larkCliQuery.error.message : larkCliStatus?.message || "正在读取本机 CLI 状态。"}
                  </p>
                </div>
                <StatusBadge
                  label={getLarkCliBadge(larkCliStatus, larkCliQuery.isLoading, larkCliQuery.error)}
                  tone={getLarkCliTone(larkCliStatus, larkCliQuery.isLoading, larkCliQuery.error)}
                />
              </div>

              {larkCliStatus ? (
                <div className="grid gap-2">
                  <StatusRow label="安装状态" value={larkCliStatus.installed ? `已检测：${larkCliStatus.executable || "lark-cli"}` : "未安装"} tone={larkCliStatus.installed ? "success" : "warning"} />
                  <StatusRow label="当前身份" value={larkCliStatus.identity || "未知"} tone={larkCliStatus.identity === "user" ? "success" : "info"} />
                  <StatusRow label="用户身份" value={larkCliStatus.user?.user_name || (larkCliStatus.user?.available ? "可用" : "不可用")} tone={larkCliStatus.user?.available ? "success" : "warning"} />
                  <StatusRow label="docs 权限" value={larkCliStatus.user?.docs_scope_detected ? "已检测" : "未检测"} tone={larkCliStatus.user?.docs_scope_detected ? "success" : "warning"} />
                  <StatusRow label="drive 权限" value={larkCliStatus.user?.drive_scope_detected ? "已检测" : "未检测"} tone={larkCliStatus.user?.drive_scope_detected ? "success" : "warning"} />
                  <StatusRow label="scope 数量" value={`${larkCliStatus.user?.scope_count ?? 0}`} tone="info" />
                </div>
              ) : null}

              <DiagnosticCommand
                label="检查 CLI 登录状态"
                command={larkCliStatus?.status_command || "lark-cli auth status --json --verify"}
                onCopy={(command) => copyText(command, "CLI 状态命令已复制")}
              />
              <DiagnosticCommand
                label="生成设备码授权"
                command={larkCliStatus?.login_command || "lark-cli auth login --domain docs --domain drive --no-wait --json"}
                onCopy={(command) => copyText(command, "CLI 设备码命令已复制")}
              />
              <DiagnosticCommand
                label="生成二维码"
                command={larkCliStatus?.qrcode_command || 'lark-cli auth qrcode "<verification_url>" --output larksync-cli-auth.png'}
                onCopy={(command) => copyText(command, "CLI 二维码命令已复制")}
              />
              <p className="rounded-lg border border-[#d7e4f5] bg-[#f6faff] px-3 py-2 text-xs leading-5 text-[#52657a]">
                当前主流程仍使用 LarkSync 原生 OAuth 和本地加密凭证。CLI 状态只用于降低后续设备码授权方案的验证成本。
              </p>
            </div>
          </Panel>

          <a
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-[#d7e4f5] bg-white px-4 py-3 text-sm font-semibold text-[#3370ff] hover:bg-[#eef5ff]"
            href="/oauth-guide.html"
            target="_blank"
            rel="noopener noreferrer"
          >
            <IconExternalLink className="h-4 w-4" />
            打开 OAuth 配置指南
          </a>
        </aside>
      </main>
    </div>
  );
}

const inputClassName =
  "w-full rounded-lg border border-[#c9d8ec] bg-white px-3 py-2 text-sm text-[#102033] outline-none placeholder:text-[#9fb2c8] focus:border-[#3370ff]";

function getFrontendRuntimeStatus(
  staticAvailable: boolean,
  packaged: boolean
): { value: string; tone: StatusTone } {
  if (staticAvailable) return { value: "生产静态", tone: "success" };
  if (!packaged) return { value: "开发服务", tone: "info" };
  return { value: "静态缺失", tone: "danger" };
}

function getWindowHostStatus(): { value: string; tone: StatusTone } {
  if (typeof window !== "undefined" && "pywebview" in window) {
    return { value: "桌面窗口", tone: "success" };
  }
  return { value: "浏览器/开发预览", tone: "info" };
}

function shortRuntimePath(path: string): string {
  if (path.length <= 32) return path;
  return `...${path.slice(-29)}`;
}

function Panel({
  title,
  hint,
  action,
  children,
}: {
  title: string;
  hint?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="min-w-0 rounded-xl border border-[#d7e4f5] bg-white p-4 shadow-[0_16px_40px_rgba(51,112,255,0.06)]">
      <div className="mb-4 flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-[#102033]">{title}</h2>
          {hint ? <p className="mt-1 text-xs leading-5 text-[#6b7f96]">{hint}</p> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
      {children}
    </section>
  );
}

function StatusBadge({ label, tone }: { label: string; tone: StatusTone }) {
  const styles =
    tone === "success" ? "border-[#10b981]/25 bg-[#ecfdf5] text-[#047857]" :
      tone === "warning" ? "border-[#f59e0b]/35 bg-[#fffbeb] text-[#b45309]" :
        tone === "danger" ? "border-[#f43f5e]/30 bg-[#fff1f2] text-[#be123c]" :
          tone === "info" ? "border-[#3370ff]/25 bg-[#eef5ff] text-[#1d4ed8]" :
            "border-[#c9d8ec] bg-white text-[#52657a]";
  return (
    <span className={`inline-flex items-center gap-2 whitespace-nowrap rounded-full border px-3 py-1 text-xs font-semibold ${styles}`}>
      <span className="h-2 w-2 rounded-full bg-current" />
      {label}
    </span>
  );
}

function StatusRow({
  label,
  value,
  tone,
  mono = false,
}: {
  label: string;
  value: string;
  tone: StatusTone;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-[#edf3fb] bg-[#f8fbff] px-3 py-2">
      <span className="text-xs text-[#6b7f96]">{label}</span>
      <span className={cn("truncate text-right text-xs font-semibold text-[#102033]", mono && "font-mono")}>
        {value}
      </span>
      <span
        className={cn(
          "h-2 w-2 shrink-0 rounded-full",
          tone === "success" ? "bg-[#10b981]" :
            tone === "warning" ? "bg-[#f59e0b]" :
              tone === "danger" ? "bg-[#f43f5e]" :
                tone === "info" ? "bg-[#3370ff]" : "bg-[#9fb2c8]"
        )}
      />
    </div>
  );
}

function QrPlaceholder({
  title,
  hint,
  tone = "neutral",
  loading = false,
}: {
  title: string;
  hint: string;
  tone?: "neutral" | "danger";
  loading?: boolean;
}) {
  return (
    <div className="grid h-full w-full place-items-center text-center">
      <div>
        <div className={cn("mx-auto grid h-14 w-14 place-items-center rounded-xl", tone === "danger" ? "bg-[#fff1f2] text-[#be123c]" : "bg-[#eef5ff] text-[#3370ff]")}>
          {loading ? <span className="h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent" /> : <IconCloud className="h-7 w-7" />}
        </div>
        <p className="mt-3 text-sm font-semibold text-[#102033]">{title}</p>
        <p className="mt-1 text-xs leading-5 text-[#6b7f96]">{hint}</p>
      </div>
    </div>
  );
}

function StepCard({
  title,
  state,
  done,
  danger = false,
}: {
  title: string;
  state: string;
  done: boolean;
  danger?: boolean;
}) {
  return (
    <div className={cn("rounded-xl border p-3", danger ? "border-[#f43f5e]/30 bg-[#fff1f2]" : done ? "border-[#10b981]/25 bg-[#ecfdf5]" : "border-[#d7e4f5] bg-[#f8fbff]")}>
      <p className="text-xs text-[#6b7f96]">{title}</p>
      <p className={cn("mt-2 text-sm font-semibold", danger ? "text-[#be123c]" : done ? "text-[#047857]" : "text-[#52657a]")}>{state}</p>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-xs font-semibold text-[#52657a]">
      {label}
      <div className="mt-1.5">{children}</div>
    </label>
  );
}

function DiagnosticCommand({
  label,
  command,
  onCopy,
}: {
  label: string;
  command: string;
  onCopy: (command: string) => void;
}) {
  return (
    <div className="rounded-lg border border-[#d7e4f5] bg-[#f8fbff] p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold text-[#102033]">{label}</p>
        <button className="text-xs font-semibold text-[#3370ff]" onClick={() => onCopy(command)} type="button">
          复制
        </button>
      </div>
      <p className="mt-2 break-all font-mono text-xs leading-5 text-[#52657a]">{command}</p>
    </div>
  );
}

function getLarkCliTitle(
  status: LarkCliAuthStatus | undefined,
  loading: boolean,
  error: unknown
): string {
  if (loading) return "正在检测 lark-cli";
  if (error) return "CLI 状态读取失败";
  if (!status) return "等待 CLI 状态";
  if (!status.installed) return "未检测到 lark-cli";
  if (status.can_assist_oauth) return "CLI 用户身份可用";
  return "CLI 需要重新授权";
}

function getLarkCliBadge(
  status: LarkCliAuthStatus | undefined,
  loading: boolean,
  error: unknown
): string {
  if (loading) return "检测中";
  if (error) return "读取失败";
  if (!status) return "未检测";
  if (!status.installed) return "未安装";
  if (status.can_assist_oauth) return "CLI 可用";
  return "需授权";
}

function getLarkCliTone(
  status: LarkCliAuthStatus | undefined,
  loading: boolean,
  error: unknown
): StatusTone {
  if (loading) return "info";
  if (error) return "danger";
  if (!status) return "neutral";
  if (!status.installed) return "warning";
  return status.can_assist_oauth ? "success" : "warning";
}

function getStateTitle(state: "ready" | "authorize" | "configure"): string {
  if (state === "ready") return "授权完成";
  if (state === "authorize") return "等待飞书授权";
  return "需要配置飞书应用";
}

function getStateHint(state: "ready" | "authorize" | "configure"): string {
  if (state === "ready") return "当前账号已在本机完成授权，可以进入桌面工作台。";
  if (state === "authorize") return "OAuth 配置已保存。请扫码或在本机浏览器打开授权链接完成连接。";
  return "请先填写飞书企业自建应用的 App ID、App Secret，并复制 Redirect URI 到飞书后台。";
}

function getStateBadge(state: "ready" | "authorize" | "configure"): string {
  if (state === "ready") return "可进入总览";
  if (state === "authorize") return "待授权";
  return "待配置";
}

function getStateTone(state: "ready" | "authorize" | "configure"): StatusTone {
  if (state === "ready") return "success";
  if (state === "authorize") return "info";
  return "warning";
}
