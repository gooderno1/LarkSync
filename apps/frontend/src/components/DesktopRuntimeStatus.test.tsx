// @vitest-environment jsdom
import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DesktopTopBar } from "./DesktopTopBar";
import { Sidebar } from "./Sidebar";

const state = vi.hoisted(() => ({
  stale: false, running: 1,
  tasks: [{ id: "busy", enabled: true }, { id: "ready", enabled: true }],
  runTask: vi.fn(),
}));
vi.mock("../hooks/useDesktopStatus", () => ({ useDesktopStatus: () => ({
  status: {
    runtime: { profile: "production", backend_running: true },
    auth: { connected: true, account_name: "测试账号" },
    tasks: { enabled: 2, running: state.running },
    update: { current_version: "v1.1.0" },
  }, stale: state.stale, refetch: vi.fn(),
}) }));
vi.mock("../hooks/useTasks", () => ({ useTasks: () => ({
  tasks: state.tasks,
  statusMap: { busy: { state: "success", runtime: { active: true } }, ready: { state: "success" } },
  runTask: state.runTask,
}) }));
vi.mock("../hooks/useProblems", () => ({ useProblemSummary: () => ({ summary: { unresolved: 0 } }) }));
vi.mock("../hooks/useAccounts", () => ({ useAccounts: () => ({
  activeAccount: { id: "test", state: "connected", paused: false }, accounts: [], switchAccount: vi.fn(),
}) }));
vi.mock("./ui/toast", () => ({ useToast: () => ({ toast: vi.fn() }) }));

afterEach(() => { cleanup(); state.stale = false; state.running = 1; state.runTask.mockClear(); });

describe("desktop runtime indicators", () => {
  it("skips a task in preflight when triggering all enabled tasks", () => {
    const view = render(<DesktopTopBar activeTab="dashboard" onNavigate={vi.fn()} />);
    fireEvent.click(view.getByRole("button", { name: "立即同步" }));
    expect(state.runTask).toHaveBeenCalledExactlyOnceWith(state.tasks[1]);
  });
  it("does not present an expired running count as current", () => {
    state.stale = true;
    const view = render(<DesktopTopBar activeTab="dashboard" onNavigate={vi.fn()} />);
    expect(view.getByText("— 个正在运行")).toBeTruthy();
    expect(view.getByRole("button", { name: "立即同步" }).hasAttribute("disabled")).toBe(true);
  });
  it("shows connected when idle and an explicit unknown state when stale", () => {
    state.running = 0;
    const view = render(<Sidebar activeTab="dashboard" onNavigate={vi.fn()} unresolvedConflicts={0} />);
    expect(view.queryByText(/飞书成员 · 同步中/)).toBeNull();
    expect(view.getByText(/飞书成员 · 已连接/)).toBeTruthy();
    state.stale = true;
    view.rerender(<Sidebar activeTab="dashboard" onNavigate={vi.fn()} unresolvedConflicts={0} />);
    expect(view.getByText(/飞书成员 · 状态待更新/)).toBeTruthy();
  });
});
