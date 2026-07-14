import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TasksPage } from "./TasksPage";
import type { SyncTask, SyncTaskStatus } from "../types";

const taskMockState = vi.hoisted(() => ({
  tasks: [] as SyncTask[],
  statusMap: {} as Record<string, SyncTaskStatus>,
}));

vi.mock("../hooks/useTasks", () => ({
  useTasks: () => ({
    tasks: taskMockState.tasks,
    taskLoading: false,
    taskError: null,
    statusMap: taskMockState.statusMap,
    refreshTasks: vi.fn(),
    toggleTask: vi.fn(),
    updateTaskSettings: vi.fn(),
    runTask: vi.fn(),
    deleteTask: vi.fn(),
  }),
}));

vi.mock("../hooks/useConflicts", () => ({
  useConflicts: () => ({
    conflicts: [],
  }),
}));

vi.mock("../components/ui/toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

vi.mock("../components/ThemeToggle", () => ({
  ThemeToggle: () => <div>Theme Toggle</div>,
}));

vi.mock("../components/NewTaskModal", () => ({
  NewTaskModal: () => null,
}));

describe("TasksPage smoke", () => {
  beforeEach(() => {
    taskMockState.tasks = [];
    taskMockState.statusMap = {};
  });

  it("renders task management shell and empty state", () => {
    const html = renderToStaticMarkup(<TasksPage />);

    expect(html).toContain("同步任务");
    expect(html).toContain("搜索任务");
    expect(html).toContain("全部状态");
    expect(html).toContain("全部模式");
    expect(html).toContain("全部健康");
    expect(html).toContain("暂无同步任务");
    expect(html).toContain("border-[#c9d8ec]");
    expect(html).not.toContain("bg-zinc-900/60");
    expect(html).not.toContain("border-zinc-800");
  });

  it("renders tasks in the dense desktop table layout", () => {
    taskMockState.tasks = [
      {
        id: "task-desktop-main",
        name: "知识库同步",
        local_path: "D:/Workspace/LarkSync/Knowledge",
        cloud_folder_token: "fld_token_knowledge",
        cloud_folder_name: "飞书知识库",
        base_path: null,
        sync_mode: "bidirectional",
        update_mode: "auto",
        md_sync_mode: "enhanced",
        delete_policy: "safe",
        delete_grace_minutes: 30,
        enabled: true,
        created_at: 1710000000,
        updated_at: 1710000000,
        last_run_at: 1710001000,
      },
    ];
    taskMockState.statusMap = {
      "task-desktop-main": {
        task_id: "task-desktop-main",
        state: "running",
        started_at: 1710001200,
        finished_at: null,
        total_files: 10,
        completed_files: 4,
        failed_files: 1,
        skipped_files: 0,
        uploaded_files: 2,
        downloaded_files: 2,
        deleted_files: 0,
        conflict_files: 0,
        delete_pending_files: 1,
        delete_failed_files: 0,
        last_error: null,
        current_run_id: "run-1",
        last_files: [
          { path: "pending.md", status: "queued" },
          { path: "failed.md", status: "failed" },
        ],
      },
    };

    const html = renderToStaticMarkup(<TasksPage onOpenTaskDetail={vi.fn()} />);

    expect(html).toContain("<table");
    expect(html).toContain("min-w-[1120px]");
    expect(html).toContain("tasks-clarity");
    expect(html).toContain("space-y-4");
    expect(html).toContain("px-4 py-3");
    expect(html).not.toContain("min-[1320px]:min-w-[1180px]");
    expect(html).not.toContain("min-[1320px]:table-cell");
    expect(html).toContain("任务名称");
    expect(html).toContain("本地目录");
    expect(html).toContain("云端目录");
    expect(html).toContain("状态 / 健康");
    expect(html).toContain("知识库同步");
    expect(html).toContain("双向同步");
    expect(html).toContain("同步中");
    expect(html).toContain('aria-label="查看任务详情"');
    expect(html).toContain('role="switch"');
    expect(html).toContain('aria-checked="true"');
    expect(html).toContain("展开任务设置");
    expect(html).toContain("whitespace-nowrap");
    expect(html).not.toContain("展开策略");
    expect(html).not.toContain("任务卡片");

    const tableEnd = html.indexOf("</table>");
    const footer = html.indexOf('data-task-table-footer="true"');
    expect(tableEnd).toBeGreaterThan(-1);
    expect(footer).toBeGreaterThan(tableEnd);
  });

  it("uses truthful empty recent-run copy and avoids duplicate paused health labels", () => {
    taskMockState.tasks = [
      {
        id: "task-never-run",
        name: "尚未运行任务",
        local_path: "D:/Workspace/LarkSync/New",
        cloud_folder_token: "fld_token_new",
        cloud_folder_name: "新建目录",
        base_path: null,
        sync_mode: "download_only",
        update_mode: "auto",
        md_sync_mode: "download_only",
        delete_policy: "safe",
        delete_grace_minutes: 30,
        enabled: false,
        created_at: 1710000000,
        updated_at: 1710000000,
        last_run_at: null,
      },
    ];

    const html = renderToStaticMarkup(<TasksPage onOpenTaskDetail={vi.fn()} />);

    expect(html).toContain("尚未运行");
    expect(html).not.toContain(">自动<");
    expect(html.match(/已停用/g)).toHaveLength(2);
    expect(html).toContain('aria-checked="false"');
  });
});
