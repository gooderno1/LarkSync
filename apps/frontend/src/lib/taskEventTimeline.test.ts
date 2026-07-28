import { describe, expect, it } from "vitest";

import { buildTaskEventQueryPath, shouldPollTaskEventTimeline } from "./taskEventTimeline";

describe("task event timeline helpers", () => {
  it("uses the selective run query without the broad task condition", () => {
    const path = buildTaskEventQueryPath({
      selectedTaskId: "task-1",
      activeRunId: "run-1",
      eventFilter: "deleted",
      eventSearch: "  delete failed  ",
      eventPage: 2,
      eventPageSize: 30,
      since: 100,
      until: 200,
    });

    expect(path).toContain("/sync/logs/sync?");
    expect(path).toContain("limit=30");
    expect(path).toContain("offset=30");
    expect(path).not.toContain("task_ids=task-1");
    expect(path).toContain("run_ids=run-1");
    expect(path).toContain("statuses=deleted");
    expect(path).toContain("statuses=delete_pending");
    expect(path).toContain("statuses=delete_failed");
    expect(path).toContain("search=delete+failed");
    expect(path).toContain("since=100");
    expect(path).toContain("until=200");
  });

  it("falls back to a task query when no run is selected", () => {
    const path = buildTaskEventQueryPath({
      selectedTaskId: "task-1",
      activeRunId: null,
      eventFilter: "activity",
      eventSearch: "",
      eventPage: 1,
      eventPageSize: 30,
    });

    expect(path).toContain("task_ids=task-1");
    expect(path).not.toContain("run_ids=");
    expect(path).not.toContain("statuses=queued");
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
