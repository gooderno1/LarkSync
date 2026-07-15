import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import {
  buildRealtimeMetrics,
  buildRecentRow,
  DashboardPage,
  formatDashboardRelativeTime,
  selectRunningTasks,
  selectDashboardRecentRows,
  shouldUseDashboardShowcase,
} from "./DashboardPage";

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
  it("renders the v3 dashboard workbench without crowded legacy layout classes", () => {
    const html = renderToStaticMarkup(<DashboardPage onNavigate={vi.fn()} />);

    expect(html).toContain("总体状态");
    expect(html).toContain("今日活动");
    expect(html).toContain("正在运行");
    expect(html).toContain("最近同步");
    expect(html).toContain("优先处理");
    expect(html).toContain("任务状态");
    expect(html).toContain("今日传输");
    expect(html).toContain("数据流入");
    expect(html).toContain("数据流出");
    expect(html).toContain('data-dashboard-running-state="idle"');
    expect(html).toContain('data-dashboard-recent-status="check"');
    expect(html).toContain('data-dashboard-attention-card="summary"');
    expect(html).toContain('data-dashboard-flow-direction="incoming"');
    expect(html).toContain('data-dashboard-flow-direction="outgoing"');
    expect(html).toContain('data-dashboard-realtime-state="empty"');
    expect(html).toContain("暂无传输事件");
    expect(html).not.toContain("-- ms");
    expect(html).toContain("grid-cols-4");
    expect(html).toContain("grid-cols-[minmax(0,1fr)_316px]");
    expect(html).toContain("w-[316px]");
    expect(html).toContain("dashboard-clarity");
    expect(html).toContain('data-dashboard-rail="aligned"');
    expect(html).toContain('data-dashboard-main-column="true"');
    expect(html).toContain('data-dashboard-summary="true"');
    expect(html).toContain('data-dashboard-panel="running"');
    expect(html).toContain('data-dashboard-panel="recent"');
    expect(html).toContain("h-[300px]");
    expect(html).toContain("min-h-0 flex-1");
    expect(html).toContain("grid-rows-[146px_300px_minmax(0,1fr)]");
    expect(html).toContain('data-dashboard-transfer="true"');
    expect(html).toContain("gap-5 pt-9");
    expect(html).toContain("min-h-0 min-w-0 flex-1 overflow-hidden");
    expect(html).toContain('data-dashboard-recent-row="true"');
    expect(html).not.toContain("快速操作");
    expect(html).not.toContain("任务启停");
    expect(html).not.toContain("实时连接");
    expect(html).not.toContain("连接延迟");
    expect(html).not.toContain("min-[1760px]:grid-cols-4");
    expect(html).not.toContain("min-[1760px]:grid-cols-[minmax(0,1fr)_300px]");
    expect(html).not.toContain("min-[1600px]:grid-cols-4");
    expect(html).not.toContain("min-[1600px]:grid-cols-[minmax(0,1fr)_300px]");
    expect(html).not.toContain("min-[1440px]:grid-cols-4");
    expect(html).not.toContain("min-[1440px]:grid-cols-[minmax(0,1fr)_300px]");
    expect(html).not.toContain("min-[1440px]:grid-cols-[minmax(0,1fr)_320px]");
    expect(html).not.toContain("min-[1180px]:grid-cols-4");
    expect(html).not.toContain("min-[1180px]:grid-cols-[minmax(0,1fr)_300px]");
    expect(html).not.toContain("[@media(max-height:760px)]");
    expect(html).not.toContain("min-[1760px]:h-[calc(100vh-2.5rem)]");
    expect(html).not.toContain("max-h-[560px]");
    expect(html).not.toContain("max-h-[390px]");
  });

  it("keeps the running panel truthful when every task is idle", () => {
    const html = renderToStaticMarkup(<DashboardPage onNavigate={vi.fn()} />);

    expect(html).toContain('data-dashboard-running-state="idle"');
    expect(html).toContain("当前没有正在运行的任务");
    expect(html).toContain("任务状态");
    expect(html).not.toContain("12.4 MB/s");
  });
});

