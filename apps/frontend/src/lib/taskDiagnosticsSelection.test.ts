import { describe, expect, it } from "vitest";

import {
  filterTaskPickerOptions,
  getFocusedTaskOverviews,
  hasFocusedTaskActivity,
  resolveActiveRunSelection,
  resolveSelectedTaskId,
} from "./taskDiagnosticsSelection";
import type { SyncTaskOverview } from "../types";

const overviewA = {
  task: {
    id: "task-a",
    name: "知识库同步",
    local_path: "D:/Knowledge",
    cloud_folder_name: "知识库",
    cloud_folder_token: "fld_a",
  },
} as const;

const overviewB = {
  task: {
    id: "task-b",
    name: "日志归档",
    local_path: "D:/Logs",
    cloud_folder_name: "日志目录",
    cloud_folder_token: "fld_b",
  },
} as const;

type DiagnosticsOverviewOverrides = Partial<Omit<SyncTaskOverview, "task" | "status" | "counts">> & {
  task?: Partial<SyncTaskOverview["task"]>;
  status?: Partial<SyncTaskOverview["status"]>;
  counts?: Partial<SyncTaskOverview["counts"]>;
};

function makeDiagnosticsOverview(overrides: DiagnosticsOverviewOverrides = {}): SyncTaskOverview {
  const base: SyncTaskOverview = {
    task: {
      id: "task-focused",
      name: "同步任务",
      local_path: "D:/Sync",
      cloud_folder_name: "云端目录",
      cloud_folder_token: "fld_focused",
      sync_mode: "bidirectional",
      update_mode: "auto",
      enabled: true,
      created_at: 1,
      updated_at: 2,
      last_run_at: 3,
    },
    status: {
      task_id: "task-focused",
      state: "success",
      total_files: 0,
      completed_files: 0,
      failed_files: 0,
      skipped_files: 0,
      uploaded_files: 0,
      downloaded_files: 0,
      deleted_files: 0,
      conflict_files: 0,
      delete_pending_files: 0,
      delete_failed_files: 0,
      last_files: [],
    },
    last_event_at: 3,
    last_result: "success",
    problem_count: 0,
    counts: {
      total: 0,
      processed: 0,
      completed: 0,
      failed: 0,
      skipped: 0,
      uploaded: 0,
      downloaded: 0,
      deleted: 0,
      conflicts: 0,
      delete_pending: 0,
      delete_failed: 0,
    },
    current_file: null,
  };
  return {
    ...base,
    ...overrides,
    task: {
      ...base.task,
      ...overrides.task,
    },
    status: {
      ...base.status,
      ...overrides.status,
    },
    counts: {
      ...base.counts,
      ...overrides.counts,
    },
  };
}

describe("task diagnostics selection helpers", () => {
  it("resolves selected task id with fallback to the first overview", () => {
    expect(resolveSelectedTaskId([], "task-a")).toBeNull();
    expect(resolveSelectedTaskId([overviewA as never, overviewB as never], "task-b")).toBe("task-b");
    expect(resolveSelectedTaskId([overviewA as never, overviewB as never], "missing")).toBe("task-a");
  });

  it("filters task picker options by task metadata", () => {
    expect(filterTaskPickerOptions([overviewA as never, overviewB as never], "日志")).toEqual([overviewB]);
    expect(filterTaskPickerOptions([overviewA as never, overviewB as never], "D:/Knowledge")).toEqual([overviewA]);
    expect(filterTaskPickerOptions([overviewA as never, overviewB as never], "")).toEqual([overviewA, overviewB]);
  });

  it("keeps only tasks with visible diagnostic activity in focused mode", () => {
    const emptyOverview = makeDiagnosticsOverview({
      task: { id: "empty", name: "全零任务" },
    });
    const deletePendingOverview = makeDiagnosticsOverview({
      task: { id: "delete-pending", name: "待删除任务" },
      counts: { delete_pending: 1 },
    });
    const failedOverview = makeDiagnosticsOverview({
      task: { id: "failed", name: "失败任务" },
      status: { failed_files: 1 },
    });
    const runningOverview = makeDiagnosticsOverview({
      task: { id: "running", name: "运行任务" },
      status: { state: "running" },
    });

    expect(hasFocusedTaskActivity(emptyOverview)).toBe(false);
    expect(getFocusedTaskOverviews([
      emptyOverview,
      deletePendingOverview,
      failedOverview,
      runningOverview,
    ]).map((overview) => overview.task.id)).toEqual([
      "delete-pending",
      "failed",
      "running",
    ]);
  });

  it("resolves active run selection from explicit selection, diagnostics fallback or latest run", () => {
    const recentRuns = [
      { run_id: "run-1", state: "success" },
      { run_id: "run-2", state: "running" },
    ] as never[];

    expect(resolveActiveRunSelection({
      recentRuns,
      selectedRunId: "run-2",
      diagnosticsSelectedRunId: "run-1",
    })).toMatchObject({
      activeRunId: "run-2",
      activeRunSummary: { run_id: "run-2" },
    });

    expect(resolveActiveRunSelection({
      recentRuns,
      selectedRunId: "missing",
      diagnosticsSelectedRunId: "run-1",
    })).toMatchObject({
      activeRunId: "run-1",
      activeRunSummary: { run_id: "run-1" },
    });

    expect(resolveActiveRunSelection({
      recentRuns,
      selectedRunId: null,
      diagnosticsSelectedRunId: null,
    })).toMatchObject({
      activeRunId: "run-1",
      activeRunSummary: { run_id: "run-1" },
    });
  });

  it("prefers the latest run with real activity over a newer empty check", () => {
    const recentRuns = [
      {
        run_id: "check-newer",
        state: "success",
        problem_count: 0,
        counts: { uploaded: 0, downloaded: 0, deleted: 0, failed: 0, conflicts: 0, delete_pending: 0, delete_failed: 0 },
      },
      {
        run_id: "activity-older",
        state: "success",
        problem_count: 0,
        counts: { uploaded: 1, downloaded: 0, deleted: 0, failed: 0, conflicts: 0, delete_pending: 0, delete_failed: 0 },
      },
    ] as never[];

    expect(resolveActiveRunSelection({
      recentRuns,
      selectedRunId: null,
      diagnosticsSelectedRunId: "check-newer",
    })).toMatchObject({
      activeRunId: "activity-older",
      activeRunSummary: { run_id: "activity-older" },
    });

    expect(resolveActiveRunSelection({
      recentRuns,
      selectedRunId: "check-newer",
      diagnosticsSelectedRunId: "check-newer",
    })).toMatchObject({
      activeRunId: "check-newer",
    });
  });
});
