import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { TaskSelectionPanel } from "./TaskSelectionPanel";
import { RunHistoryPanel } from "./RunHistoryPanel";
import { TaskDiagnosticsDetailPanel } from "./TaskDiagnosticsDetailPanel";
import type {
  SyncLogEntry,
  SyncTask,
  SyncTaskDiagnosticCounts,
  SyncTaskRunSummary,
  SyncTaskStatus,
  SyncTaskOverview,
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

const overview: SyncTaskOverview = {
  task,
  status,
  last_event_at: 4,
  last_result: "success",
  problem_count: 1,
  counts,
  current_file: {
    path: "D:/Knowledge/Base/README.md",
    status: "running",
    message: "正在上传",
    timestamp: 4,
  },
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
  current_file: overview.current_file,
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

vi.mock("../ui/toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

describe("log center task panels", () => {
  it("renders task selection and current task metadata", () => {
    const html = renderToStaticMarkup(
      <TaskSelectionPanel
        taskPickerRef={{ current: null }}
        selectedTask={task}
        selectedTaskId={task.id}
        selectedStatus={status}
        selectedStateKey="running"
        lastActivityAt={4}
        overviewQueryIsFetching={false}
        diagnosticsQueryIsFetching={false}
        taskPickerOpen={false}
        setTaskPickerOpen={vi.fn()}
        showAllTasks={false}
        setShowAllTasks={vi.fn()}
        hiddenTaskCount={0}
        focusedTaskCount={1}
        taskPickerQuery=""
        setTaskPickerQuery={vi.fn()}
        taskPickerOptions={[overview]}
        selectTask={vi.fn()}
        refreshDiagnostics={vi.fn()}
      />,
    );

    expect(html).toContain("任务选择");
    expect(html).toContain("当前任务信息");
    expect(html).toContain("知识库同步");
  });

  it("renders run history items and detail overview", () => {
    const html = renderToStaticMarkup(
      <>
        <RunHistoryPanel
          selectedTask={task}
          diagnosticsQueryIsLoading={false}
          recentRuns={[selectedRun]}
          activeRunId="run-1"
          setSelectedRunId={vi.fn()}
          resetEventPage={vi.fn()}
        />
        <TaskDiagnosticsDetailPanel
          selectedTask={task}
          selectedRun={selectedRun}
          selectedStatus={status}
          selectedStateKey="running"
          lastActivityAt={4}
          activeRunId="run-1"
          detailTab="overview"
          setDetailTab={vi.fn()}
          diagnosticsQueryIsFetching={false}
          refreshDiagnostics={vi.fn()}
          progress={{ progress: 60, effectiveTotal: 10, processed: 6, completed: 6, failed: 1, skipped: 1, total: 10 }}
          diagnosticCounts={counts}
          currentFile={overview.current_file ?? null}
          runAlert={null}
          selectedProblems={selectedProblems}
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
        />
      </>,
    );

    expect(html).toContain("运行记录");
    expect(html).toContain("同步目标");
    expect(html).toContain("知识库");
  });
});
