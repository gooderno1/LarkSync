/* ------------------------------------------------------------------ */
/*  侧边栏                                                             */
/* ------------------------------------------------------------------ */

import type { NavKey } from "../types";
import {
  IconActivityList,
  IconConflicts,
  IconDownloadTray,
  IconHome,
  IconSettings,
  IconSyncCircle,
} from "./Icons";
import { cn } from "../lib/utils";

type SidebarProps = {
  activeTab: NavKey;
  onNavigate: (tab: NavKey) => void;
  unresolvedConflicts: number;
};

const navItems: Array<{
  id: NavKey;
  label: string;
  icon: typeof IconHome;
  badgeKey?: "conflicts";
}> = [
  { id: "dashboard", label: "总览", icon: IconHome },
  { id: "tasks", label: "同步任务", icon: IconSyncCircle },
  { id: "activity", label: "活动与问题", icon: IconActivityList },
  { id: "conflicts", label: "冲突处理", icon: IconConflicts, badgeKey: "conflicts" },
  { id: "settings", label: "设置", icon: IconSettings },
  { id: "maintenance", label: "更新与维护", icon: IconDownloadTray },
];

export function Sidebar({ activeTab, onNavigate, unresolvedConflicts }: SidebarProps) {
  return (
    <aside className="flex h-full w-[220px] flex-none flex-col border-r border-[#d7e6ff] bg-[#f9fbfd] px-4 pb-7 pt-6">
      {/* Logo */}
      <div className="flex h-14 items-center justify-start px-3">
        <img
          src="/logo-horizontal.png"
          alt="LarkSync"
          className="h-auto w-[140px] object-contain"
          draggable={false}
        />
      </div>

      {/* Nav */}
      <nav className="mt-7 grid gap-3">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          const badge = item.badgeKey === "conflicts" ? unresolvedConflicts : 0;
          return (
            <button
              key={item.id}
              className={cn(
                "group relative flex h-11 items-center justify-between rounded-lg px-3 text-sm transition",
                isActive
                  ? "bg-[#eaf3ff] text-[#3370FF] font-semibold shadow-[inset_3px_0_0_#3370FF]"
                  : "text-[#52657A] hover:bg-[#f2f7ff] hover:text-[#102033]"
              )}
              onClick={() => onNavigate(item.id)}
              title={item.label}
              type="button"
            >
              <span className="flex min-w-0 items-center justify-start gap-5">
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
        })}
      </nav>

      {/* Connection status */}
      <div className="mt-auto flex justify-center pb-3">
        <button
          className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-[#1f3763] transition hover:bg-[#eef5ff] hover:text-[#3370ff]"
          type="button"
          title="折叠侧边栏"
        >
          <span className="text-xl leading-none">«</span>
        </button>
      </div>

    </aside>
  );
}
