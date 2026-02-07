/* ------------------------------------------------------------------ */
/*  LarkSync App Shell — 布局 + 路由（基于 state）                       */
/* ------------------------------------------------------------------ */

import { useState } from "react";
import { useConflicts } from "./hooks/useConflicts";
import { Sidebar } from "./components/Sidebar";
import { Header } from "./components/Header";
import { DashboardPage } from "./pages/DashboardPage";
import { TasksPage } from "./pages/TasksPage";
import { LogCenterPage } from "./pages/LogCenterPage";
import { SettingsPage } from "./pages/SettingsPage";
import { ConfirmDialogProvider } from "./components/ui/confirm-dialog";
import type { NavKey } from "./types";

export default function App() {
  const [activeTab, setActiveTab] = useState<NavKey>("dashboard");
  const [globalPaused, setGlobalPaused] = useState(false);
  const { conflicts } = useConflicts();
  const unresolvedConflicts = conflicts.filter((c) => !c.resolved).length;

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
          <Header
            activeTab={activeTab}
            globalPaused={globalPaused}
            onTogglePause={() => setGlobalPaused((prev) => !prev)}
          />

          {activeTab === "dashboard" ? (
            <DashboardPage onNavigate={setActiveTab} />
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
