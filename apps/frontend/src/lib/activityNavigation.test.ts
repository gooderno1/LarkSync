import { describe, expect, it } from "vitest";

import { parseActivityLink, parseProblemLink } from "./activityNavigation";

describe("activity/problem deep links", () => {
  it("parses internal activity context without exposing evidence", () => {
    expect(parseActivityLink("#activity?task_id=t-1&run_id=r-1&event_id=e-1")).toEqual({
      taskId: "t-1",
      runId: "r-1",
      eventId: "e-1",
    });
  });

  it("parses legacy conflict route into problem filters", () => {
    expect(parseProblemLink("#conflicts?type=conflict&problem_id=p-1")).toEqual({
      taskId: null,
      runId: null,
      problemId: "p-1",
      category: "conflict",
    });
  });
});
