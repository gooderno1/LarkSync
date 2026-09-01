// @vitest-environment jsdom

import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { OrganizationAvatar, organizationDisplayName } from "./OrganizationAvatar";
import type { AccountSummary } from "../types";

const account = {
  id: "account-abcdef",
  tenant_name: "青鸟科技",
  tenant_avatar_url: "https://example.test/logo.png",
} as AccountSummary;

describe("OrganizationAvatar", () => {
  it("uses organization identity instead of the member name", () => {
    expect(organizationDisplayName({ ...account, account_name: "张三" })).toBe("青鸟科技");
    expect(organizationDisplayName({ ...account, account_alias: "研发租户" })).toBe("研发租户");
  });

  it("never exposes an account id fragment as the organization fallback", () => {
    expect(organizationDisplayName({ id: "legacy-default-account", brand: "feishu" } as AccountSummary)).toBe("飞书组织");
    expect(organizationDisplayName({ id: "621fe8-account", brand: "lark" } as AccountSummary)).toBe("Lark 组织");
  });

  it("falls back to the organization initial when the image fails", () => {
    const view = render(<OrganizationAvatar account={account} className="logo" fallbackClassName="fallback" />);
    fireEvent.error(view.container.querySelector('[data-organization-avatar="true"]') as HTMLImageElement);
    expect(view.container.querySelector('[data-organization-avatar-fallback="true"]')?.textContent).toBe("青");
  });
});
