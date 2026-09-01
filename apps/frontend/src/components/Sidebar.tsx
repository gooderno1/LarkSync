/* ------------------------------------------------------------------ */
/*  侧边栏                                                             */
/* ------------------------------------------------------------------ */

import type { NavKey } from "../types";
import {
  IconActivity,
  IconActivityList,
  IconBell,
  IconClock,
  IconCloud,
  IconConflicts,
  IconDownloadTray,
  IconHome,
  IconSettings,
  IconSyncCircle,
} from "./Icons";
import { cn } from "../lib/utils";
import { formatShortTime } from "../lib/formatters";
import { useDesktopStatus } from "../hooks/useDesktopStatus";
import { useState } from "react";
import { useAccounts } from "../hooks/useAccounts";
import { AccountConnectPanel } from "./AccountConnectPanel";
import { NotificationDrawer } from "./NotificationDrawer";
import { OrganizationAvatar, organizationDisplayName } from "./OrganizationAvatar";

type SidebarProps = {
  activeTab: NavKey;
  onNavigate: (tab: NavKey) => void;
  unresolvedConflicts: number;
};

type SidebarItem = {
  id: NavKey;
  label: string;
  icon: typeof IconHome;
  badgeKey?: "conflicts";
};

const workspaceItems: SidebarItem[] = [
  { id: "dashboard", label: "总览", icon: IconHome },
  { id: "tasks", label: "同步任务", icon: IconSyncCircle },
  { id: "activity", label: "活动管理", icon: IconActivityList },
  { id: "conflicts", label: "问题中心", icon: IconConflicts, badgeKey: "conflicts" },
];

const systemItems: SidebarItem[] = [
  { id: "settings", label: "设置", icon: IconSettings },
  { id: "maintenance", label: "更新与维护", icon: IconDownloadTray },
];

const runtimeProfileLabels: Record<string, string> = {
  synthetic_test: "合成测试",
  snapshot_test: "快照测试",
  live_readonly: "真实只读",
  live_bidirectional: "专用双向",
};

