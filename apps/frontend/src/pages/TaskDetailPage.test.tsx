import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { getRunPanelHeading, TaskDetailPage } from "./TaskDetailPage";

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
    updateTaskSettings: vi.fn(),
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
  it("restores the original standalone detail hierarchy", () => {
    const html = renderToStaticMarkup(<TaskDetailPage taskId="task-1" onBack={vi.fn()} />);

    expect(html).toContain("项目文档同步");
    expect(html).toContain("同步任务");
    expect(html).toContain("任务详情");
    expect(html).toContain("当前运行");
    expect(html).toContain("运行历史");
    expect(html).toContain("问题摘要");
    expect(html).toContain("任务操作");
    expect(html).toContain("策略摘要");
    expect(html).toContain("忽略目录");
    expect(html).toContain("危险操作");
    expect(html).toContain("编辑策略");
    expect(html).toContain("打开目录");
    expect(html).toContain('data-task-detail-identity="true"');
    expect(html).toContain('data-task-detail-path-map="true"');
    expect(html).toContain('data-local-endpoint-icon="monitor"');
    expect(html).toContain('data-sync-endpoint-content="local"');
    expect(html).toContain('data-sync-endpoint-content="cloud"');
    expect((html.match(/w-\[300px\] max-w-full/g) || [])).toHaveLength(2);
    expect(html).toContain('data-sync-brand-mark="true"');
    expect(html).toContain('viewBox="0 0 214 97"');
    expect(html).toContain('href="/logo-horizontal.png"');
    expect(html).toContain('h-[50px] w-[110px]');
    expect(html).toContain('data-sync-visual-offset="-17"');
    expect(html).toContain('-translate-x-[17px]');
    expect((html.match(/data-sync-connector=/g) || [])).toHaveLength(2);
    expect((html.match(/data-sync-mode-label=/g) || [])).toHaveLength(1);
    expect((html.match(/data-sync-health=/g) || [])).toHaveLength(1);
    expect(html).not.toContain('src="/favicon.png"');
    expect(html).toContain('data-task-detail-current-run="true"');
    expect(html).toContain('data-task-detail-history="true"');
    expect(html).toContain('data-task-detail-inspector="true"');
    expect((html.match(/data-task-detail-inspector=/g) || [])).toHaveLength(1);
    expect((html.match(/data-task-detail-inspector-card=/g) || [])).toHaveLength(5);
    expect(html).toContain("overflow-y-auto");
    expect(html).toContain('data-task-detail-inspector-card="danger" class="shrink-0');
    expect(html).toContain('role="switch"');
    expect(html).toContain('aria-checked="true"');
    expect(html).toContain('data-run-metrics="true"');
    expect(html).toContain("grid-cols-[minmax(0,1fr)_300px]");
    expect(html).toContain("w-[300px]");
    expect(html).not.toContain("返回列表管理策略");
    expect(html).not.toContain("维护操作");
    expect(html).not.toContain("grid-cols-[minmax(0,1fr)_112px_minmax(0,1fr)]");
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

  it("renders the task-page showcase detail instead of a missing-task state", () => {
    const html = renderToStaticMarkup(<TaskDetailPage taskId="task_001" onBack={vi.fn()} showcase />);

    expect(html).toContain("项目文档同步");
    expect(html).toContain("68%");
    expect(html).toContain("12,458");
    expect(html).toContain("run_20250512_102214_fa3c");
    expect((html.match(/data-run-history-row=/g) || [])).toHaveLength(5);
    expect(html).not.toContain("未找到任务");
  });

  it("distinguishes an active run from the latest completed run", () => {
    expect(getRunPanelHeading("running", true)).toBe("当前运行");
    expect(getRunPanelHeading("success", true)).toBe("最近一次运行");
    expect(getRunPanelHeading("idle", false)).toBe("运行状态");
  });
});
