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

  it("renders a full-height activity workspace without partial first-screen cards", () => {
    const html = renderToStaticMarkup(<ActivityIssuesShowcasePage />);
    expect(html).toContain('data-showcase-page="activity"');
    expect(html).toContain('data-workspace-fill="true"');
    expect(html).toContain('data-activity-task-selector="true"');
    expect(html).toContain('data-activity-run-search="true"');
    expect(html).toContain("grid-cols-[276px_minmax(0,1fr)_416px]");
    expect(html.match(/data-activity-summary=/g)).toHaveLength(4);
    expect(html).toContain('data-activity-summary-grid="two-by-two"');
    expect(html).toContain("grid-cols-2");
    expect(html).toContain('data-activity-timeline-filters="true"');
    expect(html).toContain('data-activity-timeline-line="true"');
    expect(html).toContain("left-[83px]");
    expect(html.match(/data-activity-timeline-dot=/g)).toHaveLength(5);
    expect(html).toContain("justify-self-center");
    expect(html).toContain('data-activity-error-detail="true"');
    expect(html).toContain('data-activity-diagnosis-actions="true"');
    expect(html.match(/data-demo-run=/g)).toHaveLength(5);
    expect(html.match(/data-demo-event=/g)).toHaveLength(5);
    expect(html).toContain("显示全部事件");
    expect(html).toContain("基础信息");
    expect(html).toContain("错误码");
    expect(html).toContain('data-visibility-region="activity-runs"');
    expect(html).toContain('data-visibility-card="activity-run"');
    expect(html).not.toContain("grid-rows-[68px_minmax(0,1fr)]");
    expect(html).not.toContain("min-h-[760px]");
    expect(html).toContain("前端演示数据");
  });

  it("renders a non-empty conflict decision workspace", () => {
    const html = renderToStaticMarkup(<ConflictResolutionShowcasePage />);
    expect(html).toContain('data-showcase-page="conflicts"');
    expect(html.match(/data-demo-conflict=/g)).toHaveLength(4);
    expect(html).toContain('data-visibility-region="conflict-queue"');
    expect(html).toContain('data-visibility-card="conflict"');
    expect(html).toContain("覆盖影响");
  });

  it("renders one settings save action and populated rule context", () => {
    const html = renderToStaticMarkup(<SettingsShowcasePage />);
    expect(html).toContain('data-showcase-page="settings"');
    expect(html.match(/保存设置/g)).toHaveLength(1);
    expect(html.match(/data-demo-rule=/g)).toHaveLength(3);
    expect(html).toContain('data-visibility-region="settings-left"');
    expect(html).toContain('data-visibility-card="settings-directory"');
    expect(html).toContain("配置状态");
  });

  it("renders one update check and keeps dangerous tasks collapsed initially", () => {
    const html = renderToStaticMarkup(<MaintenanceShowcasePage />);
    expect(html).toContain('data-showcase-page="maintenance"');
    expect(html.match(/检查更新/g)).toHaveLength(1);
    expect(html).toContain("选择任务重置");
    expect(html).not.toContain("市场资料备份");
    expect(html).toContain("版本说明");
    expect(html).toContain("安装前检查");
    expect(html).toContain('data-maintenance-summary-grid="true"');
    expect(html).toContain('data-visibility-region="maintenance-main"');
  });
});
