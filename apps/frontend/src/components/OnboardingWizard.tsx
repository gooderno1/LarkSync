/* ------------------------------------------------------------------ */
/*  首次使用引导向导 — OAuth 配置 + 飞书连接                              */
/* ------------------------------------------------------------------ */

import { useMemo, useState } from "react";
import { useConfig } from "../hooks/useConfig";
import { useAuth } from "../hooks/useAuth";
import { getLoginUrl } from "../lib/api";
import { useToast } from "./ui/toast";
import { IconCloud, IconSettings, IconCopy, IconExternalLink } from "./Icons";
import { ThemeToggle } from "./ThemeToggle";
import { cn } from "../lib/utils";

/* 飞书 v1 OAuth 端点（已验证可用） */
const FEISHU_AUTHORIZE_URL =
  "https://open.feishu.cn/open-apis/authen/v1/index";
const FEISHU_TOKEN_URL =
  "https://open.feishu.cn/open-apis/authen/v1/access_token";

type Props = {
  oauthConfigured: boolean;
  connected: boolean;
};

export function OnboardingWizard({ oauthConfigured, connected }: Props) {
  const { config, saveConfig, saving } = useConfig();
  const { loading: authLoading } = useAuth();
  const { toast } = useToast();
  const loginUrl = getLoginUrl();

  /* ---------- OAuth 表单状态 ---------- */
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);

  /* 当前步骤：根据 oauthConfigured 自动推导 */
  const currentStep = oauthConfigured ? 2 : 1;

  /*
   * Redirect URI — 回调地址
   * 生产模式（安装包）：前端由 FastAPI 同源服务，origin 即后端地址，正确。
   * 开发模式：Vite 代理 /auth → 后端，使用 origin 同样可行。
   */
  const redirectUri = useMemo(() => {
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    return `${origin}/auth/callback`;
  }, []);

  const copyRedirectUri = () => {
    navigator.clipboard.writeText(redirectUri).then(
      () => toast("已复制到剪贴板", "success"),
      () => toast("复制失败", "danger")
    );
  };

  /* ---------- 保存 OAuth 配置 ---------- */
  const handleSaveOAuth = async () => {
    if (!clientId.trim()) {
      setSaveError("请填写 App ID。");
      return;
    }
    if (!clientSecret.trim()) {
      setSaveError("请填写 App Secret。");
      return;
    }
    setSaveError(null);
    try {
      // 保存完整的 OAuth 配置：包含飞书标准端点地址
      await saveConfig({
        auth_client_id: clientId.trim(),
        auth_client_secret: clientSecret.trim(),
        auth_redirect_uri: redirectUri,
        auth_authorize_url: FEISHU_AUTHORIZE_URL,
        auth_token_url: FEISHU_TOKEN_URL,
      });
      setClientSecret("");
      toast("OAuth 配置已保存，请继续连接飞书", "success");
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "保存失败");
    }
  };

  const inputCls =
    "w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-200 outline-none focus:border-[#3370FF] placeholder:text-zinc-600";

  return (
    <div className="relative flex min-h-screen items-center justify-center px-4 py-8">
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>
      <div className="w-full max-w-lg space-y-8">
        {/* Logo + 欢迎语 */}
        <div className="text-center">
          <img
            src="/logo-horizontal.png"
            alt="LarkSync"
            className="mx-auto h-10 w-auto object-contain drop-shadow-[0_1px_6px_rgba(51,112,255,0.3)]"
            draggable={false}
          />
          <h1 className="mt-6 text-2xl font-bold text-zinc-50">
            欢迎使用 LarkSync
          </h1>
          <p className="mt-2 text-sm text-zinc-400">
            飞书云文档与本地文件的同步桥梁，让你随时掌控数据。
          </p>
        </div>

        {/* 步骤指示器 */}
        <div className="flex items-center justify-center gap-3">
          <StepDot
            num={1}
            label="配置应用"
            active={currentStep === 1}
            done={currentStep > 1}
          />
          <div
            className={cn(
              "h-px w-10 transition-colors",
              currentStep > 1 ? "bg-emerald-500" : "bg-zinc-700"
            )}
          />
          <StepDot
            num={2}
            label="连接飞书"
            active={currentStep === 2}
            done={connected}
          />
        </div>

        {/* ===================== Step 1: OAuth 配置 ===================== */}
        {currentStep === 1 ? (
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-6 space-y-5 animate-fade-up">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#3370FF]/20 text-[#3370FF]">
                <IconSettings className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-zinc-50">
                  配置 OAuth 应用
                </h2>
                <p className="text-xs text-zinc-400">
                  请前往飞书开放平台创建应用，获取 App ID 和 App Secret。
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {/* App ID */}
              <div>
                <label className="mb-1.5 block text-xs font-medium text-zinc-400">
                  App ID
                </label>
                <input
                  className={inputCls}
                  placeholder="cli_xxxxxxxxxxxx"
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                />
              </div>

              {/* App Secret */}
              <div>
                <label className="mb-1.5 block text-xs font-medium text-zinc-400">
                  App Secret
                </label>
                <input
                  className={inputCls}
                  placeholder="输入后保存即加密存储"
                  type="password"
                  value={clientSecret}
                  onChange={(e) => setClientSecret(e.target.value)}
                />
              </div>

              {/* Redirect URI */}
              <div>
                <label className="mb-1.5 block text-xs font-medium text-zinc-400">
                  Redirect URI
                  <span className="ml-2 text-zinc-500">
                    （自动生成，请复制填入飞书后台）
                  </span>
                </label>
                <div className="flex gap-2">
                  <input
                    className={`${inputCls} bg-zinc-900 text-zinc-300`}
                    value={redirectUri}
                    readOnly
                  />
                  <button
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-xs font-medium text-zinc-300 transition hover:bg-zinc-700"
                    onClick={copyRedirectUri}
                    type="button"
                  >
                    <IconCopy className="h-3.5 w-3.5" />
                    复制
                  </button>
                </div>
              </div>
            </div>

            {saveError ? (
              <p className="text-sm text-rose-400">错误：{saveError}</p>
            ) : null}

            <div className="flex flex-wrap items-center justify-between gap-3">
              <a
                href="/oauth-guide.html"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs font-medium text-[#3370FF] transition hover:text-[#3370FF]/80"
              >
                <IconExternalLink className="h-3.5 w-3.5" />
                查看配置教程
              </a>
              <button
                className="rounded-lg bg-[#3370FF] px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-[#3370FF]/80 disabled:opacity-50"
                onClick={handleSaveOAuth}
                disabled={saving}
                type="button"
              >
                {saving ? "保存中..." : "保存并继续"}
              </button>
            </div>
          </div>
        ) : null}

        {/* ================ Step 2: 连接飞书 ================ */}
        {currentStep === 2 ? (
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-6 space-y-6 animate-fade-up">
            <div className="flex flex-col items-center text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#3370FF]/20 text-[#3370FF]">
                <IconCloud className="h-8 w-8" />
              </div>
              <h2 className="mt-4 text-lg font-semibold text-zinc-50">
                连接飞书账号
              </h2>
              <p className="mt-2 max-w-sm text-sm text-zinc-400">
                OAuth 配置已就绪。点击下方按钮，通过浏览器完成飞书授权，即可开始使用。
              </p>
            </div>

            {authLoading ? (
              <div className="flex items-center justify-center gap-3 py-4">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-[#3370FF] border-t-transparent" />
                <span className="text-sm text-zinc-400">正在检测授权状态...</span>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <a
                  className="inline-flex items-center gap-2 rounded-lg bg-[#3370FF] px-8 py-3 text-sm font-semibold text-white transition hover:bg-[#3370FF]/80"
                  href={loginUrl}
                >
                  <IconCloud className="h-4 w-4" />
                  连接飞书
                </a>
                <button
                  className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-500 transition hover:text-zinc-300"
                  onClick={() => window.location.reload()}
                  type="button"
                >
                  已完成授权？刷新页面
                </button>
              </div>
            )}

            <div className="border-t border-zinc-800 pt-4 text-center">
              <p className="text-xs text-zinc-500">
                需要修改 OAuth 配置？
                <button
                  className="ml-1 font-medium text-[#3370FF] transition hover:text-[#3370FF]/80"
                  onClick={() => window.location.reload()}
                  type="button"
                >
                  返回上一步
                </button>
              </p>
            </div>
          </div>
        ) : null}

        {/* 底部提示 */}
        <p className="text-center text-xs text-zinc-600">
          所有凭证均加密存储于本地，不会上传至任何第三方服务器。
        </p>
      </div>
    </div>
  );
}

/* ---------- 步骤圆点子组件 ---------- */
function StepDot({
  num,
  label,
  active,
  done,
}: {
  num: number;
  label: string;
  active: boolean;
  done: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          "flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition",
          done
            ? "bg-emerald-500/20 text-emerald-400"
            : active
              ? "bg-[#3370FF] text-white"
              : "bg-zinc-800 text-zinc-500"
        )}
      >
        {done ? "✓" : num}
      </span>
      <span
        className={cn(
          "text-xs font-medium transition",
          active ? "text-zinc-200" : done ? "text-emerald-400" : "text-zinc-500"
        )}
      >
        {label}
      </span>
    </div>
  );
}
