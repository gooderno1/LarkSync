import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { ActivityIssuesPage } from "./ActivityIssuesPage";

const task = {
  id: "task-1",
  name: "项目文档同步",
  local_path: "D:/Knowledge/FeishuMirror/ProjectDocs",
  cloud_folder_token: "fld_123",
  cloud_folder_name: "项目文档",
  sync_mode: "bidirectional",
  update_mode: "auto",
  md_sync_mode: "enhanced",
  enabled: true,
  created_at: 1,
  updated_at: 2,
  last_run_at: 3,
};

const status = {
  task_id: "task-1",
  state: "failed",
  total_files: 10,
  completed_files: 8,
  failed_files: 1,
  skipped_files: 0,
  uploaded_files: 2,
  downloaded_files: 3,
  deleted_files: 0,
  conflict_files: 1,
  delete_pending_files: 0,
  delete_failed_files: 0,
  last_error: "forbidden",
  current_run_id: "run-1",
  last_files: [],
};

const event = {
  taskId: "task-1",
  taskName: "项目文档同步",
  timestamp: 3,
  status: "failed",
  path: "D:/Knowledge/FeishuMirror/ProjectDocs/a.md",
  message: "forbidden",
  runId: "run-1",
};

vi.mock("@tanstack/react-query", () => ({
  useQuery: () => ({
    data: { total: 1, items: [event] },
    isLoading: false,
    isFetching: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock("../hooks/useTasks", () => ({
  useTasks: () => ({
    runTask: vi.fn(),
  }),
}));

vi.mock("../hooks/useLogCenterTaskDiagnostics", () => ({
  useLogCenterTaskDiagnostics: () => ({
    selectedTaskId: "task-1",
    setSelectedRunId: vi.fn(),
    taskPickerQuery: "",
    setTaskPickerQuery: vi.fn(),
    showAllTasks: false,
    setShowAllTasks: vi.fn(),
    hiddenTaskCount: 0,
    focusedTaskCount: 1,
    overviewQuery: { isLoading: false },
    taskPickerOptions: [
      {
        task,
        status,
        last_event_at: 3,
        last_result: "failed",
        problem_count: 1,
        counts: {
          total: 10,
          processed: 8,
          completed: 8,
          failed: 1,
          skipped: 0,
          uploaded: 2,
          downloaded: 3,
          deleted: 0,
          conflicts: 1,
          delete_pending: 0,
          delete_failed: 0,
        },
        current_file: null,
      },
    ],
    selectTask: vi.fn(),
    selectedTask: task,
    selectedStatus: status,
    recentRuns: [
      {
        run_id: "run-1",
        state: "failed",
        started_at: 1,
        finished_at: 3,
        last_event_at: 3,
        last_error: "forbidden",
        problem_count: 1,
        counts: {
          total: 10,
          processed: 8,
          completed: 8,
          failed: 1,
          skipped: 0,
          uploaded: 2,
          downloaded: 3,
          deleted: 0,
          conflicts: 1,
          delete_pending: 0,
          delete_failed: 0,
        },
        current_file: null,
      },
    ],
    activeRunId: "run-1",
    selectedRun: { run_id: "run-1" },
    selectedProblems: [event],
    diagnosticCounts: {
      uploaded: 2,
      downloaded: 3,
      deleted: 0,
      failed: 1,
      conflicts: 1,
    },
    lastActivityAt: 3,
    selectedStateKey: "failed",
    refreshDiagnostics: vi.fn(),
    setDetailTab: vi.fn(),
  }),
}));

vi.mock("../components/ui/toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

describe("ActivityIssuesPage smoke", () => {
  it("renders the independent light troubleshooting workspace", () => {
    const html = renderToStaticMarkup(<ActivityIssuesPage />);

    expect(html).toContain("问题摘要");
    expect(html).toContain("任务选择");
    expect(html).toContain("运行历史");
    expect(html).toContain("事件时间线");
    expect(html).toContain("事件详情");
    expect(html).toContain("建议动作");
    expect(html).toContain("grid-cols-[280px_minmax(0,1fr)_400px]");
    expect(html).toContain("grid-cols-2");
    expect(html).not.toContain("grid grid-cols-4 gap-4");
    expect(html).not.toContain("min-[1760px]");
    expect(html).not.toContain("min-[1440px]");
    expect(html).not.toContain("min-[1280px]:grid-cols-[300px_minmax(0,1fr)_320px]");
    expect(html).not.toContain("日志中心");
  });
});
