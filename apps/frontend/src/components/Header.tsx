/* ------------------------------------------------------------------ */
/*  仪表盘 Header Banner — 仅在仪表盘页面渲染                            */
/* ------------------------------------------------------------------ */

import { useAuth } from "../hooks/useAuth";
import { StatusPill } from "./StatusPill";
import { ThemeToggle } from "./ThemeToggle";
import { IconPlay, IconPause } from "./Icons";
import { cn } from "../lib/utils";

type HeaderProps = {
  globalPaused: boolean;
  onTogglePause: () => void;
};

export function Header({ globalPaused, onTogglePause }: HeaderProps) {
  const { connected, loading } = useAuth();

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-zinc-800 bg-zinc-900/70 p-6">
      <div className="space-y-1.5">
        <p className="text-xs uppercase tracking-widest text-zinc-500">仪表盘</p>
        <p className="text-xl font-semibold text-zinc-50">保持本地与云端一致的同步节奏</p>
        <p className="text-sm text-zinc-400">连接状态、任务调度与日志都集中在这里，随时掌握同步进度。</p>
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
        <ThemeToggle />
      </div>
    </header>
  );
}
