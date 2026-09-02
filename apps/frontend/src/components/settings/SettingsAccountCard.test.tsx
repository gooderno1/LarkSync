// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import type { AccountSummary } from "../../types";
import { SettingsAccountCard } from "./SettingsAccountCard";

const account: AccountSummary = {
  id: "account-1",
  app_profile_id: "profile-1",
  brand: "feishu",
  open_id: "ou_1",
  account_name: "晏玮奇",
  tenant_name: "星河科技",
  state: "connected",
  granted_scopes: [],
  paused: false,
  auth_protocol: "device_v2",
  unread_total: 3,
  unread_errors: 1,
  unread_messages: 2,
  is_active: true,
  app_display_name: "LarkSync · 星河科技",
  app_id: "cli_123456789F2C",
  app_source: "official_registration",
  app_created_at: 1_788_243_200,
};

function Harness() {
  const [expanded, setExpanded] = useState(false);
  return (
    <SettingsAccountCard
      account={account}
      active
      expanded={expanded}
      refreshing={false}
      onToggle={() => setExpanded((value) => !value)}
      onSwitch={vi.fn()}
      onRefresh={vi.fn()}
      onEditAlias={vi.fn()}
      onReauthorize={vi.fn()}
      onAction={vi.fn()}
    />
  );
}

describe("SettingsAccountCard", () => {
  it("默认仅展示可辨识摘要，点击后才显示授权与维护操作", () => {
    render(<Harness />);

    expect(screen.getByText("星河科技")).toBeTruthy();
    expect(screen.getByText(/LarkSync · 星河科技/)).toBeTruthy();
    expect(screen.getByText(/…9F2C/)).toBeTruthy();
    expect(screen.queryByText("访问凭据有效至")).toBeNull();
    expect(screen.queryByRole("button", { name: "重新授权" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "展开星河科技详情" }));

    expect(screen.getByText("访问凭据有效至")).toBeTruthy();
    expect(screen.getByRole("button", { name: "重新授权" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "修改组织名称" })).toBeTruthy();
  });
});
