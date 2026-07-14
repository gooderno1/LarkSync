import { useMemo } from "react";
import { useDesktopStatus } from "../hooks/useDesktopStatus";
import { useTasks } from "../hooks/useTasks";
import { useToast } from "./ui/toast";
import { IconPauseCircle, IconRefresh } from "./Icons";
import type { NavKey } from "../types";

type DesktopTopBarProps = {
  activeTab: NavKey;
  onNavigate: (tab: NavKey) => void;
};

type TopBarStatusTone = "success" | "info" | "danger";

const topBarStatusDot: Record<TopBarStatusTone, string> = {
  success: "bg-[#10b981] shadow-[0_0_0_4px_rgba(16,185,129,0.08)]",
  info: "bg-[#3370ff] shadow-[0_0_0_4px_rgba(51,112,255,0.08)]",
  danger: "bg-[#f43f5e] shadow-[0_0_0_4px_rgba(244,63,94,0.08)]",
};

function TopBarStatus({ label, tone }: { label: string; tone: TopBarStatusTone }) {
  return (
    <span className="inline-flex h-8 items-center gap-2 whitespace-nowrap text-sm font-medium text-[#1f3763]">
      <span className={`h-2.5 w-2.5 rounded-full ${topBarStatusDot[tone]}`} aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}

export function DesktopTopBar({ onNavigate }: DesktopTopBarProps) {
  const { status: desktopStatus, refetch: refetchDesktopStatus } = useDesktopStatus();
  const { tasks, runTask } = useTasks();
  const { toast } = useToast();

  const enabledTasks = useMemo(() => tasks.filter((task) => task.enabled), [tasks]);
  const accountName = desktopStatus.auth.account_name;
  const pendingCount = desktopStatus.conflicts.unresolved + Math.max(0, desktopStatus.tasks.failed || 0);

  const handleRunAll = () => {
    if (enabledTasks.length === 0) {
      toast("暂无启用任务", "warning");
      return;
    }
    enabledTasks.forEach((task) => runTask(task));
    toast(`已触发 ${enabledTasks.length} 个任务同步`, "info");
    void refetchDesktopStatus();
  };

  return (
    <header className="flex h-[88px] flex-none items-center justify-between gap-4 overflow-hidden border-b border-[#d7e6ff] bg-[#fdfdfd] pb-0 pl-9 pr-8 pt-2">
      <div
        className="flex min-w-0 items-center gap-6 text-sm text-[#334762]"
        aria-label={`${desktopStatus.auth.connected ? "飞书已连接" : "飞书未连接"}，${desktopStatus.tasks.running} 个任务运行中，${pendingCount} 个待处理`}
      >
        <TopBarStatus
          label={desktopStatus.runtime.backend_running ? "后端运行中" : "后端异常"}
          tone={desktopStatus.runtime.backend_running ? "success" : "danger"}
        />
        <span className="h-5 w-px bg-[#d7e6ff]" aria-hidden="true" />
        <TopBarStatus
          label="WebSocket 已连接"
          tone="info"
        />
      </div>

      <div className="flex w-[430px] min-w-0 shrink-0 items-center">
        <button
          className="inline-flex h-10 w-[128px] items-center justify-center gap-2 rounded-lg bg-[#3370FF] px-5 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(51,112,255,0.22)] transition hover:bg-[#2563eb]"
          onClick={handleRunAll}
          type="button"
          title="立即同步"
        >
          <IconRefresh className="h-4 w-4" />
          <span>立即同步</span>
        </button>
        <button
          className="ml-5 inline-flex h-10 w-[116px] items-center justify-center gap-2 whitespace-nowrap rounded-lg border border-[#bfd8ff] bg-white px-3 text-sm font-medium text-[#3370FF] transition hover:bg-[#eef5ff]"
          onClick={() => onNavigate("tasks")}
          type="button"
          title="前往同步任务页管理任务启停"
        >
          <IconPauseCircle className="h-4 w-4" />
          <span>任务启停</span>
        </button>
        <div className="ml-7 flex min-w-0 flex-1 items-center justify-start gap-2 border-l border-[#d7e6ff] pl-9">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#e6eefb] text-xs font-semibold text-[#52657A]">
            {(accountName || "Z").trim().slice(0, 1).toUpperCase()}
          </span>
          <span className="max-w-[50px] truncate text-sm text-[#52657A]">{accountName || "张三"}</span>
          <span className="text-sm leading-none text-[#52657A]">⌄</span>
        </div>
      </div>
    </header>
  );
}
