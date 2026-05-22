import { describe, expect, it } from "vitest";

import {
  filterTaskPickerOptions,
  resolveActiveRunSelection,
  resolveSelectedTaskId,
} from "./taskDiagnosticsSelection";

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
});