describe("dashboard showcase boundary", () => {
  it("only enables design fixtures through an explicit development query", () => {
    expect(shouldUseDashboardShowcase("?ui-demo=dashboard", true)).toBe(true);
    expect(shouldUseDashboardShowcase("", true)).toBe(false);
    expect(shouldUseDashboardShowcase("?ui-demo=dashboard", false)).toBe(false);
  });

  it("uses all seven rows released by the removed status bar", () => {
    expect(selectDashboardRecentRows([], true)).toHaveLength(7);
  });
});

describe("selectRunningTasks", () => {
  it("ignores stale running status retained by a disabled task", () => {
    const tasks = [
      {
        id: "enabled-task",
        name: "启用任务",
        local_path: "D:/Docs/enabled",
        cloud_folder_token: "fld_enabled",
        cloud_folder_name: "启用任务",
        base_path: null,
        sync_mode: "download_only" as const,
        update_mode: "auto" as const,
        md_sync_mode: "enhanced" as const,
        ignored_subpaths: [],
        enabled: true,
        created_at: 1,
        updated_at: 1,
        last_run_at: null,
      },
      {
        id: "disabled-task",
        name: "停用任务",
        local_path: "D:/Docs/disabled",
        cloud_folder_token: "fld_disabled",
        cloud_folder_name: "停用任务",
        base_path: null,
        sync_mode: "download_only" as const,
        update_mode: "auto" as const,
        md_sync_mode: "enhanced" as const,
        ignored_subpaths: [],
        enabled: false,
        created_at: 1,
        updated_at: 1,
        last_run_at: null,
      },
    ];
    const status = {
      task_id: "disabled-task",
      state: "running" as const,
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
    };

    expect(selectRunningTasks(tasks, { "disabled-task": status })).toEqual([]);
  });
});

describe("buildRecentRow", () => {
  it("does not invent transfer volume or duration for an event log", () => {
    const row = buildRecentRow({
      taskId: "task-1",
      taskName: "任务A",
      timestamp: 10,
      status: "downloaded",
      path: "D:/Docs/a.md",
      message: null,
    });

    expect(row.path).toContain("a.md");
    expect(row.volumeLabel).toBe("—");
    expect(row.durationLabel).toBe("—");
  });
});

describe("formatDashboardRelativeTime", () => {
  it("uses relative language for recent successful activity", () => {
    expect(formatDashboardRelativeTime(1_000, 1_030)).toBe("刚刚");
    expect(formatDashboardRelativeTime(1_000, 1_180)).toBe("3 分钟前");
    expect(formatDashboardRelativeTime(1_000, 8_200)).toBe("2 小时前");
  });
});

describe("buildRealtimeMetrics", () => {
  it("derives stable placeholder realtime metrics from sync events", () => {
    const metrics = buildRealtimeMetrics([
        {
          taskId: "task-1",
          taskName: "任务A",
          timestamp: 10,
          status: "downloaded",
          path: "D:/Docs/a.md",
          message: null,
        },
        {
          taskId: "task-1",
          taskName: "任务A",
          timestamp: 20,
          status: "uploaded",
          path: "D:/Docs/b.md",
          message: null,
        },
        {
          taskId: "task-1",
          taskName: "任务A",
          timestamp: 30,
          status: "conflict",
          path: "D:/Docs/c.md",
          message: "冲突",
        },
      ]);

    expect(metrics.latencyMs).toBeNull();
    expect(metrics.incomingEvents).toBe(1);
    expect(metrics.outgoingEvents).toBe(1);
    expect(metrics.incomingSeries).toHaveLength(20);
    expect(metrics.outgoingSeries).toHaveLength(20);
    expect(Math.max(...metrics.incomingSeries)).toBeGreaterThanOrEqual(10);
    expect(Math.max(...metrics.outgoingSeries)).toBeGreaterThanOrEqual(10);
  });
});
