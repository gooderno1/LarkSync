import { describe, expect, it } from "vitest";

import { buildProblemQuery } from "./useProblems";

describe("problem query", () => {
  it("keeps list reads separate from background source refresh", () => {
    const path = buildProblemQuery({
      state: "open,in_progress,waiting",
      categories: [],
      severities: [],
      taskId: "",
      search: "",
      since: null,
      offset: 0,
      limit: 50,
    });

    expect(path).toContain("refresh=false");
  });
});
