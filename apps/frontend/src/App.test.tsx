import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import App from "./App";

const authState = vi.hoisted(() => ({
  connected: false,
  driveOk: false,
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

vi.mock("./components/Header", () => ({
  Header: () => <div>Header</div>,
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

vi.mock("./pages/LogCenterPage", () => ({
  LogCenterPage: () => <div>Log Center Page</div>,
}));

vi.mock("./pages/SettingsPage", () => ({
  SettingsPage: () => <div>Settings Page</div>,
}));

vi.mock("./components/ui/confirm-dialog", () => ({
  ConfirmDialogProvider: ({ children }: { children?: ReactNode }) => <>{children}</>,
}));

describe("App smoke", () => {
  it("renders onboarding when OAuth is configured but account is not connected", () => {
    authState.connected = false;
    authState.driveOk = false;

    const html = renderToStaticMarkup(<App />);

    expect(html).toContain("Onboarding Wizard");
  });

  it("renders updated scope hint when doc permissions are unavailable", () => {
    authState.connected = true;
    authState.driveOk = false;

    const html = renderToStaticMarkup(<App />);

    expect(html).toContain("docx:document");
    expect(html).toContain("docx:document.block:convert");
  });
});
