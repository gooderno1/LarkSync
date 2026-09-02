import { useState } from "react";

import type { AccountSummary } from "../../types";
import { OrganizationAvatar, organizationDisplayName } from "../OrganizationAvatar";

type AccountAction = "pause" | "resume" | "disconnect" | "remove";

type SettingsAccountCardProps = {
  account: AccountSummary;
  active: boolean;
  expanded: boolean;
  refreshing: boolean;
  onToggle: () => void;
  onSwitch: () => void;
  onRefresh: () => void;
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

function formatCreatedAt(timestamp?: number | null) {
  if (!timestamp) return "创建时间未知";
  return new Date(timestamp * 1000).toLocaleDateString();
}

function accountState(account: AccountSummary) {
  if (account.state !== "connected") return { label: "需要重新授权", dot: "bg-[#f43f5e]", text: "text-[#be123c]" };
  if (account.paused) return { label: "同步已暂停", dot: "bg-[#f59e0b]", text: "text-[#b45309]" };
  return { label: "正常同步", dot: "bg-[#10b981]", text: "text-[#047857]" };
}

function appSourceLabel(source?: string | null) {
  if (source === "official_registration") return "自动创建";
  if (source === "legacy") return "升级迁移";
  return "手动配置";
}

export function SettingsAccountCard({
  account, active, expanded, refreshing, onToggle, onSwitch, onRefresh,
  onEditAlias, onReauthorize, onAction,
}: SettingsAccountCardProps) {
  const [moreOpen, setMoreOpen] = useState(false);
  const state = accountState(account);
  const organizationName = organizationDisplayName(account);
  const appName = account.app_display_name || "未命名应用";
  const appSuffix = account.app_id ? `…${account.app_id.slice(-4).toUpperCase()}` : "App ID 未知";

  return (
    <article
      data-account-card="true"
      data-account-expanded={expanded ? "true" : "false"}
      className={`overflow-visible rounded-xl border bg-white transition ${active ? "border-[#9fc0ee] shadow-[0_8px_22px_rgba(51,112,255,0.07)]" : "border-[#dce6f2]"}`}
    >
      <div data-account-identity="true" className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-2 px-3 py-3">
        <button
          type="button"
          aria-expanded={expanded}
          aria-label={`查看${organizationName}账号详情`}
          onClick={onToggle}
          className="grid min-w-0 grid-cols-[44px_minmax(0,1fr)] items-center gap-3 rounded-lg text-left outline-none focus-visible:ring-2 focus-visible:ring-[#3370ff]/30"
        >
          <OrganizationAvatar
            account={account}
            className="h-11 w-11 rounded-xl border border-[#d7e4f5] bg-[#eef5ff] object-cover"
            fallbackClassName="grid h-11 w-11 place-items-center rounded-xl bg-[#eaf3ff] text-sm font-bold text-[#3370ff]"
          />
          <span className="min-w-0">
            <span className="flex min-w-0 items-center gap-2">
              <span className="truncate text-sm font-semibold text-[#102033]">{organizationName}</span>
              {active ? <span className="shrink-0 rounded-full bg-[#eaf3ff] px-2 py-0.5 text-[10px] font-semibold text-[#3370ff]">当前账号</span> : null}
              {account.unread_total > 0 ? <span className={`grid h-5 min-w-5 shrink-0 place-items-center rounded-full px-1 text-[10px] font-semibold ${account.unread_errors > 0 ? "bg-[#fff1f2] text-[#e11d48]" : "bg-[#eef5ff] text-[#3370ff]"}`}>{account.unread_total}</span> : null}
            </span>
            <span className="mt-1 flex min-w-0 items-center gap-2 text-xs text-[#71869d]">
              <span className="truncate">{account.account_name || "飞书成员"}</span>
              <span className={`inline-flex shrink-0 items-center gap-1 font-medium ${state.text}`}><span className={`h-1.5 w-1.5 rounded-full ${state.dot}`} />{state.label}</span>
            </span>
            <span className="mt-1 block truncate text-[11px] text-[#8a9bb0]">{appName} · {appSuffix}</span>
          </span>
        </button>
        {!active ? (
          <button type="button" onClick={onSwitch} className="h-8 shrink-0 rounded-lg border border-[#9fc0ee] bg-[#f5f9ff] px-3 text-xs font-semibold text-[#3370ff] hover:bg-[#eaf3ff]">切换</button>
        ) : null}
        <button
          type="button"
          aria-expanded={expanded}
          aria-label={`${expanded ? "收起" : "展开"}${organizationName}详情`}
          onClick={onToggle}
          className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-[#71869d] hover:bg-[#eef5ff] hover:text-[#3370ff]"
        >
          <svg viewBox="0 0 20 20" aria-hidden="true" className={`h-4 w-4 transition-transform ${expanded ? "rotate-180" : ""}`}><path d="m5 7.5 5 5 5-5" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" /></svg>
        </button>
      </div>

      {expanded ? (
        <div className="border-t border-[#e4edf8]">
          <div className="grid gap-4 bg-[#f8fbff] px-4 py-4 min-[1180px]:grid-cols-2">
            <section>
              <div className="flex items-center justify-between gap-3">
                <h4 className="text-xs font-semibold text-[#294662]">身份与应用</h4>
                <button type="button" aria-label="修改组织名称" onClick={onEditAlias} className="text-xs font-semibold text-[#3370ff] hover:underline">修改组织名称</button>
              </div>
              <dl className="mt-3 grid grid-cols-[82px_minmax(0,1fr)] gap-x-3 gap-y-2 text-xs">
                <dt className="text-[#8a9bb0]">成员</dt><dd className="truncate text-[#34516f]">{account.account_name || "飞书成员"}</dd>
                <dt className="text-[#8a9bb0]">应用名称</dt><dd className="truncate font-medium text-[#34516f]">{appName}</dd>
                <dt className="text-[#8a9bb0]">App ID</dt><dd className="font-mono text-[#34516f]">{appSuffix}</dd>
                <dt className="text-[#8a9bb0]">应用来源</dt><dd className="text-[#34516f]">{appSourceLabel(account.app_source)} · {formatCreatedAt(account.app_created_at)}</dd>
              </dl>
            </section>
            <section>
              <h4 className="text-xs font-semibold text-[#294662]">授权与同步</h4>
              <dl data-account-facts="true" className="mt-3 grid grid-cols-[96px_minmax(0,1fr)] gap-x-3 gap-y-2 text-xs">
                <dt className="text-[#8a9bb0]">授权方式</dt><dd className={account.auth_protocol === "device_v2" ? "font-medium text-[#047857]" : "font-medium text-[#b45309]"}>{account.auth_protocol === "device_v2" ? "Device Flow V2" : "OAuth V1 兼容"}</dd>
                <dt className="text-[#8a9bb0]">访问凭据有效至</dt><dd className="truncate text-[#34516f]" title={formatCredentialExpiry(account.access_expires_at)}>{formatCredentialExpiry(account.access_expires_at)}</dd>
                <dt className="text-[#8a9bb0]">后台同步</dt><dd className={`font-medium ${state.text}`}>{state.label}</dd>
              </dl>
            </section>
          </div>

          {account.last_auth_error ? <p className="border-t border-[#fecdd3] bg-[#fff1f2] px-4 py-2.5 text-xs leading-5 text-[#be123c]">最近授权错误：{account.last_auth_error}</p> : null}

          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-t border-[#e4edf8] px-4 py-3">
            <div data-account-primary-actions="true" className="flex flex-wrap gap-2">
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
        </div>
      ) : null}
    </article>
  );
}
