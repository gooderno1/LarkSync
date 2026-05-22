import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { LogCenterPage } from "./LogCenterPage";

const overviewItem = {
  task: {
    id: "task-1",
    name: "日志任务",
    local_path: "D:/Knowledge/Logs",
    cloud_folder_token: "fld_123",
    cloud_folder_name: "日志目录",
    sync_mode: "bidirectional",
    update_mode: "auto",
    md_sync_mode: "enhanced",
    enabled: true,
    created_at: 1,
    updated_at: 2,
    last_run_at: 3,
  },
  status: {
    task_id: "task-1",
    state: "idle",
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

const diagnostics = {
  overview: overviewItem,
  selected_run: {
    run_id: "run-1",
    state: "success",
    started_at: 1,
    finished_at: 3,
    last_event_at: 3,
    last_error: null,
    problem_count: 0,
    counts: overviewItem.counts,
    current_file: null,
  },
  recent_runs: [
    {
      run_id: "run-1",
      state: "success",
      started_at: 1,
      finished_at: 3,
      last_event_at: 3,
      last_error: null,
      problem_count: 0,
      counts: overviewItem.counts,
      current_file: null,
    },
  ],
  recent_events: [],
  problems: [],
};

vi.mock("@tanstack/react-query", () => ({
  useQuery: (options: {
    queryKey: unknown[];
    enabled?: boolean;
    placeholderData?: unknown;
  }) => {
    const [queryKey] = options.queryKey;
    const disabled = options.enabled === false;
    const empty = {
      data: typeof options.placeholderData === "function" ? undefined : options.placeholderData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
    if (disabled) return empty;
    if (queryKey === "sync-task-overview") {
      return { data: [overviewItem], isLoading: false, error: null, refetch: vi.fn() };
    }
    if (queryKey === "sync-task-diagnostics") {
      return { data: diagnostics, isLoading: false, error: null, refetch: vi.fn() };
    }
    if (queryKey === "sync-log-task-events") {
      return { data: { total: 0, items: [] }, isLoading: false, error: null, refetch: vi.fn() };
    }
    if (queryKey === "file-logs") {
      return { data: { total: 0, items: [] }, isLoading: false, error: null, refetch: vi.fn() };
    }
    return empty;
  },
}));

vi.mock("../hooks/useConflicts", () => ({
  useConflicts: () => ({
    conflicts: [],
    conflictLoading: false,
    conflictError: null,
    refreshConflicts: vi.fn(),
    resolveConflictAsync: vi.fn(),
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

describe("LogCenterPage smoke", () => {
  it("renders task diagnostics workspace shell", () => {
    const html = renderToStaticMarkup(<LogCenterPage />);

    expect(html).toContain("日志中心");
    expect(html).toContain("任务选择");
    expect(html).toContain("运行记录");
  });
});
