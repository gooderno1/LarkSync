// @vitest-environment jsdom

import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Sidebar } from "./Sidebar";

vi.mock("../hooks/useDesktopStatus", () => ({
  useDesktopStatus: () => ({
    status: {
      runtime: { profile: "production", backend_running: true },
      auth: { connected: true },
      tasks: { last_sync_time: null },
      update: { current_version: "v0.9.5" },
    },
  }),
}));

vi.mock("../hooks/useAccounts", () => ({
  useAccounts: () => ({
    accounts: [{ id: "account-1", account_name: "张三", tenant_name: "青鸟科技", state: "connected", paused: false, unread_total: 2 }],
    activeAccount: { id: "account-1", account_name: "张三", tenant_name: "青鸟科技", state: "connected", paused: false, unread_total: 2 },
    switchAccount: vi.fn(),
    switchingAccountId: null,
  }),
}));

describe("Sidebar organization switcher", () => {
  it("uses the same flat navigation language as the app sections", () => {
    const view = render(<Sidebar activeTab="dashboard" onNavigate={vi.fn()} unresolvedConflicts={0} />);
    fireEvent.click(view.getByRole("button", { name: /青鸟科技/ }));
    const html = view.container.innerHTML;

    expect(html).toContain('data-sidebar-current-organization="true"');
    expect(html).toContain('data-sidebar-organization-drawer="true"');
    expect(html).toContain("w-[244px]");
    expect(html).toContain("青鸟科技");
    expect(html).toContain("切换组织");
    expect(html).not.toContain("shadow-[0_8px_24px_rgba(51,112,255,0.06)]");
    expect(html).not.toContain("添加飞书组织或账号");
    expect(html).toContain("添加组织或账号");
  });
});
