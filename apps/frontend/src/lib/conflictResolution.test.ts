import { describe, expect, it } from "vitest";

import {
  getConflictStatusMeta,
  isTaskBusyConflictError,
  summarizeConflictResolutionStates,
} from "./conflictResolution";

describe("conflict resolution helpers", () => {
  it("recognizes task-busy retryable messages", () => {
    expect(isTaskBusyConflictError("任务运行中，请稍后再试")).toBe(true);
    expect(isTaskBusyConflictError("正在同步，稍后再试")).toBe(true);
    expect(isTaskBusyConflictError("普通错误")).toBe(false);
  });

  it("summarizes queue states for the conflict panel", () => {
    const summary = summarizeConflictResolutionStates({
      a: { action: "use_local", state: "queued" },
      b: { action: "use_cloud", state: "running" },
      c: { action: "use_local", state: "waiting" },
      d: { action: "use_cloud", state: "success" },
      e: { action: "use_local", state: "error" },
    });

    expect(summary).toEqual({
      queued: 1,
      running: 1,
      waiting: 1,
      success: 1,
      failed: 1,
    });
  });

  it("builds panel status metadata for resolved and queued conflicts", () => {
    expect(getConflictStatusMeta(true, "use_cloud", undefined)).toEqual({
      label: "已处理",
      tone: "success",
      detail: "use_cloud",
    });
    expect(
      getConflictStatusMeta(false, null, {
        action: "use_local",
        state: "queued",
        message: "已加入处理队列",
      }),
    ).toEqual({
      label: "已排队",
      tone: "warning",
      detail: "已加入处理队列",
    });
  });
});
