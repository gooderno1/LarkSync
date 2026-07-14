import { useEffect, useMemo, useRef, useState } from "react";
import { useDesktopStatus } from "../hooks/useDesktopStatus";
import { useTasks } from "../hooks/useTasks";
import { useToast } from "./ui/toast";
import { IconChevronDown, IconDownloadTray, IconPauseCircle, IconRefresh, IconSettings } from "./Icons";
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
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const accountMenuRef = useRef<HTMLDivElement>(null);

  const enabledTasks = useMemo(() => tasks.filter((task) => task.enabled), [tasks]);
  const accountName = desktopStatus.auth.account_name;
  const pendingCount = desktopStatus.conflicts.unresolved + Math.max(0, desktopStatus.tasks.failed || 0);

  useEffect(() => {
    const closeOnOutsideClick = (event: PointerEvent) => {
      if (!accountMenuRef.current?.contains(event.target as Node)) {
        setAccountMenuOpen(false);
      }
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setAccountMenuOpen(false);
    };
    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);

  const navigateFromAccountMenu = (tab: "settings" | "maintenance") => {
    setAccountMenuOpen(false);
    onNavigate(tab);
  };

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
    <header className="relative z-30 flex h-[88px] flex-none items-center justify-between gap-4 border-b border-[#c6d7e9] bg-white pb-0 pl-9 pr-8 pt-2">
      <div
        className="flex min-w-0 items-center gap-6 text-sm text-[#334762]"
        aria-label={`${desktopStatus.auth.connected ? "飞书已连接" : "飞书未连接"}，${desktopStatus.tasks.running} 个任务运行中，${pendingCount} 个待处理`}
      >
        <TopBarStatus
          label={desktopStatus.runtime.backend_running ? "后端运行中" : "后端异常"}
          tone={desktopStatus.runtime.backend_running ? "success" : "danger"}
        />
        <span className="h-5 w-px bg-[#c6d7e9]" aria-hidden="true" />
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
        <div ref={accountMenuRef} className="relative ml-5 min-w-0 flex-1 border-l border-[#c6d7e9] pl-4">
          <button
            aria-expanded={accountMenuOpen}
            aria-haspopup="menu"
            className="flex h-10 w-full min-w-0 items-center justify-start gap-2 rounded-lg px-1.5 text-[#334762] transition hover:bg-[#eef5ff]"
            data-account-menu-trigger="true"
            onClick={() => setAccountMenuOpen((current) => !current)}
            title="打开账户菜单"
            type="button"
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#dfe9f7] text-xs font-bold text-[#334762]">
              {(accountName || "飞").trim().slice(0, 1).toUpperCase()}
            </span>
            <span className="min-w-0 flex-1 truncate text-left text-sm font-medium">{accountName || "飞书账号"}</span>
            <IconChevronDown className={`h-4 w-4 shrink-0 transition-transform ${accountMenuOpen ? "rotate-180" : ""}`} />
          </button>

          <div
            aria-hidden={!accountMenuOpen}
            aria-label="账户菜单"
            className={`absolute right-0 top-[48px] w-[244px] rounded-lg border border-[#c6d7e9] bg-white p-2 shadow-[0_18px_50px_rgba(16,32,51,0.18)] transition ${accountMenuOpen ? "visible translate-y-0 opacity-100" : "pointer-events-none invisible -translate-y-1 opacity-0"}`}
            data-account-menu="true"
            role="menu"
          >
            <div className="border-b border-[#dce7f3] px-3 pb-2.5 pt-1.5">
              <p className="truncate text-sm font-semibold text-[#102033]">{accountName || "飞书账号"}</p>
              <p className="mt-1 text-xs font-medium text-[#52657a]">已连接 · 当前设备</p>
            </div>
            <button
              className="mt-1 flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm font-medium text-[#334762] hover:bg-[#eef5ff] hover:text-[#3370ff]"
              onClick={() => navigateFromAccountMenu("settings")}
              role="menuitem"
              type="button"
            >
              <IconSettings className="h-4 w-4" />
              <span><span className="block">账号与授权</span><span className="mt-0.5 block text-[11px] font-normal text-[#52657a]">查看飞书连接与 OAuth 配置</span></span>
            </button>
            <button
              className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm font-medium text-[#334762] hover:bg-[#eef5ff] hover:text-[#3370ff]"
              onClick={() => navigateFromAccountMenu("maintenance")}
              role="menuitem"
              type="button"
            >
              <IconDownloadTray className="h-4 w-4" />
              <span><span className="block">更新与维护</span><span className="mt-0.5 block text-[11px] font-normal text-[#52657a]">版本、日志和维护工具</span></span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
