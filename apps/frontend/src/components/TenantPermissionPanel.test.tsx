// @vitest-environment jsdom

import { fireEvent, render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TenantPermissionPanel } from "./TenantPermissionPanel";
import { apiFetch } from "../lib/api";

vi.mock("qrcode", () => ({
  toDataURL: vi.fn().mockResolvedValue("data:image/png;base64,permission-qr"),
}));

vi.mock("../lib/api", () => ({
  apiFetch: vi.fn(),
}));

describe("TenantPermissionPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders a QR code for the validated official permission URL", async () => {
    const view = render(
      <TenantPermissionPanel
        accountId="account-1"
        organizationName="青鸟科技"
        permissionUrl="https://open.feishu.cn/app/cli_test/auth?q=tenant%3Atenant%3Areadonly&token_type=tenant"
        onClose={vi.fn()}
        onResolved={vi.fn()}
      />,
    );

    await waitFor(() => expect((view.getByTestId("tenant-permission-qr") as HTMLImageElement).src).toBe("data:image/png;base64,permission-qr"));
    expect(view.getByText("扫码开通组织信息权限")).toBeTruthy();
    expect(view.getByText("这不是账号重新登录")).toBeTruthy();
  });

  it("checks the permission immediately and reports success", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ status: "ready", tenant_name: "青鸟科技" });
    const onResolved = vi.fn().mockResolvedValue(undefined);
    const view = render(
      <TenantPermissionPanel
        accountId="account-1"
        organizationName="青鸟科技"
        permissionUrl="https://open.feishu.cn/app/cli_test/auth?q=tenant%3Atenant%3Areadonly&token_type=tenant"
        onClose={vi.fn()}
        onResolved={onResolved}
      />,
    );

    fireEvent.click(view.getByRole("button", { name: "我已开通，立即检查" }));
    await waitFor(() => expect(view.getByText("权限已开通，组织信息已更新")).toBeTruthy());
    expect(apiFetch).toHaveBeenCalledWith("/accounts/account-1/tenant-metadata/refresh", { method: "POST" });
    expect(onResolved).toHaveBeenCalledOnce();
  });
});
