// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { AppProfile } from "../../types";
import { SettingsAppProfilesPanel } from "./SettingsAppProfilesPanel";

const profiles: AppProfile[] = [
  {
    id: "profile-feishu",
    brand: "feishu",
    app_id: "cli_feishu_1234",
    display_name: "客户文档同步",
    source: "official_registration",
    enabled: true,
    has_secret: true,
    created_at: 1_788_243_200,
    updated_at: 1_788_243_200,
    linked_account_count: 2,
    recoverable_account_count: 0,
  },
  {
    id: "profile-lark",
    brand: "lark",
    app_id: "cli_lark_9ce8",
    display_name: "海外知识库",
    source: "manual",
    enabled: true,
    has_secret: true,
    created_at: 1_788_329_600,
    updated_at: 1_788_329_600,
    linked_account_count: 0,
    recoverable_account_count: 1,
  },
];

describe("SettingsAppProfilesPanel", () => {
  it("默认只显示应用统计，展开后才显示紧凑列表和管理入口", () => {
    const onEdit = vi.fn();
    render(
      <SettingsAppProfilesPanel
        profiles={profiles}
        activeProfileId="profile-feishu"
        onEdit={onEdit}
      />,
    );

    expect(screen.getByText("2 个应用 · 1 个正在使用 · 1 个账号可恢复")).toBeTruthy();
    expect(screen.queryByText("客户文档同步")).toBeNull();
    expect(screen.queryByRole("link", { name: /应用管理/ })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "展开应用配置" }));

    expect(screen.getByText("客户文档同步")).toBeTruthy();
    expect(screen.getByText("海外知识库")).toBeTruthy();
    const managementLinks = screen.getAllByRole("link", { name: /应用管理/ });
    expect(managementLinks[0].getAttribute("href")).toBe("https://open.feishu.cn/app/cli_feishu_1234");
    expect(managementLinks[1].getAttribute("href")).toBe("https://open.larksuite.com/app/cli_lark_9ce8");
    expect(managementLinks[0].getAttribute("target")).toBe("_blank");
    expect(managementLinks[0].getAttribute("rel")).toContain("noopener");

    fireEvent.click(screen.getAllByRole("button", { name: "改名" })[1]);
    expect(onEdit).toHaveBeenCalledWith(profiles[1]);

    fireEvent.click(screen.getByRole("button", { name: "收起应用配置" }));
    expect(screen.queryByText("客户文档同步")).toBeNull();
  });

  it("无应用时保留紧凑空摘要并禁用展开", () => {
    render(<SettingsAppProfilesPanel profiles={[]} activeProfileId={null} onEdit={vi.fn()} />);

    expect(screen.getByText("尚无应用配置")).toBeTruthy();
    expect(screen.getByRole("button", { name: "暂无应用配置" }).hasAttribute("disabled")).toBe(true);
  });
});
