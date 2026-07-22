import { describe, expect, it } from "vitest";

import { problemCategoryLabel, problemSeverityTone, shouldKeepProblemSelection } from "./problemCenter";

describe("problem center helpers", () => {
  it("maps backend classifications without reclassifying messages", () => {
    expect(problemCategoryLabel("auth_permission")).toBe("权限认证");
    expect(problemCategoryLabel("network_remote")).toBe("网络与云端");
    expect(problemSeverityTone("critical")).toBe("danger");
    expect(problemSeverityTone("low")).toBe("info");
  });

  it("keeps selection only while the entity still exists", () => {
    expect(shouldKeepProblemSelection("p-1", ["p-1", "p-2"])).toBe(true);
    expect(shouldKeepProblemSelection("p-1", ["p-2"])).toBe(false);
    expect(shouldKeepProblemSelection(null, ["p-2"])).toBe(false);
  });
});
