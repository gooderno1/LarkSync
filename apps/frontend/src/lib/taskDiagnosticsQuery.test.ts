import { describe, expect, it } from "vitest";

import {
  buildTaskDiagnosticsQueryPath,
  shouldIncludeDiagnosticProblems,
  shouldPollTaskDiagnostics,
} from "./taskDiagnosticsQuery";

describe("task diagnostics query helpers", () => {
  it("builds diagnostics query path with run selection and include problems flag", () => {
    const path = buildTaskDiagnosticsQueryPath({
      selectedTaskId: "task-1",
      selectedRunId: "run-1",
      includeProblems: true,
    });

    expect(path).toContain("/sync/tasks/task-1/diagnostics?");
    expect(path).toContain("limit=200");
    expect(path).toContain("include_events=false");
    expect(path).toContain("include_problems=true");
    expect(path).toContain("run_id=run-1");
  });

  it("maps detail tabs to include problems behavior", () => {
    expect(shouldIncludeDiagnosticProblems("problems")).toBe(true);
    expect(shouldIncludeDiagnosticProblems("overview")).toBe(false);
    expect(shouldIncludeDiagnosticProblems("events")).toBe(false);
  });

  it("uses 5s polling for running tasks and 10s for idle selected tasks", () => {
    expect(shouldPollTaskDiagnostics({
      enabled: true,
      selectedTaskId: "task-1",
      selectedTaskState: "running",
    })).toBe(5_000);

    expect(shouldPollTaskDiagnostics({
      enabled: true,
      selectedTaskId: "task-1",
      selectedTaskState: "idle",
    })).toBe(10_000);

    expect(shouldPollTaskDiagnostics({
      enabled: false,
      selectedTaskId: "task-1",
      selectedTaskState: "running",
    })).toBe(false);
  });
});
