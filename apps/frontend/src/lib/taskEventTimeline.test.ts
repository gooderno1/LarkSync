import { describe, expect, it } from "vitest";

import { buildTaskEventQueryPath, shouldPollTaskEventTimeline } from "./taskEventTimeline";

describe("task event timeline helpers", () => {
  it("builds sync log query path with task, run, filter and trimmed search", () => {
    const path = buildTaskEventQueryPath({
      selectedTaskId: "task-1",
      activeRunId: "run-1",
      eventFilter: "deleted",
      eventSearch: "  delete failed  ",
      eventPage: 2,
      eventPageSize: 30,
    });

    expect(path).toContain("/sync/logs/sync?");
    expect(path).toContain("limit=30");
    expect(path).toContain("offset=30");
    expect(path).toContain("task_ids=task-1");
    expect(path).toContain("run_ids=run-1");
    expect(path).toContain("statuses=deleted");
    expect(path).toContain("statuses=delete_pending");
    expect(path).toContain("statuses=delete_failed");
    expect(path).toContain("search=delete+failed");
  });

  it("enables polling only for running event detail timelines", () => {
    expect(shouldPollTaskEventTimeline({
      enabled: true,
      detailTab: "events",
      activeRunState: "running",
    })).toBe(5_000);

    expect(shouldPollTaskEventTimeline({
      enabled: true,
      detailTab: "overview",
      activeRunState: "running",
    })).toBe(false);

    expect(shouldPollTaskEventTimeline({
      enabled: false,
      detailTab: "events",
      activeRunState: "running",
    })).toBe(false);
  });
});
