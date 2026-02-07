/* ------------------------------------------------------------------ */
/*  全局 Header — 仪表盘显示完整信息，其他页面仅标题+描述               */
/* ------------------------------------------------------------------ */

import type { NavKey } from "../types";
import { useAuth } from "../hooks/useAuth";
import { StatusPill } from "./StatusPill";
import { IconPlay, IconPause } from "./Icons";
import { cn } from "../lib/utils";

type HeaderProps = {
  activeTab: NavKey;
  globalPaused: boolean;
  onTogglePause: () => void;
};

const headerCopy: Record<NavKey, { eyebrow: string; title: string; subtitle: string }> = {
  dashboard: {
    eyebrow: "仪表盘",
    title: "保持本地与云端一致的同步节奏",
    subtitle: "连接状态、任务调度与日志都集中在这里，随时掌握同步进度。",
  },
  tasks: {
    eyebrow: "同步任务",
    title: "让每个同步任务都清晰可控",
    subtitle: "集中管理路径、状态、进度与同步策略，支持快速操作。",
  },
  logcenter: {
    eyebrow: "日志中心",
    title: "用时间线追踪每一次同步",
    subtitle: "统一查看同步日志与冲突处理结果，快速定位问题。",
  },
  settings: {
    eyebrow: "设置",
    title: "配置授权与同步节奏",
    subtitle: "填写应用凭证并调整同步策略，确保授权与调度一致。",
  },
};

export function Header({ activeTab, globalPaused, onTogglePause }: HeaderProps) {
  const { connected, loading } = useAuth();
  const h = headerCopy[activeTab];
  const isDashboard = activeTab === "dashboard";

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-zinc-800 bg-zinc-900/70 p-6">
      <div className="space-y-1.5">
        <p className="text-xs uppercase tracking-widest text-zinc-500">{h.eyebrow}</p>
        <p className="text-xl font-semibold text-zinc-50">{h.title}</p>
        <p className="text-sm text-zinc-400">{h.subtitle}</p>
      </div>
      {/* 仅仪表盘显示连接状态和暂停控制 */}
      {isDashboard ? (
        <div className="flex flex-wrap items-center gap-3">
          <StatusPill
            label={connected ? "已连接" : loading ? "检测中" : "未连接"}
            tone={connected ? "success" : loading ? "info" : "danger"}
            dot
          />
          <button
            className={cn(
              "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold transition",
              globalPaused
                ? "bg-amber-500/20 text-amber-300"
                : "bg-emerald-500/20 text-emerald-300"
            )}
            onClick={onTogglePause}
            type="button"
          >
            {globalPaused ? <IconPlay className="h-3.5 w-3.5" /> : <IconPause className="h-3.5 w-3.5" />}
            {globalPaused ? "已暂停" : "运行中"}
          </button>
        </div>
      ) : null}
    </header>
  );
}
