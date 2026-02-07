/* ------------------------------------------------------------------ */
/*  全局 Header                                                        */
/*  仪表盘：完整 banner（标题+描述+状态+暂停+主题）                       */
/*  其他页：轻量工具栏（页名+主题切换）                                   */
/* ------------------------------------------------------------------ */

import type { NavKey } from "../types";
import { useAuth } from "../hooks/useAuth";
import { useTheme } from "../hooks/useTheme";
import { StatusPill } from "./StatusPill";
import { IconPlay, IconPause, IconSun, IconMoon } from "./Icons";
import { cn } from "../lib/utils";

type HeaderProps = {
  activeTab: NavKey;
  globalPaused: boolean;
  onTogglePause: () => void;
};

const pageTitles: Record<NavKey, string> = {
  dashboard: "仪表盘",
  tasks: "同步任务",
  logcenter: "日志中心",
  settings: "设置",
};

const dashboardCopy = {
  title: "保持本地与云端一致的同步节奏",
  subtitle: "连接状态、任务调度与日志都集中在这里，随时掌握同步进度。",
};

export function Header({ activeTab, globalPaused, onTogglePause }: HeaderProps) {
  const { connected, loading } = useAuth();
  const { theme, toggle } = useTheme();
  const isDashboard = activeTab === "dashboard";

  const ThemeBtn = (
    <button
      className="inline-flex items-center justify-center rounded-lg border border-zinc-700 p-2 text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-200"
      onClick={toggle}
      type="button"
      title={theme === "dark" ? "切换明亮模式" : "切换深色模式"}
    >
      {theme === "dark" ? <IconSun className="h-4 w-4" /> : <IconMoon className="h-4 w-4" />}
    </button>
  );

  /* 仪表盘：完整 Banner */
  if (isDashboard) {
    return (
      <header className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-zinc-800 bg-zinc-900/70 p-6">
        <div className="space-y-1.5">
          <p className="text-xs uppercase tracking-widest text-zinc-500">仪表盘</p>
          <p className="text-xl font-semibold text-zinc-50">{dashboardCopy.title}</p>
          <p className="text-sm text-zinc-400">{dashboardCopy.subtitle}</p>
        </div>
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
          {ThemeBtn}
        </div>
      </header>
    );
  }

  /* 其他页：轻量工具栏 */
  return (
    <header className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900/70 px-5 py-3">
      <h1 className="text-base font-semibold text-zinc-50">{pageTitles[activeTab]}</h1>
      {ThemeBtn}
    </header>
  );
}
