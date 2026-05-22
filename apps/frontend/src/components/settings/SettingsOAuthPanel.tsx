import type { ReactNode } from "react";

import { IconCopy } from "../Icons";

type SettingsOAuthPanelProps = {
  clientId: string;
  setClientId: (value: string) => void;
  clientSecret: string;
  setClientSecret: (value: string) => void;
  redirectUri: string;
  copyRedirectUri: () => void;
  handleSave: () => void;
  saving: boolean;
  saveError: string | null;
  showAdvanced: boolean;
  toggleAdvanced: () => void;
  authorizeUrl: string;
  setAuthorizeUrl: (value: string) => void;
  tokenUrl: string;
  setTokenUrl: (value: string) => void;
  tokenStore: string;
  setTokenStore: (value: string) => void;
  inputCls: string;
  themeSlot?: ReactNode;
};

export function SettingsOAuthPanel({
  clientId,
  setClientId,
  clientSecret,
  setClientSecret,
  redirectUri,
  copyRedirectUri,
  handleSave,
  saving,
  saveError,
  showAdvanced,
  toggleAdvanced,
  authorizeUrl,
  setAuthorizeUrl,
  tokenUrl,
  setTokenUrl,
  tokenStore,
  setTokenStore,
  inputCls,
  themeSlot,
}: SettingsOAuthPanelProps) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-50">OAuth 配置</h2>
          <p className="mt-1 text-xs text-zinc-400">填写飞书开放平台的 App ID 和 App Secret 即可完成授权。</p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="/oauth-guide.html"
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 rounded-lg border border-[#3370FF]/30 bg-[#3370FF]/10 px-3 py-1.5 text-xs font-medium text-[#3370FF] transition hover:bg-[#3370FF]/20"
          >
            查看配置教程 ↗
          </a>
          {themeSlot}
        </div>
      </div>

      <div className="mt-5 space-y-4">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">App ID</label>
          <input className={inputCls} placeholder="cli_xxxxxxxxxxxx" value={clientId} onChange={(e) => setClientId(e.target.value)} />
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">App Secret</label>
          <input className={inputCls} placeholder="保存后自动清空" type="password" value={clientSecret} onChange={(e) => setClientSecret(e.target.value)} />
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">
            Redirect URI
            <span className="ml-2 text-zinc-500">（自动生成，请复制填入飞书后台）</span>
          </label>
          <div className="flex gap-2">
            <input className={`${inputCls} bg-zinc-900 text-zinc-300`} value={redirectUri} readOnly />
            <button
              className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-xs font-medium text-zinc-300 transition hover:bg-zinc-700"
              onClick={copyRedirectUri}
              type="button"
            >
              <IconCopy className="h-3.5 w-3.5" />
              复制
            </button>
          </div>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button className="rounded-lg bg-[#3370FF] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#3370FF]/80 disabled:opacity-50" onClick={handleSave} disabled={saving} type="button">
          {saving ? "保存中..." : "保存配置"}
        </button>
        <button className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200" onClick={toggleAdvanced} type="button">
          {showAdvanced ? "收起高级设置" : "高级设置"}
        </button>
        {saveError ? <span className="text-sm text-rose-400">错误：{saveError}</span> : null}
      </div>

      {showAdvanced ? (
        <div className="mt-5 space-y-4 rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
          <p className="text-xs font-medium text-zinc-400">高级 OAuth 参数（通常无需修改）</p>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs text-zinc-500">授权地址</label>
              <input className={inputCls} placeholder="默认可空" value={authorizeUrl} onChange={(e) => setAuthorizeUrl(e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-xs text-zinc-500">Token 地址</label>
              <input className={inputCls} placeholder="默认可空" value={tokenUrl} onChange={(e) => setTokenUrl(e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-xs text-zinc-500">Token 存储方式</label>
              <select className="rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-200 outline-none" value={tokenStore} onChange={(e) => setTokenStore(e.target.value)}>
                <option value="keyring">系统密钥库</option>
                <option value="file">文件存储</option>
              </select>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
