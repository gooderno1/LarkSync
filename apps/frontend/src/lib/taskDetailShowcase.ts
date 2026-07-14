import type {
  SyncLogEntry,
  SyncTask,
  SyncTaskDiagnosticCounts,
  SyncTaskDiagnostics,
  SyncTaskRunSummary,
  SyncTaskStatus,
} from "../types";

export type TaskDetailShowcaseStats = {
  localFiles: string;
  cloudFiles: string;
  elapsed: string;
  remaining: string;
  speed: string;
  runSizes: Record<string, string>;
};

const timestamp = (day: number, hour: number, minute: number, second = 0) =>
  Date.UTC(2025, 4, day, hour - 8, minute, second) / 1000;

function counts(overrides: Partial<SyncTaskDiagnosticCounts> = {}): SyncTaskDiagnosticCounts {
  return {
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
    ...overrides,
  };
}

function run(
  runId: string,
  state: SyncTaskRunSummary["state"],
  startedAt: number,
  finishedAt: number | null,
  uploaded: number,
  downloaded: number,
  skipped: number,
  problemCount = 0,
): SyncTaskRunSummary {
  const processed = uploaded + downloaded + skipped;
  return {
    run_id: runId,
    state,
    started_at: startedAt,
    finished_at: finishedAt,
    last_event_at: finishedAt ?? timestamp(12, 10, 23, 48),
    last_error: state === "failed" ? "同步过程中发生错误" : null,
    problem_count: problemCount,
    counts: counts({
      total: processed,
      processed,
      completed: uploaded + downloaded,
      skipped,
      uploaded,
      downloaded,
      conflicts: state === "cancelled" ? 1 : 0,
    }),
    current_file: null,
  };
}

const primaryRuns: SyncTaskRunSummary[] = [
  run("run_20250512_102214_fa3c", "running", timestamp(12, 10, 22, 14), null, 128, 86, 43),
  run("run_20250512_094510_d2b1", "success", timestamp(12, 9, 45, 10), timestamp(12, 9, 48, 31), 201, 152, 0),
  run("run_20250512_083022_7a91", "success", timestamp(12, 8, 30, 22), timestamp(12, 8, 32, 40), 97, 88, 0),
  run("run_20250511_231508_c6e7", "cancelled", timestamp(11, 23, 15, 8), timestamp(11, 23, 19, 10), 312, 289, 0, 1),
  run("run_20250511_200533_8d54", "success", timestamp(11, 20, 5, 33), timestamp(11, 20, 7, 44), 61, 44, 0),
];

export const TASK_DETAIL_SHOWCASE_STATS: TaskDetailShowcaseStats = {
  localFiles: "12,458（256.3 MB）",
  cloudFiles: "12,102（238.7 MB）",
  elapsed: "00:01:34",
  remaining: "00:00:47",
  speed: "12.4 MB/s",
  runSizes: {
    run_20250512_102214_fa3c: "164.0 MB",
    run_20250512_094510_d2b1: "312.5 MB",
    run_20250512_083022_7a91: "145.6 MB",
    run_20250511_231508_c6e7: "428.9 MB",
    run_20250511_200533_8d54: "78.3 MB",
  },
};

export function buildTaskDetailShowcase(
  task: SyncTask,
  sourceStatus: SyncTaskStatus | undefined,
): { status: SyncTaskStatus; diagnostics: SyncTaskDiagnostics; stats: TaskDetailShowcaseStats } {
  const isPrimary = task.id === "task_001";
  const baseStatus: SyncTaskStatus = sourceStatus ?? {
    task_id: task.id,
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
  };
  const status: SyncTaskStatus = isPrimary
    ? {
        ...baseStatus,
        state: "running",
        started_at: timestamp(12, 10, 22, 14),
        finished_at: null,
        total_files: 256,
        completed_files: 131,
        failed_files: 0,
        skipped_files: 43,
        uploaded_files: 128,
        downloaded_files: 86,
        conflict_files: 1,
        current_run_id: primaryRuns[0].run_id,
      }
    : baseStatus;
  const recentRuns = isPrimary
    ? primaryRuns
    : [
        run(
          `run_${task.id}_latest`,
          status.state === "running" ? "running" : status.state === "failed" ? "failed" : "success",
          status.started_at ?? task.last_run_at ?? task.updated_at,
          status.finished_at ?? null,
          status.uploaded_files,
          status.downloaded_files,
          status.skipped_files,
          status.failed_files + status.conflict_files,
        ),
      ];
  const problem: SyncLogEntry = {
    taskId: task.id,
    taskName: task.name || task.local_path,
    timestamp: timestamp(12, 10, 24),
    status: "conflict",
    path: `${task.local_path}/需求说明.md`,
    message: "本地与云端均有修改，等待处理。",
    runId: recentRuns[0]?.run_id ?? null,
  };
  const selectedRun = recentRuns[0] ?? null;
  const diagnosticCounts = counts({
    total: status.total_files,
    processed: Math.min(status.total_files, status.completed_files + status.failed_files + status.skipped_files),
    completed: status.completed_files,
    failed: status.failed_files,
    skipped: status.skipped_files,
    uploaded: status.uploaded_files,
    downloaded: status.downloaded_files,
    deleted: status.deleted_files,
    conflicts: status.conflict_files,
    delete_pending: status.delete_pending_files,
    delete_failed: status.delete_failed_files,
  });

  return {
    status,
    diagnostics: {
      overview: {
        task,
        status,
        last_event_at: selectedRun?.last_event_at ?? task.last_run_at,
        last_result: status.state,
        problem_count: status.failed_files + status.conflict_files,
        counts: diagnosticCounts,
        current_file: null,
      },
      selected_run: selectedRun,
      recent_runs: recentRuns,
      recent_events: isPrimary ? [problem] : [],
      problems: isPrimary ? [problem] : [],
    },
    stats: isPrimary
      ? TASK_DETAIL_SHOWCASE_STATS
      : {
          localFiles: `${status.total_files.toLocaleString("zh-CN")} 个文件`,
          cloudFiles: `${status.total_files.toLocaleString("zh-CN")} 个文件`,
          elapsed: "--",
          remaining: "--",
          speed: "--",
          runSizes: {},
        },
  };
}