export function Sidebar({ activeTab, onNavigate, unresolvedConflicts }: SidebarProps) {
  const { status } = useDesktopStatus();
  const { accounts, activeAccount, switchAccount, switchingAccountId } = useAccounts();
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [accountSwitchError, setAccountSwitchError] = useState<string | null>(null);
  const [addAccountOpen, setAddAccountOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const runtimeProfileLabel = runtimeProfileLabels[status.runtime.profile];
  const handleAccountSwitch = async (accountId: string) => {
    setAccountSwitchError(null);
    try {
      await switchAccount(accountId);
      setAccountMenuOpen(false);
    } catch (error) {
      setAccountSwitchError(error instanceof Error ? error.message : "账号切换失败");
    }
  };

  const renderNavItems = (items: SidebarItem[], compact = false) => items.map((item) => {
    const Icon = item.icon;
    const isActive = activeTab === item.id;
    const badge = item.badgeKey === "conflicts" ? unresolvedConflicts : 0;
    return (
      <button
        key={item.id}
        className={cn(
          "group relative flex items-center justify-between rounded-lg px-3 text-sm transition",
          compact ? "h-9" : "h-10",
          isActive
            ? "bg-[#eaf3ff] font-semibold text-[#3370FF] shadow-[inset_3px_0_0_#3370FF]"
            : "font-medium text-[#3f536b] hover:bg-[#e8f1fb] hover:text-[#102033]"
        )}
        onClick={() => onNavigate(item.id)}
        title={item.label}
        type="button"
      >
        <span className="flex min-w-0 items-center justify-start gap-4">
          <Icon className="h-[18px] w-[18px]" />
          <span>{item.label}</span>
        </span>
        {badge ? (
          <span
            className="rounded-full bg-[#fff1f2] px-2 py-0.5 text-xs font-semibold leading-none text-[#e11d48] ring-1 ring-[#fecdd3]"
            data-sidebar-badge={item.badgeKey}
          >
            {badge}
          </span>
        ) : null}
      </button>
    );
  });

  return (
    <aside data-desktop-sidebar="true" className="flex h-full w-[244px] flex-none flex-col justify-between border-r border-[#bfd0e2] bg-[#f3f7fc] px-3 pb-4 pt-5">
      <div className="min-h-0">
        <div className="flex h-14 items-center justify-start px-3">
          <img
            src="/logo-horizontal.png"
            alt="LarkSync"
            className="h-auto w-[140px] object-contain"
            draggable={false}
          />
        </div>
        {runtimeProfileLabel ? (
          <div
            className="mx-3 mt-1 rounded-md border border-[#f6c453] bg-[#fff8df] px-2.5 py-1.5 text-center text-[11px] font-semibold text-[#8a5a00]"
            data-runtime-profile={status.runtime.profile}
          >
            {runtimeProfileLabel}
          </div>
        ) : null}

        <section className="mt-3" data-sidebar-account-switcher="true" data-sidebar-organization-drawer="true">
          <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-[#8294a8]">当前组织</p>
          <div data-sidebar-current-organization="true" className="flex h-12 items-center rounded-lg bg-[#e8f1fb] shadow-[inset_3px_0_0_#3370ff]">
            <button type="button" aria-expanded={accountMenuOpen} aria-controls="sidebar-account-list" onClick={() => setAccountMenuOpen((value) => !value)} className="flex h-full min-w-0 flex-1 items-center gap-2.5 rounded-lg px-3 text-left hover:bg-[#e1edfa]">
              <OrganizationAvatar account={activeAccount} className="h-8 w-8 flex-none rounded-lg border border-white/70 object-cover" fallbackClassName="grid h-8 w-8 flex-none place-items-center rounded-lg bg-white/75 text-xs font-bold text-[#3370ff]" />
              <span className="min-w-0 flex-1"><span className="block truncate text-xs font-semibold text-[#2456d6]">{organizationDisplayName(activeAccount)}</span><span className="block truncate text-[10px] text-[#60758d]">{activeAccount?.account_name || "飞书成员"} · {activeAccount?.paused ? "已暂停" : "同步中"}</span></span>
              <span className={`text-[10px] text-[#60758d] transition-transform ${accountMenuOpen ? "rotate-180" : ""}`}>⌄</span>
            </button>
            <button type="button" aria-label="打开通知" onClick={() => setNotificationsOpen(true)} className="relative mr-2 grid h-8 w-8 flex-none place-items-center rounded-lg text-[#52657a] hover:bg-white/70 hover:text-[#3370ff]"><IconBell className="h-[17px] w-[17px]" />{activeAccount?.unread_total ? <span className="absolute -right-1 -top-1 min-w-4 rounded-full bg-[#e11d48] px-1 text-center text-[9px] font-bold leading-4 text-white">{activeAccount.unread_total > 99 ? "99+" : activeAccount.unread_total}</span> : null}</button>
          </div>
          {accountMenuOpen ? <div id="sidebar-account-list" data-sidebar-account-list="true" className="mt-1 rounded-lg bg-[#e8f0fa] p-1.5">
            <div className="flex items-center justify-between px-2 py-1"><p className="text-[10px] font-semibold text-[#71869d]">切换组织</p><span className="text-[10px] text-[#8a9bb0]">{accounts.length} 个</span></div>
            <div className="max-h-[220px] space-y-0.5 overflow-y-auto">
              {accounts.map((account) => <button key={account.id} type="button" disabled={Boolean(switchingAccountId)} onClick={() => void handleAccountSwitch(account.id)} className={`flex h-11 w-full items-center gap-2 rounded-lg px-2 text-left disabled:opacity-60 ${account.id === activeAccount?.id ? "bg-white/85 shadow-[inset_3px_0_0_#3370ff]" : "hover:bg-white/60"}`}><OrganizationAvatar account={account} className="h-7 w-7 shrink-0 rounded-md border border-white object-cover" fallbackClassName="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-white text-[10px] font-bold text-[#3370ff]" /><span className="min-w-0 flex-1"><span className={`block truncate text-xs font-semibold ${account.id === activeAccount?.id ? "text-[#3370ff]" : "text-[#243b55]"}`}>{organizationDisplayName(account)}</span><span className="block truncate text-[10px] text-[#71869d]">{account.account_name || "飞书成员"}{switchingAccountId === account.id ? " · 切换中…" : account.unread_errors ? ` · ${account.unread_errors} 个错误` : ""}</span></span>{account.unread_total ? <span className={`min-w-5 rounded-full px-1.5 text-center text-[10px] font-semibold ${account.unread_errors ? "bg-[#fff1f2] text-[#be123c]" : "bg-white text-[#3370ff]"}`}>{account.unread_total > 99 ? "99+" : account.unread_total}</span> : null}</button>)}
            </div>
            {accountSwitchError ? <p className="mt-1 rounded-md bg-[#fff1f2] px-2 py-1.5 text-[10px] text-[#be123c]">{accountSwitchError}</p> : null}
            <button type="button" onClick={() => { setAddAccountOpen(true); setAccountMenuOpen(false); }} className="mt-1 flex h-9 w-full items-center rounded-lg px-3 text-left text-xs font-semibold text-[#3370ff] hover:bg-white/65">＋ 添加组织或账号</button>
          </div> : null}
        </section>

        <section data-sidebar-section="workspace" className="mt-4">
          <p className="px-3 text-[11px] font-semibold leading-4 uppercase tracking-[0.14em] text-[#71869d]">工作区</p>
          <nav className="mt-2 grid gap-2">{renderNavItems(workspaceItems)}</nav>
        </section>
      </div>

      <div className="space-y-3">
        <section data-sidebar-section="system">
          <p className="px-3 text-[11px] font-semibold leading-4 uppercase tracking-[0.14em] text-[#71869d]">系统</p>
          <nav className="mt-1 grid gap-1">{renderNavItems(systemItems, true)}</nav>
        </section>

        <section data-sidebar-runtime="true" className="rounded-xl border border-[#c9d8e8] bg-white/80 p-3.5 shadow-[0_8px_24px_rgba(51,112,255,0.05)]">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-[#102033]">运行概况</p>
            <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-semibold", status.runtime.backend_running && status.auth.connected ? "bg-[#ecfdf5] text-[#047857]" : "bg-[#fff1f2] text-[#be123c]")}>{status.runtime.backend_running && status.auth.connected ? "正常" : "需处理"}</span>
          </div>
          <div className="mt-3 space-y-2.5 text-xs leading-[18px] text-[#52657a]">
            <div className="flex items-center justify-between gap-2"><span className="inline-flex items-center gap-2"><IconActivity className="h-3.5 w-3.5 text-[#3370ff]" />后端服务</span><span className={status.runtime.backend_running ? "text-[#047857]" : "text-[#be123c]"}>{status.runtime.backend_running ? "运行中" : "异常"}</span></div>
            <div className="flex items-center justify-between gap-2"><span className="inline-flex items-center gap-2"><IconCloud className="h-3.5 w-3.5 text-[#3370ff]" />飞书连接</span><span className={status.auth.connected ? "text-[#047857]" : "text-[#b45309]"}>{status.auth.connected ? "已连接" : "未连接"}</span></div>
            <div className="flex items-center justify-between gap-2 border-t border-[#dce7f3] pt-2"><span className="inline-flex items-center gap-2"><IconClock className="h-3.5 w-3.5 text-[#7f94ab]" />最近同步</span><span className="font-mono text-[#334762]">{status.tasks.last_sync_time ? formatShortTime(status.tasks.last_sync_time) : "暂无"}</span></div>
          </div>
        </section>

        <div className="flex items-center justify-between px-1 text-[11px] leading-4 font-medium text-[#71869d]">
          <span>{status.update.current_version}</span>
          <span>本地运行</span>
        </div>
      </div>
      {addAccountOpen ? <div className="fixed inset-0 z-[70] grid place-items-center overflow-y-auto bg-[#102033]/25 p-6 backdrop-blur-[2px]" onMouseDown={() => setAddAccountOpen(false)}><div className="w-full max-w-3xl rounded-3xl border border-[#d6e3f3] bg-[#f8fbff] p-6 shadow-2xl" onMouseDown={(event) => event.stopPropagation()}><div className="mb-5 flex items-center justify-between"><div><h2 className="text-xl font-semibold text-[#102033]">添加飞书账号</h2><p className="mt-1 text-xs text-[#71869d]">新账号的凭据、任务和状态会独立保存</p></div><button type="button" onClick={() => setAddAccountOpen(false)} className="rounded-lg border border-[#cbd9ea] px-3 py-1.5 text-sm text-[#52657a]">关闭</button></div><AccountConnectPanel onConnected={() => setAddAccountOpen(false)} /></div></div> : null}
      {notificationsOpen ? <NotificationDrawer open onClose={() => setNotificationsOpen(false)} /> : null}
    </aside>
  );
}
