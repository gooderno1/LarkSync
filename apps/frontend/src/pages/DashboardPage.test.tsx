import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { DashboardPage } from "./DashboardPage";

vi.mock("@tanstack/react-query", () => ({
  useQuery: () => ({
    data: {
      total: 2,
      items: [
        {
          taskId: "task-1",
          taskName: "芯华 - 工作记录",
          timestamp: 1,
          status: "delete_failed",
          path: "D:/Docs/output-a",
          message: "删除文件失败: not found",
        },
        {
          taskId: "task-2",
          taskName: "算云项目更新",
          timestamp: 2,
          status: "delete_pending",
          path: "D:/Docs/output-b",
          message: "检测到本地已删除，待处理删除同步",
        },
      ],
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    connected: true,
  }),
}));

vi.mock("../hooks/useTasks", () => ({
  useTasks: () => ({
    tasks: [
      {
        id: "task-1",
        name: "芯华 - 工作记录",
        local_path: "D:/Docs/work",
        cloud_folder_token: "fld_1",
        cloud_folder_name: "芯华 - 工作记录",
        sync_mode: "bidirectional",
        update_mode: "auto",
        md_sync_mode: "enhanced",
        enabled: true,
        created_at: 1,
        updated_at: 2,
        last_run_at: 3,
      },
      {
        id: "task-2",
        name: "算云项目更新",
        local_path: "D:/Docs/cloud",
        cloud_folder_token: "fld_2",
        cloud_folder_name: "算云项目更新",
        sync_mode: "download_only",
        update_mode: "auto",
        md_sync_mode: "enhanced",
        enabled: true,
        created_at: 1,
        updated_at: 2,
        last_run_at: 4,
      },
    ],
    taskLoading: false,
    statusMap: {
      "task-1": {
        task_id: "task-1",
        state: "idle",
        total_files: 10,
        completed_files: 6,
        failed_files: 0,
        skipped_files: 0,
        uploaded_files: 0,
        downloaded_files: 0,
        deleted_files: 0,
        conflict_files: 0,
        delete_pending_files: 0,
        delete_failed_files: 1,
        last_files: [],
        started_at: 1,
        finished_at: 2,
      },
      "task-2": {
        task_id: "task-2",
        state: "idle",
        total_files: 8,
        completed_files: 8,
        failed_files: 0,
        skipped_files: 0,
        uploaded_files: 0,
        downloaded_files: 0,
        deleted_files: 0,
        conflict_files: 0,
        delete_pending_files: 1,
        delete_failed_files: 0,
        last_files: [],
        started_at: 2,
        finished_at: 3,
      },
    },
    refreshTasks: vi.fn(),
    refreshStatus: vi.fn(),
  }),
}));

vi.mock("../hooks/useConflicts", () => ({
  useConflicts: () => ({
    conflicts: [],
  }),
}));

vi.mock("../hooks/useWebSocketLog", () => ({
  useWebSocketLog: () => ({
    entries: [],
    status: "connected",
  }),
}));

describe("DashboardPage smoke", () => {
  it("renders dashboard panels with wide-screen workbench height classes", () => {
    const html = renderToStaticMarkup(<DashboardPage onNavigate={vi.fn()} />);

    expect(html).toContain("任务概览");
    expect(html).toContain("需要关注");
    expect(html).toContain("min-[1760px]:flex-1");
    expect(html).toContain("min-[1760px]:overflow-hidden");
    expect(html).toContain("min-[1760px]:items-stretch");
    expect(html).toContain("min-[1760px]:h-full");
    expect(html).not.toContain("min-[1760px]:h-[calc(100vh-2.5rem)]");
    expect(html).not.toContain("max-h-[560px]");
    expect(html).not.toContain("max-h-[390px]");
  });
});
