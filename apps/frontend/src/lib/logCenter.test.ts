import { describe, expect, it } from "vitest";

import {
  compactRunId,
  diagnosticActivityTime,
  formatDuration,
  mapSyncLogResponse,
  shortPath,
} from "./logCenter";

describe("log center helpers", () => {
  it("maps sync log response to frontend shape", () => {
    const mapped = mapSyncLogResponse({
      total: 1,
      items: [
        {
          task_id: "task-1",
          task_name: "日志任务",
          timestamp: 100,
          status: "uploaded",
          path: "D:/Docs/spec.md",
          message: "ok",
          run_id: "run-1",
        },
      ],
      warning: "warn",
      meta: { file_size_bytes: 12 },
    });

    expect(mapped).toEqual({
      total: 1,
      items: [
        {
          taskId: "task-1",
          taskName: "日志任务",
          timestamp: 100,
          status: "uploaded",
          path: "D:/Docs/spec.md",
          message: "ok",
          runId: "run-1",
        },
      ],
      warning: "warn",
      meta: { file_size_bytes: 12 },
    });
  });

  it("picks the latest available diagnostic activity timestamp", () => {
    expect(
      diagnosticActivityTime({
        last_event_at: null,
        status: { finished_at: 50, started_at: 40 },
        task: { last_run_at: 30, updated_at: 20, created_at: 10 },
      } as never),
    ).toBe(50);
  });

  it("formats duration, paths and run ids for compact display", () => {
    expect(formatDuration(100, 145)).toBe("45 秒");
    expect(formatDuration(100, 225)).toBe("2 分 5 秒");
    expect(formatDuration(100, 3700)).toBe("1 小时 0 分");
    expect(shortPath("D:/Knowledge/Projects/LarkSync/docs/specs/long/path/file.md", 24)).toContain("...");
    expect(compactRunId("12345678-abcdef-987654")).toBe("12345678...987654");
  });
});
