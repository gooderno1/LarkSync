/* ------------------------------------------------------------------ */
/*  LarkSync App Shell — 布局 + hash 路由                               */
/* ------------------------------------------------------------------ */

import { useEffect, useState } from "react";
import { useAuth } from "./hooks/useAuth";
import { useConfig } from "./hooks/useConfig";
import { useConflicts } from "./hooks/useConflicts";
import { Sidebar } from "./components/Sidebar";
import { DesktopStatusBar } from "./components/DesktopStatusBar";
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
  const { connected, driveOk, loading: authLoading } = useAuth();
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
    <div className="h-screen overflow-hidden bg-[#fdfdfd] text-[#102033]" style={desktopViewport.viewportStyle}>
      <div
        className="overflow-hidden bg-[#fdfdfd]"
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

            <main className="desktop-grid-surface min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-7 py-[23px]">
              {connected && !driveOk && (
                <div className="mb-5 rounded-xl border border-[#f59e0b]/30 bg-[#fffbeb] px-5 py-4 text-sm text-[#92400e]">
                  <p className="font-semibold">飞书云文档权限不足</p>
                  <p className="mt-1 text-xs leading-relaxed">
                    当前授权令牌缺少{" "}
                    <code className="rounded border border-[#fcd34d] bg-white px-1 py-0.5 text-[#102033]">drive:drive</code>
                    、{" "}
                    <code className="rounded border border-[#fcd34d] bg-white px-1 py-0.5 text-[#102033]">docx:document</code>
                    、{" "}
                    <code className="rounded border border-[#fcd34d] bg-white px-1 py-0.5 text-[#102033]">docx:document.block:convert</code>{" "}
                    等新版文档权限。请在飞书开发者后台确认权限已添加，并前往「版本管理与发布」发布应用，然后重新授权。
                  </p>
                  <a
                    href="/auth/login?redirect=/"
                    className="mt-2.5 inline-block rounded-lg border border-[#f59e0b]/40 bg-white px-4 py-1.5 text-xs font-semibold text-[#92400e] transition hover:bg-[#fef3c7]"
                  >
                    重新授权飞书
                  </a>
                </div>
              )}

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

            <DesktopStatusBar />
          </div>
        </div>
      </div>

      {/* Global dialogs */}
      <ConfirmDialogProvider />
    </div>
  );
}
