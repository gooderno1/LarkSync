import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { StatCard } from "./StatCard";

describe("StatCard", () => {
  it("keeps long summary values and two-line explanations readable", () => {
    const html = renderToStaticMarkup(
      <StatCard
        label="最近同步"
        value="15 小时前"
        hint="同步时间来自最近一次成功完成的任务记录"
        valueClassName="text-[21px]"
      />,
    );

    expect(html).toContain("text-[21px]");
    expect(html).toContain("whitespace-nowrap");
    expect(html).toContain("line-clamp-2");
    expect(html).toContain('data-stat-card="true"');
    expect(html).toContain('data-stat-card-icon="true"');
    expect(html).toContain("overflow-hidden");
    expect(html).toContain("px-3.5");
    expect(html).not.toContain("mt-2 truncate font-semibold");
  });
});
