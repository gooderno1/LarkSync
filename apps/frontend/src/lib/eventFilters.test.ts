import { describe, expect, it } from "vitest";
import { EVENT_FILTERS, buildStatusParams } from "./eventFilters";

describe("event filters", () => {
  it("exposes direct event categories for log center filtering", () => {
    expect(EVENT_FILTERS.map((item) => item.value)).toEqual([
      "activity",
      "all",
      "queued",
      "uploaded",
      "downloaded",
      "deleted",
      "problems",
      "skipped",
      "changes",
    ]);
  });

  it("maps upload, download and delete filters to sync event statuses", () => {
    expect(buildStatusParams("uploaded")).toEqual(["uploaded"]);
    expect(buildStatusParams("downloaded")).toEqual(["downloaded"]);
    expect(buildStatusParams("deleted")).toEqual(["deleted", "delete_pending", "delete_failed"]);
  });

  it("keeps aggregate filters compatible with the existing backend statuses query", () => {
    expect(buildStatusParams("activity")).toEqual([
      "started",
      "completed",
      "success",
      "uploaded",
      "downloaded",
      "deleted",
      "delete_pending",
      "delete_failed",
      "skipped",
      "conflict",
      "failed",
      "cancelled",
      "mirrored",
    ]);
    expect(buildStatusParams("all")).toEqual([]);
    expect(buildStatusParams("queued")).toEqual(["queued"]);
    expect(buildStatusParams("problems")).toEqual(["failed", "delete_failed", "conflict", "cancelled"]);
    expect(buildStatusParams("skipped")).toEqual(["skipped"]);
    expect(buildStatusParams("changes")).toEqual([
      "uploaded",
      "downloaded",
      "deleted",
      "mirrored",
      "delete_pending",
      "conflict",
    ]);
  });
});
