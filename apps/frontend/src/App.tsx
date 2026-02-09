/* ------------------------------------------------------------------ */
/*  LarkSync App Shell — 布局 + 路由（基于 state）                       */
/* ------------------------------------------------------------------ */

import { useState } from "react";
import { useAuth } from "./hooks/useAuth";
import { useConfig } from "./hooks/useConfig";
import { useConflicts } from "./hooks/useConflicts";
import { Sidebar } from "./components/Sidebar";
import { Header } from "./components/Header";
import { OnboardingWizard } from "./components/OnboardingWizard";
import { DashboardPage } from "./pages/DashboardPage";
import { TasksPage } from "./pages/TasksPage";
import { LogCenterPage } from "./pages/LogCenterPage";
import { SettingsPage } from "./pages/SettingsPage";
import { ConfirmDialogProvider } from "./components/ui/confirm-dialog";
import type { NavKey } from "./types";

export default function App() {
  const [activeTab, setActiveTab] = useState<NavKey>("dashboard");
  const [globalPaused, setGlobalPaused] = useState(false);

  /* ---------- 连接与配置状态检测 ---------- */
  const { connected, driveOk, loading: authLoading } = useAuth();
  const { config, configLoading } = useConfig();
  const { conflicts } = useConflicts();
  const unresolvedConflicts = conflicts.filter((c) => !c.resolved).length;

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
            <span className="text-sm text-zinc-500">正在加载...</span>
          </div>
        </div>
      </div>
    );
  }

  /* ---------- 未配置 OAuth 或未连接：引导向导 ---------- */
  const oauthConfigured = !!config.auth_client_id;
  if (!oauthConfigured || !connected) {
    return (
      <div className="min-h-screen text-zinc-100">
        <OnboardingWizard
          oauthConfigured={oauthConfigured}
          connected={connected}
        />
        <ConfirmDialogProvider />
      </div>
    );
  }

  /* ---------- 正常渲染主界面 ---------- */
  return (
    <div className="min-h-screen text-zinc-100">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 lg:flex-row">
        {/* Sidebar */}
        <Sidebar
          activeTab={activeTab}
          onNavigate={setActiveTab}
          unresolvedConflicts={unresolvedConflicts}
        />

        {/* Main content */}
        <main className="flex-1 space-y-6">
          {/* Drive 权限不足提示 */}
          {connected && !driveOk && (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-5 py-4 text-sm text-amber-200">
              <p className="font-semibold">飞书云文档权限不足</p>
              <p className="mt-1 text-xs text-amber-300/80">
                当前授权令牌缺少 <code className="rounded bg-zinc-800 px-1">drive:drive</code> 等权限。请在飞书开发者后台确认权限已添加，并前往「版本管理与发布」发布应用，然后点击下方按钮重新授权。
              </p>
              <a
                href="/auth/login?redirect=/"
                className="mt-2.5 inline-block rounded-lg bg-amber-500/20 px-4 py-1.5 text-xs font-medium text-amber-200 transition hover:bg-amber-500/30"
              >
                重新授权飞书
              </a>
            </div>
          )}
          {/* 仅仪表盘渲染完整 Header banner */}
          {activeTab === "dashboard" ? (
            <>
              <Header
                globalPaused={globalPaused}
                onTogglePause={() => setGlobalPaused((prev) => !prev)}
              />
              <DashboardPage onNavigate={setActiveTab} />
            </>
          ) : null}
          {activeTab === "tasks" ? <TasksPage /> : null}
          {activeTab === "logcenter" ? <LogCenterPage /> : null}
          {activeTab === "settings" ? <SettingsPage /> : null}
        </main>
      </div>

      {/* Global dialogs */}
      <ConfirmDialogProvider />
    </div>
  );
}
