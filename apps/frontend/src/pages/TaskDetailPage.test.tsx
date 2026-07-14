import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { TaskDetailPage } from "./TaskDetailPage";

const task = {
  id: "task-1",
  name: "项目文档同步",
  local_path: "D:/Knowledge/FeishuMirror/ProjectDocs",
  cloud_folder_token: "fld_123",
  cloud_folder_name: "我的空间 / 项目文档",
  sync_mode: "bidirectional",
  update_mode: "auto",
  md_sync_mode: "enhanced",
  ignored_subpaths: [".git/", "node_modules/"],
  enabled: true,
  created_at: 1,
  updated_at: 2,
  last_run_at: 3,
};

const status = {
  task_id: "task-1",
  state: "running",
  total_files: 100,
  completed_files: 68,
  failed_files: 0,
  skipped_files: 3,
  uploaded_files: 12,
  downloaded_files: 8,
  deleted_files: 0,
  conflict_files: 1,
  delete_pending_files: 0,
  delete_failed_files: 0,
  current_run_id: "run-1",
  last_files: [],
  started_at: 1,
  finished_at: null,
};

const diagnostics = {
  overview: {
    task,
    status,
    last_event_at: 3,
    last_result: "running",
    problem_count: 1,
    counts: {
      total: 100,
      processed: 68,
      completed: 68,
      failed: 0,
      skipped: 3,
      uploaded: 12,
      downloaded: 8,
      deleted: 0,
      conflicts: 1,
      delete_pending: 0,
      delete_failed: 0,
    },
    current_file: null,
  },
  selected_run: {
    run_id: "run-1",
    state: "running",
    started_at: 1,
    finished_at: null,
    last_event_at: 3,
    last_error: null,
    problem_count: 1,
    counts: {
      total: 100,
      processed: 68,
      completed: 68,
      failed: 0,
      skipped: 3,
      uploaded: 12,
      downloaded: 8,
      deleted: 0,
      conflicts: 1,
      delete_pending: 0,
      delete_failed: 0,
    },
    current_file: null,
  },
  recent_runs: [],
  recent_events: [],
  problems: [],
};

vi.mock("@tanstack/react-query", () => ({
  useQuery: () => ({
    data: diagnostics,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock("../hooks/useTasks", () => ({
  useTasks: () => ({
    tasks: [task],
    statusMap: { "task-1": status },
    taskLoading: false,
    refreshTasks: vi.fn(),
    refreshStatus: vi.fn(),
    runTask: vi.fn(),
    toggleTask: vi.fn(),
    deleteTask: vi.fn(),
    resetLinks: vi.fn(),
    resettingLinks: false,
  }),
}));

vi.mock("../hooks/useConflicts", () => ({
  useConflicts: () => ({
    conflicts: [
      {
        id: "conflict-1",
        local_path: "D:/Knowledge/FeishuMirror/ProjectDocs/a.md",
        resolved: false,
      },
    ],
  }),
}));

vi.mock("../components/ui/toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

vi.mock("../components/ui/confirm-dialog", () => ({
  confirm: vi.fn(),
}));

describe("TaskDetailPage smoke", () => {
  it("renders v3 task detail layout with a fixed inspector rail", () => {
    const html = renderToStaticMarkup(<TaskDetailPage taskId="task-1" onBack={vi.fn()} />);

    expect(html).toContain("任务详情");
    expect(html).toContain("当前运行");
    expect(html).toContain("运行历史");
    expect(html).toContain("问题摘要");
    expect(html).toContain("任务操作");
    expect(html).toContain("策略摘要");
    expect(html).toContain("危险操作");
    expect(html).toContain("grid-cols-[minmax(0,1fr)_300px]");
    expect(html).toContain("grid-cols-[minmax(0,1fr)_112px_minmax(0,1fr)]");
    expect(html).toContain("w-[300px]");
    expect(html).toContain("grid-cols-4");
    expect(html).not.toContain("min-[1920px]");
    expect(html).not.toContain("min-[1760px]:grid-cols-4");
    expect(html).not.toContain("min-[1760px]:grid-cols-[minmax(0,1fr)_300px]");
    expect(html).not.toContain("min-[1760px]:grid-cols-[minmax(0,1fr)_112px_minmax(0,1fr)]");
    expect(html).not.toContain("min-[1600px]:grid-cols-[minmax(0,1fr)_300px]");
    expect(html).not.toContain("min-[1500px]:grid-cols-4");
    expect(html).not.toContain("min-[1440px]:grid-cols-[minmax(0,1fr)_300px]");
    expect(html).not.toContain("min-[1440px]:grid-cols-[minmax(0,1fr)_112px_minmax(0,1fr)]");
    expect(html).not.toContain("min-[1180px]:grid-cols-[minmax(760px,1fr)_300px]");
    expect(html).not.toContain("lg:flex");
  });
});
