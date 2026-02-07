/* ------------------------------------------------------------------ */
/*  侧边栏                                                             */
/* ------------------------------------------------------------------ */

import type { NavKey } from "../types";
import { useAuth } from "../hooks/useAuth";
import { useConfig } from "../hooks/useConfig";
import { getLoginUrl } from "../lib/api";
import { formatTimestamp, formatIntervalLabel } from "../lib/formatters";
import { modeLabels } from "../lib/constants";
import { StatusPill } from "./StatusPill";
import { IconArrowRightLeft, IconDashboard, IconTasks, IconConflicts, IconSettings } from "./Icons";
import { cn } from "../lib/utils";

type SidebarProps = {
  activeTab: NavKey;
  onNavigate: (tab: NavKey) => void;
  unresolvedConflicts: number;
};

const navItems: Array<{
  id: NavKey;
  label: string;
  icon: typeof IconDashboard;
  badgeKey?: "conflicts";
}> = [
  { id: "dashboard", label: "仪表盘", icon: IconDashboard },
  { id: "tasks", label: "同步任务", icon: IconTasks },
  { id: "logcenter", label: "日志中心", icon: IconConflicts, badgeKey: "conflicts" },
  { id: "settings", label: "设置", icon: IconSettings },
];

export function Sidebar({ activeTab, onNavigate, unresolvedConflicts }: SidebarProps) {
  const { connected, expiresAt, loading, logout } = useAuth();
  const { config } = useConfig();
  const loginUrl = getLoginUrl();

  const uploadVal = config.upload_interval_value != null ? String(config.upload_interval_value) : "2";
  const uploadUnit = config.upload_interval_unit || "seconds";
  const uploadTime = config.upload_daily_time || "01:00";
  const downloadVal = config.download_interval_value != null ? String(config.download_interval_value) : "1";
  const downloadUnit = config.download_interval_unit || "days";
  const downloadTime = config.download_daily_time || "01:00";
  const syncMode = config.sync_mode || "bidirectional";

  return (
    <aside className="flex w-full flex-col gap-5 rounded-2xl border border-zinc-800 bg-zinc-900/70 p-5 lg:sticky lg:top-6 lg:h-[calc(100vh-3rem)] lg:w-72">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#3370FF]/20 text-[#3370FF]">
          <IconArrowRightLeft className="h-5 w-5" />
        </div>
        <div>
          <p className="text-lg font-semibold text-zinc-50">LarkSync</p>
          <p className="text-xs text-zinc-500">Sync Studio Console</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="grid gap-1.5">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          const badge = item.badgeKey === "conflicts" ? unresolvedConflicts : 0;
          return (
            <button
              key={item.id}
              className={cn(
                "flex items-center justify-between rounded-xl px-3 py-2 text-sm transition",
                isActive
                  ? "bg-[#3370FF]/10 text-[#3370FF] font-medium"
                  : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-100"
              )}
              onClick={() => onNavigate(item.id)}
              type="button"
            >
              <span className="flex items-center gap-3">
                <Icon className="h-4 w-4" />
                {item.label}
              </span>
              {badge ? (
                <span className="rounded-full bg-rose-500/20 px-2 py-0.5 text-xs font-semibold text-rose-300">
                  {badge}
                </span>
              ) : null}
            </button>
          );
        })}
      </nav>

      {/* Connection status */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
        <p className="text-xs uppercase tracking-widest text-zinc-500">连接状态</p>
        <div className="mt-3 flex items-center justify-between">
          <StatusPill
            label={loading ? "检测中" : connected ? "已连接" : "未连接"}
            tone={loading ? "info" : connected ? "success" : "danger"}
            dot
          />
          <span className="text-xs text-zinc-500">
            {expiresAt ? formatTimestamp(expiresAt) : "—"}
          </span>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <a
            className="inline-flex items-center justify-center rounded-lg bg-[#3370FF] px-4 py-2 text-xs font-semibold text-white transition hover:bg-[#3370FF]/80"
            href={loginUrl}
          >
            {connected ? "重新授权" : "连接飞书"}
          </a>
          <button
            className="inline-flex items-center justify-center rounded-lg border border-zinc-700 px-4 py-2 text-xs font-semibold text-zinc-300 transition hover:bg-zinc-800"
            onClick={() => logout()}
            type="button"
          >
            断开连接
          </button>
        </div>
      </div>

      {/* Strategy summary */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 text-xs text-zinc-500">
        <p className="font-semibold text-zinc-300">当前策略</p>
        <ul className="mt-3 space-y-1.5">
          <li>本地 → 云端：每 {formatIntervalLabel(uploadVal, uploadUnit, uploadTime)}</li>
          <li>云端 → 本地：每 {formatIntervalLabel(downloadVal, downloadUnit, downloadTime)}</li>
          <li>默认同步：{modeLabels[syncMode] || syncMode}</li>
        </ul>
      </div>
    </aside>
  );
}
