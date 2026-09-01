import { useState } from "react";

import type { AccountSummary } from "../../types";
import { OrganizationAvatar, organizationDisplayName } from "../OrganizationAvatar";

type AccountAction = "pause" | "resume" | "disconnect" | "remove";

type SettingsAccountCardProps = {
  account: AccountSummary;
  active: boolean;
  refreshing: boolean;
  refreshingTenant: boolean;
  onSwitch: () => void;
  onRefresh: () => void;
  onRefreshTenant: () => void;
  onEditAlias: () => void;
  onReauthorize: () => void;
  onAction: (action: AccountAction) => void;
};

function formatCredentialExpiry(timestamp?: number | null) {
  if (!timestamp) return "有效期未知";
  return new Date(timestamp * 1000).toLocaleString([], {
    year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

function accountState(account: AccountSummary) {
  if (account.state !== "connected") return { label: "需要重新授权", dot: "bg-[#f43f5e]", text: "text-[#be123c]" };
  if (account.paused) return { label: "同步已暂停", dot: "bg-[#f59e0b]", text: "text-[#b45309]" };
  return { label: "正常同步", dot: "bg-[#10b981]", text: "text-[#047857]" };
}

function organizationState(account: AccountSummary) {
  if (account.tenant_metadata_status === "ready") return { label: "官方组织信息已同步", tone: "text-[#047857]" };
  if (account.tenant_metadata_status === "permission_required") return { label: "需要开通组织信息权限", tone: "text-[#b45309]" };
  if (account.tenant_metadata_status === "unavailable") return { label: "当前应用暂不支持组织信息", tone: "text-[#71869d]" };
  if (account.tenant_metadata_status === "failed") return { label: "组织信息获取失败", tone: "text-[#be123c]" };
  return { label: "尚未获取组织信息", tone: "text-[#71869d]" };
}

export function SettingsAccountCard({
  account, active, refreshing, refreshingTenant, onSwitch, onRefresh, onRefreshTenant,
  onEditAlias, onReauthorize, onAction,
}: SettingsAccountCardProps) {
  const [moreOpen, setMoreOpen] = useState(false);
  const state = accountState(account);
  const orgState = organizationState(account);
  const protocolV2 = account.auth_protocol === "device_v2";

  return (
    <article data-account-card="true" className={`overflow-visible rounded-xl border bg-white ${active ? "border-[#9fc0ee] shadow-[0_8px_22px_rgba(51,112,255,0.07)]" : "border-[#dce6f2]"}`}>
      <div data-account-identity="true" className="grid min-w-0 grid-cols-[48px_minmax(0,1fr)_auto] items-center gap-3 px-4 py-3.5">
        <OrganizationAvatar account={account} className="h-12 w-12 rounded-xl border border-[#d7e4f5] bg-[#eef5ff] object-cover" fallbackClassName="grid h-12 w-12 place-items-center rounded-xl bg-[#eaf3ff] text-sm font-bold text-[#3370ff]" />
        <div className="min-w-0">
          <div className="flex min-w-0 items-center gap-2">
            <h3 className="truncate text-sm font-semibold text-[#102033]">{organizationDisplayName(account)}</h3>
            {active ? <span className="shrink-0 rounded-full bg-[#eaf3ff] px-2 py-0.5 text-[10px] font-semibold text-[#3370ff]">当前账号</span> : null}
          </div>
          <p className="mt-1 flex min-w-0 items-center gap-1.5 text-xs text-[#71869d]">
            {account.avatar_url ? <img src={account.avatar_url} alt="" className="h-4 w-4 shrink-0 rounded-full object-cover" /> : null}
            <span className="truncate">{account.account_name || "飞书成员"} · {account.brand === "lark" ? "Lark" : "飞书"}</span>
          </p>
        </div>
        {!active ? <button type="button" onClick={onSwitch} className="h-8 shrink-0 rounded-lg border border-[#9fc0ee] bg-[#f5f9ff] px-3 text-xs font-semibold text-[#3370ff]">切换到此账号</button> : <span className="text-xs font-medium text-[#71869d]">正在使用</span>}
      </div>

      <div className="border-y border-[#e4edf8] bg-[#f8fbff]">
        <div className="px-4 py-3">
          <div className="flex min-w-0 items-center justify-between gap-3">
            <div className="min-w-0">
              <p className={`text-xs font-semibold ${orgState.tone}`}>{orgState.label}</p>
              <p className="mt-1 text-[10px] text-[#8a9bb0]">组织 Logo 与名称用于账号区分，不影响同步权限。</p>
            </div>
            <div data-account-organization-actions="true" className="flex shrink-0 items-center gap-1">
              <button type="button" disabled={refreshingTenant} onClick={onRefreshTenant} className="rounded-lg border border-[#b9cfee] bg-white px-2.5 py-1.5 text-[11px] font-semibold text-[#3370ff] disabled:opacity-50">{refreshingTenant ? "检查中…" : account.tenant_metadata_status === "permission_required" ? "扫码开通权限" : "组织信息与权限"}</button>
              <button type="button" onClick={onEditAlias} className="rounded-lg px-2 py-1.5 text-[11px] text-[#52657a] hover:bg-[#eef5ff]">显示名</button>
            </div>
          </div>
        </div>
        <dl data-account-facts="true" className="grid grid-cols-3 border-t border-[#e4edf8]">
          <div className="px-4 py-3">
            <dt className="text-[10px] font-medium text-[#8a9bb0]">同步状态</dt>
            <dd className={`mt-1.5 flex items-center gap-2 text-xs font-semibold ${state.text}`}><span className={`h-2 w-2 rounded-full ${state.dot}`} />{state.label}</dd>
          </div>
          <div className="border-l border-[#e4edf8] px-4 py-3">
            <dt className="text-[10px] font-medium text-[#8a9bb0]">授权方式</dt>
            <dd className={`mt-1.5 truncate text-xs font-semibold ${protocolV2 ? "text-[#047857]" : "text-[#b45309]"}`}>{protocolV2 ? "Device Flow V2" : "OAuth V1 兼容"}</dd>
          </div>
          <div className="border-l border-[#e4edf8] px-4 py-3">
            <dt className="text-[10px] font-medium text-[#8a9bb0]">访问凭据有效至</dt>
            <dd className="mt-1.5 truncate text-xs font-medium text-[#34516f]" title={formatCredentialExpiry(account.access_expires_at)}>{formatCredentialExpiry(account.access_expires_at)}</dd>
          </div>
        </dl>
      </div>

      {account.last_auth_error ? <p className="border-b border-[#fecdd3] bg-[#fff1f2] px-4 py-2.5 text-xs leading-5 text-[#be123c]">最近授权错误：{account.last_auth_error}</p> : null}

      <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-4 py-3">
        <div data-account-primary-actions="true" className="grid max-w-[360px] grid-cols-3 gap-2">
          <button type="button" disabled={refreshing} onClick={onRefresh} className="h-8 rounded-lg border border-[#b9cfee] px-3 text-xs font-semibold text-[#3370ff] disabled:opacity-50">{refreshing ? "刷新中…" : "刷新授权"}</button>
          <button type="button" onClick={onReauthorize} className="h-8 rounded-lg bg-[#3370ff] px-3 text-xs font-semibold text-white shadow-[0_5px_14px_rgba(51,112,255,0.16)]">重新授权</button>
          <button type="button" onClick={() => onAction(account.paused ? "resume" : "pause")} className="h-8 rounded-lg border border-[#d1dfef] px-3 text-xs font-medium text-[#52657a]">{account.paused ? "恢复同步" : "暂停同步"}</button>
        </div>
        <div data-account-maintenance-actions="true" className="relative">
          <button type="button" aria-expanded={moreOpen} onClick={() => setMoreOpen((value) => !value)} className="h-8 rounded-lg px-3 text-xs font-medium text-[#52657a] hover:bg-[#eef5ff]">更多操作 ···</button>
          {moreOpen ? <div className="absolute bottom-10 right-0 z-20 w-36 rounded-xl border border-[#d7e4f5] bg-white p-1.5 shadow-xl">
            <button type="button" onClick={() => { setMoreOpen(false); onAction("disconnect"); }} className="block w-full rounded-lg px-3 py-2 text-left text-xs text-[#b45309] hover:bg-[#fff7ed]">断开本机</button>
            <button type="button" onClick={() => { setMoreOpen(false); onAction("remove"); }} className="block w-full rounded-lg px-3 py-2 text-left text-xs text-[#be123c] hover:bg-[#fff1f2]">从本机移除</button>
          </div> : null}
        </div>
      </div>
    </article>
  );
}
