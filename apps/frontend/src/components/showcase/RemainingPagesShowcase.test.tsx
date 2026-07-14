import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  ActivityIssuesShowcasePage,
  ConflictResolutionShowcasePage,
  MaintenanceShowcasePage,
  SettingsShowcasePage,
} from "./RemainingPagesShowcase";
import { shouldUseRemainingPagesShowcase } from "../../lib/remainingPagesShowcase";

describe("remaining desktop pages showcase", () => {
  it("defaults to showcase only in development and supports an explicit live override", () => {
    expect(shouldUseRemainingPagesShowcase("", true)).toBe(true);
    expect(shouldUseRemainingPagesShowcase("?ui-data=live", true)).toBe(false);
    expect(shouldUseRemainingPagesShowcase("", false)).toBe(false);
  });

  it("renders a full-height activity diagnostic workspace with dense sample events", () => {
    const html = renderToStaticMarkup(<ActivityIssuesShowcasePage />);
    expect(html).toContain('data-showcase-page="activity"');
    expect(html).toContain('data-workspace-fill="true"');
    expect(html.match(/data-demo-event=/g)).toHaveLength(8);
    expect(html).toContain("前端演示数据");
  });

  it("renders a non-empty conflict decision workspace", () => {
    const html = renderToStaticMarkup(<ConflictResolutionShowcasePage />);
    expect(html).toContain('data-showcase-page="conflicts"');
    expect(html.match(/data-demo-conflict=/g)).toHaveLength(4);
    expect(html).toContain("覆盖影响");
  });

  it("renders one settings save action and populated rule context", () => {
    const html = renderToStaticMarkup(<SettingsShowcasePage />);
    expect(html).toContain('data-showcase-page="settings"');
    expect(html.match(/保存设置/g)).toHaveLength(1);
    expect(html.match(/data-demo-rule=/g)).toHaveLength(3);
    expect(html).toContain("配置状态");
  });

  it("renders one update check and keeps dangerous tasks collapsed initially", () => {
    const html = renderToStaticMarkup(<MaintenanceShowcasePage />);
    expect(html).toContain('data-showcase-page="maintenance"');
    expect(html.match(/检查更新/g)).toHaveLength(1);
    expect(html).toContain("选择任务重置");
    expect(html).not.toContain("市场资料备份");
    expect(html).toContain("版本说明");
  });
});
