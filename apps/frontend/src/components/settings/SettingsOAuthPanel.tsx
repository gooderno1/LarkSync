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
  showSaveAction?: boolean;
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
  showSaveAction = true,
}: SettingsOAuthPanelProps) {
  return (
    <div className="rounded-lg border border-[#d7e4f5] bg-white p-4 shadow-[0_10px_28px_rgba(51,112,255,0.05)]">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-[#102033]">高级 OAuth</h2>
          <p className="mt-1 text-xs text-[#58708d]">OAuth 配置：仅在更换应用凭证或授权端点时修改。</p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="/oauth-guide.html"
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 rounded-lg border border-[#3370FF]/25 bg-[#edf4ff] px-3 py-1.5 text-xs font-medium text-[#2456d6] transition hover:border-[#3370FF]/45 hover:bg-[#e3eeff]"
          >
            查看配置教程 ↗
          </a>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.25fr)] gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-[#52677f]">App ID</label>
          <input className={inputCls} placeholder="cli_xxxxxxxxxxxx" value={clientId} onChange={(e) => setClientId(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-[#52677f]">App Secret</label>
          <input className={inputCls} placeholder="保存后自动清空" type="password" value={clientSecret} onChange={(e) => setClientSecret(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block truncate text-xs font-medium text-[#52677f]">
            Redirect URI
            <span className="ml-2 text-[#7e91a8]">（自动生成，请复制填入飞书后台）</span>
          </label>
          <div className="flex gap-2">
            <input className={`${inputCls} bg-[#f8fbff] text-[#34516f]`} value={redirectUri} readOnly />
            <button
              className="inline-flex items-center gap-1.5 rounded-lg border border-[#c9d8eb] bg-[#f8fbff] px-3 py-2 text-xs font-medium text-[#34516f] transition hover:border-[#3370FF]/40 hover:bg-[#eef5ff]"
              onClick={copyRedirectUri}
              type="button"
            >
              <IconCopy className="h-3.5 w-3.5" />
              复制
            </button>
          </div>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {showSaveAction ? (
          <button className="h-8 rounded-lg bg-[#3370FF] px-4 text-xs font-semibold text-white transition hover:bg-[#3370FF]/80 disabled:opacity-50" onClick={handleSave} disabled={saving} type="button">
            {saving ? "保存中..." : "保存配置"}
          </button>
        ) : null}
        <button className="h-8 rounded-lg border border-[#c9d8eb] bg-white px-3 text-xs font-medium text-[#52677f] transition hover:border-[#3370FF]/40 hover:bg-[#f2f7ff] hover:text-[#2456d6]" onClick={toggleAdvanced} type="button">
          {showAdvanced ? "收起高级设置" : "高级设置"}
        </button>
        {saveError ? <span className="text-sm text-[#d14343]">错误：{saveError}</span> : null}
      </div>

      {showAdvanced ? (
        <div className="mt-3 space-y-3 rounded-lg border border-[#d7e4f5] bg-[#f8fbff] p-3">
          <p className="text-xs font-medium text-[#52677f]">高级 OAuth 参数（通常无需修改）</p>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="mb-1 block text-xs text-[#7e91a8]">授权地址</label>
              <input className={inputCls} placeholder="默认可空" value={authorizeUrl} onChange={(e) => setAuthorizeUrl(e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-xs text-[#7e91a8]">Token 地址</label>
              <input className={inputCls} placeholder="默认可空" value={tokenUrl} onChange={(e) => setTokenUrl(e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-xs text-[#7e91a8]">Token 存储方式</label>
              <select className="rounded-lg border border-[#c9d8eb] bg-white px-4 py-2.5 text-sm text-[#1f2d3d] outline-none transition focus:border-[#3370FF] focus:ring-2 focus:ring-[#3370FF]/15" value={tokenStore} onChange={(e) => setTokenStore(e.target.value)}>
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
