import { describe, expect, it } from "vitest";

import {
  deriveTaskDiagnosticsState,
  getRunAlertMeta,
  sortTaskOverviewsByActivity,
} from "./taskDiagnosticsState";

describe("task diagnostics state helpers", () => {
  it("sorts task overviews by latest activity descending", () => {
    const sorted = sortTaskOverviewsByActivity([
      {
        task: { id: "task-a", created_at: 1, updated_at: 10 },
        status: { started_at: 20 },
      },
      {
        task: { id: "task-b", created_at: 1, updated_at: 10 },
        status: { finished_at: 30 },
      },
    ] as never[]);

    expect(sorted.map((item) => item.task.id)).toEqual(["task-b", "task-a"]);
  });

  it("maps interrupted and generic error messages to alert metadata", () => {
    expect(getRunAlertMeta("运行被中断：用户取消")).toMatchObject({
      label: "最近中断",
      className: "border-amber-500/40 bg-amber-500/10 text-amber-300",
    });

    expect(getRunAlertMeta("上传失败")).toMatchObject({
      label: "最近错误",
      className: "border-rose-500/40 bg-rose-500/10 text-rose-300",
    });
  });

  it("derives display state from selected run and overview fallbacks", () => {
    const derived = deriveTaskDiagnosticsState({
      selectedTask: {
        id: "task-1",
        enabled: true,
        created_at: 1,
        updated_at: 2,
        local_path: "D:/Knowledge",
        cloud_folder_token: "fld_123",
        sync_mode: "bidirectional",
        last_run_at: 15,
      } as never,
      selectedStatus: {
        state: "running",
        started_at: 12,
        last_error: "上传失败",
      } as never,
      selectedRun: {
        last_event_at: 20,
        counts: { uploaded: 2 },
        current_file: { path: "D:/Knowledge/README.md" },
      } as never,
      activeOverview: {
        counts: { uploaded: 1 },
        current_file: { path: "D:/Knowledge/OLD.md" },
        last_event_at: 18,
      } as never,
    });

    expect(derived.currentFile).toMatchObject({ path: "D:/Knowledge/README.md" });
    expect(derived.diagnosticCounts).toMatchObject({ uploaded: 2 });
    expect(derived.lastActivityAt).toBe(20);
    expect(derived.selectedStateKey).toBe("running");
    expect(derived.runAlert?.label).toBe("最近错误");
  });
});
