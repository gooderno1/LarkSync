import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { DesktopStatusBar } from "./DesktopStatusBar";
import { DesktopTopBar } from "./DesktopTopBar";
import { Sidebar } from "./Sidebar";

const desktopStatus = vi.hoisted(() => ({
  runtime: {
    backend_running: true,
    frontend_static_available: true,
    data_dir: "D:/LarkSync/data",
    database_url: "sqlite+aiosqlite:///D:/LarkSync/data/larksync.db",
    packaged: false,
  },
  auth: {
    connected: true,
    oauth_configured: true,
    open_id: "ou_123",
    account_name: "Alex",
    device_id: "device-1",
    expires_at: 1_800_000_000,
  },
  tasks: {
    total: 5,
    enabled: 4,
    paused: 1,
    running: 2,
    failed: 0,
    last_error: null,
    last_sync_time: 1_800_000_000,
  },
  conflicts: {
    unresolved: 3,
  },
  update: {
    current_version: "v0.8.0-dev.1",
    latest_version: "v0.8.0",
    update_available: true,
    last_check: 1_800_000_000,
    last_error: null,
    download_path: null,
  },
}));

vi.mock("../hooks/useDesktopStatus", () => ({
  useDesktopStatus: () => ({
    status: desktopStatus,
    isFetching: false,
    refetch: vi.fn(),
  }),
}));

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    connected: true,
    loading: false,
  }),
}));

vi.mock("../lib/api", () => ({
  getLoginUrl: () => "/auth/login",
}));

vi.mock("../hooks/useTasks", () => ({
  useTasks: () => ({
    tasks: [{ id: "task-1", enabled: true }],
    runTask: vi.fn(),
  }),
}));

vi.mock("./ui/toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

vi.mock("./ThemeToggle", () => ({
  ThemeToggle: () => <div>Theme Toggle</div>,
}));

describe("desktop shell status", () => {
  it("renders top and bottom bars from the desktop status aggregate", () => {
    const html = renderToStaticMarkup(
      <>
        <DesktopTopBar activeTab="dashboard" onNavigate={vi.fn()} />
        <DesktopStatusBar />
      </>,
    );

    expect(html).toContain("飞书已连接");
    expect(html).toContain("2 个任务运行中");
    expect(html).toContain("3 个待处理");
    expect(html).toContain("Alex");
    expect(html).toContain("LarkSync.Backend.dev");
    expect(html).toContain("端口");
    expect(html).toContain("8000");
    expect(html).toContain("WebSocket");
    expect(html).toContain("已连接");
    expect(html).toContain("SQLite 3");
    expect(html).toContain("版本 v0.8.0-dev.1");
  });

  it("keeps the desktop shell on the fixed design canvas", () => {
    const html = renderToStaticMarkup(
      <>
        <Sidebar activeTab="dashboard" onNavigate={vi.fn()} unresolvedConflicts={2} />
        <DesktopTopBar activeTab="dashboard" onNavigate={vi.fn()} />
        <DesktopStatusBar />
      </>,
    );

    expect(html).toContain("w-[220px]");
    expect(html).toContain("/logo-horizontal.png");
    expect(html).toContain("活动与问题");
    expect(html).toContain('data-sidebar-badge="conflicts"');
    expect(html).not.toContain('data-sidebar-badge="activity"');
    expect(html).toContain("w-[140px]");
    expect(html).not.toContain("折叠侧边栏");
    expect(html).not.toContain("«");
    expect(html).toContain("pl-9 pr-8");
    expect(html).toContain("w-[430px]");
    expect(html).toContain("w-[128px]");
    expect(html).toContain("w-[116px]");
    expect(html).toContain("任务启停");
    expect(html).toContain('data-desktop-statusbar="true"');
    expect(html).toContain("bg-white");
    expect(html).toContain('data-account-menu-trigger="true"');
    expect(html).toContain('aria-haspopup="menu"');
    expect(html).toContain('aria-label="账户菜单"');
    expect(html).toContain("账号与授权");
    expect(html).toContain("更新与维护");
    expect(html).toContain("bg-[#f9fbfd]");
    expect(html).not.toContain('data-desktop-statusbar="true" class="h-[78px] shrink-0 border-t border-[#dce6f2] bg-[#fdfdfd]');
    expect(html).not.toContain("□");
    expect(html).not.toContain("×");
    expect(html).not.toContain("w-[72px]");
    expect(html).not.toContain("min-[1180px]");
    expect(html).not.toContain("[@media(max-height:760px)]");
    expect(html).not.toContain("/favicon.png");
  });
});
