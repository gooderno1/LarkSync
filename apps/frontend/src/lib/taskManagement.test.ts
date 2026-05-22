import { describe, expect, it } from "vitest";

import {
  deletePolicyLabel,
  deriveTaskHealth,
  parseDeleteGraceMinutes,
  summarizePath,
} from "./taskManagement";

describe("taskManagement", () => {
  it("summarizes long paths with trailing segments", () => {
    expect(summarizePath("C:/work/projects/larksync/docs/specs", 2, 12)).toBe(".../docs/specs");
    expect(summarizePath("short/path")).toBe("short/path");
  });

  it("maps delete policy labels", () => {
    expect(deletePolicyLabel("off")).toBe("关闭删除联动");
    expect(deletePolicyLabel("strict")).toBe("严格删除");
    expect(deletePolicyLabel("safe")).toBe("安全删除");
  });

  it("derives task health in priority order", () => {
    expect(
      deriveTaskHealth({
        enabled: true,
        state: "failed",
        conflictCount: 2,
        lastError: "boom",
      }).label
    ).toBe("需要排查");

    expect(
      deriveTaskHealth({
        enabled: true,
        state: "idle",
        conflictCount: 1,
      }).label
    ).toBe("有冲突");

    expect(
      deriveTaskHealth({
        enabled: true,
        state: "running",
        conflictCount: 0,
      }).tone
    ).toBe("info");
  });

  it("parses delete grace minutes with strict override", () => {
    expect(parseDeleteGraceMinutes("safe", "45")).toBe(45);
    expect(parseDeleteGraceMinutes("strict", "45")).toBe(0);
    expect(parseDeleteGraceMinutes("off", "", 30)).toBe(30);
  });
});
