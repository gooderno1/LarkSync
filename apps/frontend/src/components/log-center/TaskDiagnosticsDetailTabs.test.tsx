import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { TaskDiagnosticsOverviewTab } from "./TaskDiagnosticsOverviewTab";
import { TaskDiagnosticsProblemsTab } from "./TaskDiagnosticsProblemsTab";
import { TaskDiagnosticsEventsTab } from "./TaskDiagnosticsEventsTab";
import type {
  SyncLogEntry,
  SyncTask,
  SyncTaskDiagnosticCounts,
  SyncTaskRunSummary,
  SyncTaskStatus,
} from "../../types";

const task: SyncTask = {
  id: "task-1",
  name: "知识库同步",
  local_path: "D:/Knowledge/Base",
  cloud_folder_token: "fld_123",
  cloud_folder_name: "知识库",
  sync_mode: "bidirectional",
  update_mode: "auto",
  md_sync_mode: "enhanced",
  enabled: true,
  created_at: 1,
  updated_at: 2,
  last_run_at: 3,
};

const status: SyncTaskStatus = {
  task_id: "task-1",
  state: "running",
  started_at: 1,
  finished_at: null,
  total_files: 10,
  completed_files: 6,
  failed_files: 1,
  skipped_files: 1,
  uploaded_files: 2,
  downloaded_files: 2,
  deleted_files: 0,
  conflict_files: 0,
  delete_pending_files: 0,
  delete_failed_files: 0,
  current_run_id: "run-1",
  last_error: null,
  last_files: [],
};

const counts: SyncTaskDiagnosticCounts = {
  total: 10,
  processed: 6,
  completed: 6,
  failed: 1,
  skipped: 1,
  uploaded: 2,
  downloaded: 2,
  deleted: 0,
  conflicts: 1,
  delete_pending: 0,
  delete_failed: 0,
};

const selectedRun: SyncTaskRunSummary = {
  run_id: "run-1",
  state: "running",
  started_at: 1,
  finished_at: null,
  last_event_at: 4,
  last_error: null,
  problem_count: 1,
  counts,
  current_file: {
    path: "D:/Knowledge/Base/README.md",
    status: "running",
    message: "正在上传",
    timestamp: 4,
  },
};

const selectedProblems: SyncLogEntry[] = [
  {
    taskId: "task-1",
    taskName: "知识库同步",
    timestamp: 4,
    status: "failed",
    path: "D:/Knowledge/Base/README.md",
    message: "上传失败",
    runId: "run-1",
  },
];

const selectedTimelineEntries: SyncLogEntry[] = [
  {
    taskId: "task-1",
    taskName: "知识库同步",
    timestamp: 4,
    status: "uploaded",
    path: "D:/Knowledge/Base/README.md",
    message: "上传完成",
    runId: "run-1",
  },
];

describe("task diagnostics detail tabs", () => {
  it("renders overview tab content", () => {
    const html = renderToStaticMarkup(
      <TaskDiagnosticsOverviewTab
        selectedTask={task}
        selectedRun={selectedRun}
        selectedStatus={status}
        lastActivityAt={4}
        progress={{ progress: 60, effectiveTotal: 10, processed: 6, completed: 6, failed: 1, skipped: 1, total: 10 }}
        diagnosticCounts={counts}
        currentFile={selectedRun.current_file ?? null}
        runAlert={null}
      />,
    );

    expect(html).toContain("同步目标");
    expect(html).toContain("当前处理");
    expect(html).toContain("知识库");
  });

  it("renders problems tab content", () => {
    const html = renderToStaticMarkup(
      <TaskDiagnosticsProblemsTab selectedProblems={selectedProblems} />,
    );

    expect(html).toContain("上传失败");
    expect(html).toContain("1 条");
  });

  it("renders events tab content and pagination shell", () => {
    const html = renderToStaticMarkup(
      <TaskDiagnosticsEventsTab
        eventFilter="all"
        setEventFilter={vi.fn()}
        eventSearch=""
        setEventSearch={vi.fn()}
        resetEventPage={vi.fn()}
        selectedEventsQueryIsLoading={false}
        selectedTimelineEntries={selectedTimelineEntries}
        selectedTimelineTotal={1}
        eventPage={1}
        setEventPage={vi.fn()}
        eventPageSize={30}
        setEventPageSize={vi.fn()}
      />,
    );

    expect(html).toContain("全部事件");
    expect(html).toContain("上传完成");
    expect(html).toContain("共");
  });
});
