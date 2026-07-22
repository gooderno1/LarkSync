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
    sortedOverviews: [
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
    eventFilter: "all",
    setEventFilter: vi.fn(),
    eventSearch: "",
    setEventSearch: vi.fn(),
    eventPage: 1,
    setEventPage: vi.fn(),
    eventPageSize: 30,
    setEventPageSize: vi.fn(),
    setEventTimeRange: vi.fn(),
    selectedTimelineEntries: [event],
    selectedTimelineTotal: 1,
    selectedEventsQuery: { isFetching: false },
  }),
}));

vi.mock("../components/ui/toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

describe("ActivityIssuesPage smoke", () => {
  it("renders the independent light troubleshooting workspace", () => {
    const html = renderToStaticMarkup(<ActivityIssuesPage />);

    expect(html).toContain("活动管理");
    expect(html).toContain("任务列表");
    expect(html).toContain("全部事件");
    expect(html).toContain("时间");
    expect(html).toContain("对象");
    expect(html).toContain('data-activity-management="true"');
    expect(html).toContain('data-window-layout="standard"');
    expect(html).toContain("grid-cols-[248px_minmax(720px,1fr)]");
    expect(html).not.toContain("grid-cols-[276px_minmax(0,1fr)_416px]");
    expect(html).not.toContain("日志中心");
  });

  it("renders compact as a single event master view", () => {
    const html = renderToStaticMarkup(<ActivityIssuesPage layoutMode="compact" />);

    expect(html).toContain('data-window-layout="compact"');
    expect(html).toContain("grid-cols-1");
    expect(html).toContain('aria-label="选择活动任务"');
    expect(html).toContain('aria-label="选择活动运行"');
    expect(html).not.toContain("任务列表");
    expect(html).not.toContain("运行列表");
  });

  it("renders wide with persistent task, run and event columns", () => {
    const html = renderToStaticMarkup(<ActivityIssuesPage layoutMode="wide" />);

    expect(html).toContain('data-window-layout="wide"');
    expect(html).toContain("grid-cols-[248px_288px_minmax(640px,1fr)]");
    expect(html).toContain("任务列表");
    expect(html).toContain("运行列表");
  });
});
