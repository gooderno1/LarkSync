// @vitest-environment jsdom

import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AccountConnectPanel } from "./AccountConnectPanel";

const apiFetchMock = vi.fn();
const refreshAccounts = vi.fn().mockResolvedValue(undefined);
const refetchProfiles = vi.fn().mockResolvedValue(undefined);

vi.mock("../lib/api", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

vi.mock("../hooks/useAccounts", () => ({
  useAccounts: () => ({
    accounts: [{ id: "account-1", account_name: "测试账号" }],
    refreshAccounts,
  }),
}));

vi.mock("@tanstack/react-query", () => ({
  useQuery: () => ({ data: [], refetch: refetchProfiles }),
}));

vi.mock("qrcode", () => ({
  toDataURL: vi.fn().mockResolvedValue("data:image/png;base64,qr"),
}));

const registrationSession = {
  session_id: "registration-1",
  status: "pending",
  brand: "feishu",
  user_code: "REG-1",
  verification_uri: "https://example.com/register",
  verification_uri_complete: "https://example.com/register?code=REG-1",
  expires_at: 10_000,
  interval: 1,
};

const deviceSession = {
  session_id: "device-1",
  status: "pending",
  brand: "feishu",
  user_code: "AUTH-2",
  verification_uri: "https://example.com/login",
  verification_uri_complete: "https://example.com/login?code=AUTH-2",
  expires_at: 10_000,
  interval: 1,
};

describe("AccountConnectPanel", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    apiFetchMock.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("第一次扫码完成后在原流程自动进入第二次账号扫码", async () => {
    apiFetchMock.mockImplementation((endpoint: string, init?: RequestInit) => {
      if (endpoint === "/app-profiles/registration-sessions" && init?.method === "POST") {
        return Promise.resolve(registrationSession);
      }
      if (endpoint === "/app-profiles/registration-sessions/registration-1") {
        return Promise.resolve({
          status: "registered",
          app_profile: { id: "profile-1" },
          next_session: deviceSession,
        });
      }
      return Promise.resolve({ cancelled: true });
    });

    render(<AccountConnectPanel />);
    fireEvent.click(screen.getByRole("button", { name: "开始两步扫码" }));
    await act(async () => Promise.resolve());
    expect(screen.getByText(/步骤 1 \/ 2/)).toBeTruthy();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });

    expect(screen.getByText(/步骤 2 \/ 2/)).toBeTruthy();
    expect(screen.getByText("备用验证码：AUTH-2")).toBeTruthy();
  });

  it("重新授权模式明确保留原账号数据", () => {
    render(<AccountConnectPanel mode="reauthorize" accountId="account-1" />);

    expect(screen.getByText("重新授权 测试账号")).toBeTruthy();
    expect(screen.getByText(/原账号、任务和历史数据保持不变/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "开始重新授权" })).toBeTruthy();
  });
});
