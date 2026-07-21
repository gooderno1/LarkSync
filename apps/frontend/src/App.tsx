/* ------------------------------------------------------------------ */
/*  LarkSync App Shell — 布局 + hash 路由                               */
/* ------------------------------------------------------------------ */

import { useEffect, useState } from "react";
import { useAuth } from "./hooks/useAuth";
import { useConfig } from "./hooks/useConfig";
import { useConflicts } from "./hooks/useConflicts";
import { Sidebar } from "./components/Sidebar";
import { DesktopTopBar } from "./components/DesktopTopBar";
import { OnboardingWizard } from "./components/OnboardingWizard";
import { ActivityIssuesPage } from "./pages/ActivityIssuesPage";
import { ConflictResolutionPage } from "./pages/ConflictResolutionPage";
import { DashboardPage } from "./pages/DashboardPage";
import { MaintenancePage } from "./pages/MaintenancePage";
import { SettingsPage } from "./pages/SettingsPage";
import { TaskDetailPage } from "./pages/TaskDetailPage";
import { TasksPage } from "./pages/TasksPage";
import { ConfirmDialogProvider } from "./components/ui/confirm-dialog";
import { useDesktopViewportScale } from "./hooks/useDesktopViewportScale";
import type { NavKey } from "./types";

const navKeys: NavKey[] = ["dashboard", "tasks", "activity", "conflicts", "settings", "maintenance"];
const legacyHashRoutes: Record<string, NavKey> = {
  logcenter: "activity",
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
  const { connected, loading: authLoading } = useAuth();
  const { config, configLoading } = useConfig();
  const { conflicts } = useConflicts();
  const unresolvedConflicts = conflicts.filter((c) => !c.resolved).length;
  const desktopViewport = useDesktopViewportScale();

  /* ---------- 加载中：全屏骨架屏 ---------- */
  if (authLoading || configLoading) {
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
  const oauthConfigured = !!config.auth_client_id;
  if (!oauthConfigured || !connected) {
    return (
      <div className="h-screen overflow-hidden bg-[#f5f9ff] text-[#102033]" style={desktopViewport.viewportStyle}>
        <div
          className="overflow-hidden bg-[#f5f9ff]"
          data-desktop-scale={desktopViewport.scale.toFixed(3)}
          style={desktopViewport.canvasStyle}
        >
          <OnboardingWizard
            oauthConfigured={oauthConfigured}
            connected={connected}
          />
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
              {activeTab === "activity" ? <ActivityIssuesPage /> : null}
              {activeTab === "conflicts" ? <ConflictResolutionPage /> : null}
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
