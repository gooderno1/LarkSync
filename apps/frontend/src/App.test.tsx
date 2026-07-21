import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import App, { getNavKeyFromHash } from "./App";

const authState = vi.hoisted((): { connected: boolean; loading: boolean } => ({
  connected: false,
  loading: false,
}));

vi.mock("./hooks/useAuth", () => ({
  useAuth: () => authState,
}));

vi.mock("./hooks/useConfig", () => ({
  useConfig: () => ({
    config: { auth_client_id: "cli_123" },
    configLoading: false,
  }),
}));

vi.mock("./hooks/useConflicts", () => ({
  useConflicts: () => ({
    conflicts: [],
  }),
}));

vi.mock("./components/Sidebar", () => ({
  Sidebar: () => <div>Sidebar</div>,
}));

vi.mock("./components/DesktopTopBar", () => ({
  DesktopTopBar: () => <div>Desktop Top Bar</div>,
}));

vi.mock("./components/OnboardingWizard", () => ({
  OnboardingWizard: () => <div>Onboarding Wizard</div>,
}));

vi.mock("./pages/DashboardPage", () => ({
  DashboardPage: () => <div>Dashboard Page</div>,
}));

vi.mock("./pages/TasksPage", () => ({
  TasksPage: () => <div>Tasks Page</div>,
}));

vi.mock("./pages/ActivityIssuesPage", () => ({
  ActivityIssuesPage: () => <div>Activity Issues Page</div>,
}));

vi.mock("./pages/ConflictResolutionPage", () => ({
  ConflictResolutionPage: () => <div>Conflict Resolution Page</div>,
}));

vi.mock("./pages/SettingsPage", () => ({
  SettingsPage: () => <div>Settings Page</div>,
}));

vi.mock("./pages/MaintenancePage", () => ({
  MaintenancePage: () => <div>Maintenance Page</div>,
}));

vi.mock("./components/ui/confirm-dialog", () => ({
  ConfirmDialogProvider: ({ children }: { children?: ReactNode }) => <>{children}</>,
}));

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App smoke", () => {
  it("parses desktop hash routes and keeps legacy log center hash compatible", () => {
    expect(getNavKeyFromHash("#settings")).toBe("settings");
    expect(getNavKeyFromHash("#activity")).toBe("activity");
    expect(getNavKeyFromHash("#logcenter")).toBe("activity");
    expect(getNavKeyFromHash("#unknown")).toBeNull();
  });

  it("renders onboarding when OAuth is configured but account is not connected", () => {
    authState.connected = false;

    const html = renderToStaticMarkup(<App />);

    expect(html).toContain("Onboarding Wizard");
  });

  it("uses a binary local authorization state without permission-check banners", () => {
    authState.connected = true;

    const html = renderToStaticMarkup(<App />);

    expect(html).not.toContain("飞书云文档权限不足");
    expect(html).not.toContain("重新授权飞书");
    expect(html).toContain("Dashboard Page");
  });

  it("renders the desktop shell around the dashboard", () => {
    authState.connected = true;

    const html = renderToStaticMarkup(<App />);

    expect(html).toContain("Desktop Top Bar");
    expect(html).not.toContain("Desktop Status Bar");
    expect(html).toContain("Dashboard Page");
    expect(html).toContain("Sidebar");
    expect(html).toContain('data-desktop-scale="1.000"');
    expect(html).toContain('--desktop-scale:1');
    expect(html).toContain("px-8 py-6");
    expect(html).toContain("desktop-grid-surface");
    expect(html).toContain('data-desktop-main="true"');
    expect(html).not.toContain('data-desktop-statusbar="true"');
    expect(html).toContain("bg-white");
    expect(html).not.toContain("desktop-perspective-line");
    expect(html).not.toContain("min-[1180px]");
    expect(html).not.toContain("min-[1440px]");
  });

  it("opens the page requested by the desktop window hash", () => {
    authState.connected = true;
    vi.stubGlobal("window", {
      location: { hash: "#settings" },
      history: { replaceState: vi.fn() },
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    });

    const html = renderToStaticMarkup(<App />);

    expect(html).toContain("Settings Page");
    expect(html).not.toContain("Dashboard Page");
  });
});
