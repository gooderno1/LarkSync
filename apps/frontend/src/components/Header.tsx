/* ------------------------------------------------------------------ */
/*  仪表盘 Header Banner — 仅在仪表盘页面渲染                            */
/* ------------------------------------------------------------------ */

import { useAuth } from "../hooks/useAuth";
import { useTasks } from "../hooks/useTasks";
import { StatusPill } from "./StatusPill";
import { ThemeToggle } from "./ThemeToggle";

export function Header() {
  const { connected, loading } = useAuth();
  const { tasks, statusMap } = useTasks();
  const runningTasks = tasks.filter((task) => statusMap[task.id]?.state === "running");
  const enabledTasks = tasks.filter((task) => task.enabled);
  const taskStatusLabel =
    runningTasks.length > 0
      ? `正在同步 ${runningTasks.length} 个任务`
      : enabledTasks.length > 0
        ? "当前无运行任务"
        : "暂无启用任务";

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
        <StatusPill
          label={taskStatusLabel}
          tone={runningTasks.length > 0 ? "info" : enabledTasks.length > 0 ? "neutral" : "warning"}
          dot={runningTasks.length > 0}
        />
        <ThemeToggle />
      </div>
    </header>
  );
}
