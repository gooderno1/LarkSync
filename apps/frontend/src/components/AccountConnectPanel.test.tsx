// @vitest-environment jsdom

import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AccountConnectPanel } from "./AccountConnectPanel";

const apiFetchMock = vi.fn();
const refreshAccounts = vi.fn().mockResolvedValue(undefined);
const switchAccount = vi.fn().mockResolvedValue(undefined);
const refetchProfiles = vi.fn().mockResolvedValue(undefined);

vi.mock("../lib/api", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

vi.mock("../hooks/useAccounts", () => ({
  useAccounts: () => ({
    accounts: [{ id: "account-1", account_name: "测试账号" }],
    refreshAccounts,
    switchAccount,
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
    refreshAccounts.mockClear();
    refetchProfiles.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("第一次扫码完成后停留在检查点，点击后才进入第二次账号扫码", async () => {
    apiFetchMock.mockImplementation((endpoint: string, init?: RequestInit) => {
      if (endpoint === "/app-profiles/registration-sessions" && init?.method === "POST") {
        return Promise.resolve(registrationSession);
      }
      if (endpoint === "/app-profiles/registration-sessions/registration-1") {
        return Promise.resolve({
          status: "registered",
          app_profile: { id: "profile-1", app_id: "cli_created", display_name: "LarkSync" },
        });
      }
      if (endpoint === "/auth/device-sessions" && init?.method === "POST") {
        return Promise.resolve(deviceSession);
      }
      return Promise.resolve({ cancelled: true });
    });

    render(<AccountConnectPanel />);
    fireEvent.click(screen.getByRole("button", { name: "开始第 1 次扫码" }));
    await act(async () => Promise.resolve());
    expect(screen.getByText(/步骤 1 \/ 2/)).toBeTruthy();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });

    expect(screen.getByText("第 1 步已完成")).toBeTruthy();
    expect(screen.getByRole("button", { name: "继续第 2 次扫码" })).toBeTruthy();
    expect(
      apiFetchMock.mock.calls.filter(
        ([endpoint]) => endpoint === "/auth/device-sessions",
      ),
    ).toHaveLength(0);

    fireEvent.click(screen.getByRole("button", { name: "继续第 2 次扫码" }));
    await act(async () => Promise.resolve());

    expect(screen.getByText(/第 2 次扫码/)).toBeTruthy();
    expect(screen.getByText("备用验证码：AUTH-2")).toBeTruthy();
  });

  it("使用已有应用时明确显示本次只扫码一次", async () => {
    vi.mocked(refetchProfiles).mockResolvedValue(undefined);
    apiFetchMock.mockResolvedValue(deviceSession);

    render(<AccountConnectPanel />);

    expect(screen.getByText(/已有应用和手动配置都只需要扫码 1 次/)).toBeTruthy();
  });

  it("重新授权模式明确保留原账号数据", () => {
    render(<AccountConnectPanel mode="reauthorize" accountId="account-1" />);

    expect(screen.getByText("重新授权 测试账号")).toBeTruthy();
    expect(screen.getByText(/原账号、任务和历史数据保持不变/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "开始重新授权" })).toBeTruthy();
  });

  it("授权成功后停留在明确确认页，完成后才刷新账号并关闭", async () => {
    const onConnected = vi.fn();
    apiFetchMock.mockImplementation((endpoint: string, init?: RequestInit) => {
      if (endpoint === "/accounts/account-1/reauthorize-sessions" && init?.method === "POST") {
        return Promise.resolve(deviceSession);
      }
      if (endpoint === "/auth/device-sessions/device-1") {
        return Promise.resolve({
          status: "authorized",
          account: {
            id: "account-1",
            account_name: "测试账号",
            auth_protocol: "device_v2",
          },
        });
      }
      return Promise.resolve({ cancelled: true });
    });

    render(<AccountConnectPanel mode="reauthorize" accountId="account-1" onConnected={onConnected} />);
    fireEvent.click(screen.getByRole("button", { name: "开始重新授权" }));
    await act(async () => Promise.resolve());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });

    expect(screen.getByTestId("authorization-success")).toBeTruthy();
    expect(screen.getByText("授权成功")).toBeTruthy();
    expect(screen.getByText("Device Flow V2")).toBeTruthy();
    expect(screen.getByText("凭据已安全保存")).toBeTruthy();
    expect(refreshAccounts).not.toHaveBeenCalled();
    expect(onConnected).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "完成" }));
    await act(async () => Promise.resolve());

    expect(refreshAccounts).toHaveBeenCalledTimes(1);
    expect(onConnected).toHaveBeenCalledTimes(1);
  });

  it("区分飞书授权成功后的本机凭据保存失败并可创建新会话重试", async () => {
    apiFetchMock.mockImplementation((endpoint: string, init?: RequestInit) => {
      if (endpoint === "/accounts/account-1/reauthorize-sessions" && init?.method === "POST") {
        return Promise.resolve(deviceSession);
      }
      if (endpoint === "/auth/device-sessions/device-1") {
        return Promise.resolve({
          status: "credential_storage_failed",
          message: "飞书授权已完成，但新凭据未能安全保存。原授权仍保留。",
        });
      }
      return Promise.resolve({ cancelled: true });
    });

    render(<AccountConnectPanel mode="reauthorize" accountId="account-1" />);
    fireEvent.click(screen.getByRole("button", { name: "开始重新授权" }));
    await act(async () => Promise.resolve());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });

    expect(screen.getByText("飞书授权已完成，但新凭据未能安全保存。原授权仍保留。")).toBeTruthy();
    expect(screen.getByText("飞书授权已完成")).toBeTruthy();
    expect(refreshAccounts).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "重新扫码授权" }));
    await act(async () => Promise.resolve());

    expect(
      apiFetchMock.mock.calls.filter(
        ([endpoint, init]) =>
          endpoint === "/accounts/account-1/reauthorize-sessions" &&
          (init as RequestInit | undefined)?.method === "POST",
      ),
    ).toHaveLength(2);
  });
});
