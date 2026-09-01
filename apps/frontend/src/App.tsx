/* ------------------------------------------------------------------ */
/*  LarkSync App Shell — 布局 + hash 路由                               */
/* ------------------------------------------------------------------ */

import { useEffect, useState } from "react";
import { useAccounts } from "./hooks/useAccounts";
import { useProblemSummary } from "./hooks/useProblems";
import { Sidebar } from "./components/Sidebar";
import { DesktopTopBar } from "./components/DesktopTopBar";
import { AccountConnectPanel } from "./components/AccountConnectPanel";
import { ActivityIssuesPage } from "./pages/ActivityIssuesPage";
import { ConflictResolutionPage } from "./pages/ConflictResolutionPage";
import { DashboardPage } from "./pages/DashboardPage";
import { MaintenancePage } from "./pages/MaintenancePage";
import { SettingsPage } from "./pages/SettingsPage";
import { TaskDetailPage } from "./pages/TaskDetailPage";
import { TasksPage } from "./pages/TasksPage";
import { ConfirmDialogProvider } from "./components/ui/confirm-dialog";
import { useDesktopViewportScale } from "./hooks/useDesktopViewportScale";
import { useWindowLayoutMode } from "./hooks/useWindowLayoutMode";
import type { NavKey } from "./types";

const navKeys: NavKey[] = ["dashboard", "tasks", "activity", "conflicts", "settings", "maintenance"];
const legacyHashRoutes: Record<string, NavKey> = {
  logcenter: "activity",
  problems: "conflicts",
};

export function getNavKeyFromHash(hash?: string): NavKey | null {
  const raw = (hash || "").replace(/^#\/?/, "").split(/[/?&]/)[0].trim();
  if (!raw) return null;
  const route = legacyHashRoutes[raw] || raw;
  return navKeys.includes(route as NavKey) ? (route as NavKey) : null;
}

function getInitialNavKey(): NavKey {
  if (typeof window === "undefined") return "dashboard";
  return getNavKeyFromHash(window.location.hash) || "dashboard";
}

function syncWindowHash(tab: NavKey) {
  if (typeof window === "undefined") return;
  const nextHash = `#${tab}`;
  if (window.location.hash === nextHash) return;
  window.history.replaceState(null, "", nextHash);
}

export default function App() {
  const [activeTab, setActiveTab] = useState<NavKey>(() => getInitialNavKey());
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const handleNavigate = (tab: NavKey) => {
    setActiveTab(tab);
    if (tab !== "tasks") setSelectedTaskId(null);
    syncWindowHash(tab);
  };

  useEffect(() => {
    const handleHashChange = () => {
      const tab = getNavKeyFromHash(window.location.hash);
      if (!tab) return;
      setActiveTab(tab);
      if (tab !== "tasks") setSelectedTaskId(null);
      if (window.location.hash !== `#${tab}`) {
        syncWindowHash(tab);
      }
    };

    handleHashChange();
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  /* ---------- 连接与配置状态检测 ---------- */
  const { activeAccount, activeAccountId, loading: accountLoading } = useAccounts();
  useEffect(() => {
    setSelectedTaskId(null);
  }, [activeAccountId]);
  const connected = activeAccount?.state === "connected";
  const { summary: problemSummary } = useProblemSummary(Boolean(activeAccount));
  const unresolvedConflicts = problemSummary?.unresolved ?? 0;
  const desktopViewport = useDesktopViewportScale();
  const windowLayout = useWindowLayoutMode();

  /* ---------- 加载中：全屏骨架屏 ---------- */
  if (accountLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <img
            src="/logo-horizontal.png"
            alt="LarkSync"
            className="h-9 w-auto object-contain opacity-60"
            draggable={false}
          />
          <div className="flex items-center gap-3">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-[#3370FF] border-t-transparent" />
            <span className="text-sm text-[#6b7f96]">正在加载...</span>
          </div>
        </div>
      </div>
    );
  }

  /* ---------- 未配置 OAuth 或未连接：引导向导 ---------- */
  if (!connected) {
    return (
      <div className="h-screen overflow-hidden bg-[#f5f9ff] text-[#102033]" style={desktopViewport.viewportStyle}>
        <div
          className="overflow-hidden bg-[#f5f9ff]"
          data-desktop-scale={desktopViewport.scale.toFixed(3)}
          data-window-layout={windowLayout.mode}
          data-window-low-height={windowLayout.lowHeight ? "true" : "false"}
          style={desktopViewport.canvasStyle}
        >
          <div className="grid h-full place-items-center overflow-y-auto px-6 py-10">
            <div className="w-full max-w-3xl rounded-3xl border border-[#d6e3f3] bg-white p-7 shadow-[0_24px_70px_rgba(51,112,255,0.12)]">
              <img src="/logo-horizontal.png" alt="LarkSync" className="h-9 w-auto" />
              <h1 className="mt-7 text-3xl font-semibold text-[#102033]">{activeAccount ? "重新连接飞书账号" : "连接你的第一个飞书账号"}</h1>
              <p className="mb-6 mt-3 text-sm leading-6 text-[#52657a]">{activeAccount ? "当前账号授权已失效。重新扫码后原任务、状态与历史数据都会保留。" : "安装完成后直接扫码即可，应用创建与账号登录会在当前窗口连续完成。"}</p>
              <AccountConnectPanel mode={activeAccount ? "reauthorize" : "add"} accountId={activeAccount?.id} />
            </div>
          </div>
        </div>
        <ConfirmDialogProvider />
      </div>
    );
  }

  /* ---------- 正常渲染主界面 ---------- */
  return (
    <div className="h-screen overflow-hidden bg-white text-[#102033]" style={desktopViewport.viewportStyle}>
      <div
        className="overflow-hidden bg-white"
        data-desktop-scale={desktopViewport.scale.toFixed(3)}
        data-window-layout={windowLayout.mode}
        data-window-low-height={windowLayout.lowHeight ? "true" : "false"}
        style={desktopViewport.canvasStyle}
      >
        <div className="flex h-full w-full overflow-hidden">
          <Sidebar
            activeTab={activeTab}
            onNavigate={handleNavigate}
            unresolvedConflicts={unresolvedConflicts}
          />

          <div className="flex min-w-0 flex-1 flex-col">
            <DesktopTopBar activeTab={activeTab} onNavigate={handleNavigate} />

            <main data-desktop-main="true" className="desktop-grid-surface min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-8 py-6">
              {activeTab === "dashboard" ? <DashboardPage onNavigate={handleNavigate} /> : null}
              {activeTab === "tasks" && selectedTaskId ? (
                <TaskDetailPage taskId={selectedTaskId} onBack={() => setSelectedTaskId(null)} />
              ) : null}
              {activeTab === "tasks" && !selectedTaskId ? (
                <TasksPage onOpenTaskDetail={setSelectedTaskId} />
              ) : null}
              {activeTab === "activity" ? <ActivityIssuesPage layoutMode={windowLayout.mode} /> : null}
              {activeTab === "conflicts" ? <ConflictResolutionPage layoutMode={windowLayout.mode} /> : null}
              {activeTab === "settings" ? <SettingsPage /> : null}
              {activeTab === "maintenance" ? <MaintenancePage /> : null}
            </main>

          </div>
        </div>
      </div>

      {/* Global dialogs */}
      <ConfirmDialogProvider />
    </div>
  );
}
