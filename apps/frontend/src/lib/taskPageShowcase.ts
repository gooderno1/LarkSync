import type { SyncTask, SyncTaskStatus } from "../types";

export type TaskPageShowcaseCounts = {
  queued: number;
  deleteTotal: number;
  failed: number;
  conflict: number;
};

const timestamp = (hour: number, minute: number, second = 0) =>
  Date.UTC(2025, 4, 12, hour - 8, minute, second) / 1000;

const task = (
  id: string,
  name: string,
  localPath: string,
  cloudName: string,
  syncMode: "bidirectional" | "upload_only" | "download_only",
  enabled = true,
): SyncTask => ({
  id,
  name,
  local_path: localPath,
  cloud_folder_token: `folder_${id}`,
  cloud_folder_name: cloudName,
  base_path: null,
  sync_mode: syncMode,
  update_mode: "auto",
  md_sync_mode: syncMode === "download_only" ? "download_only" : "enhanced",
  ignored_subpaths: [],
  delete_policy: "safe",
  delete_grace_minutes: 1440,
  enabled,
  created_at: timestamp(8, 0),
  updated_at: timestamp(10, 30),
  last_run_at: enabled ? timestamp(10, 0) : null,
});

const status = (
  taskId: string,
  state: SyncTaskStatus["state"],
  totalFiles: number,
  completedFiles: number,
  finishedAt: number | null,
  failedFiles = 0,
  conflictFiles = 0,
): SyncTaskStatus => ({
  task_id: taskId,
  state,
  started_at: state === "running" ? timestamp(10, 18) : timestamp(9, 58),
  finished_at: finishedAt,
  total_files: totalFiles,
  completed_files: completedFiles,
  failed_files: failedFiles,
  skipped_files: 0,
  uploaded_files: Math.floor(completedFiles / 2),
  downloaded_files: completedFiles - Math.floor(completedFiles / 2),
  deleted_files: 0,
  conflict_files: conflictFiles,
  delete_pending_files: 0,
  delete_failed_files: 0,
  last_error: state === "failed" ? "目标文件被占用，写入重试已达到上限。" : null,
  current_run_id: state === "running" ? `run_${taskId}` : null,
  last_files: [],
});

export const TASK_PAGE_SHOWCASE_TASKS: SyncTask[] = [
  task("task_001", "项目文档同步", "D:/Knowledge/FeishuMirror/ProjectDocs", "我的空间 / 项目文档", "bidirectional"),
  task("task_002", "设计资源库", "D:/Design/Resources", "我的空间 / 设计资源", "upload_only"),
  task("task_003", "固定资料库", "D:/Company/PublicInfo", "共享空间 / 固定资料", "bidirectional"),
  task("task_004", "个人笔记同步", "D:/Notes/MyNotes", "我的空间 / 个人笔记", "bidirectional"),
  task("task_005", "会议记录归档", "D:/Meetings/Archive", "共享空间 / 会议记录", "upload_only"),
  task("task_006", "市场资料备份", "D:/Market/Backup", "共享空间 / 市场资料", "bidirectional"),
  task("task_007", "产品手册同步", "D:/Product/Manuals", "我的空间 / 产品手册", "upload_only"),
  task("task_008", "历史资料只读", "D:/Archive/History", "共享空间 / 历史资料", "download_only", false),
];

export const TASK_PAGE_SHOWCASE_STATUS: Record<string, SyncTaskStatus> = {
  task_001: { ...status("task_001", "running", 256, 128, null), started_at: timestamp(10, 22, 14) },
  task_002: { ...status("task_002", "running", 172, 86, null), started_at: timestamp(10, 20, 48) },
  task_003: { ...status("task_003", "running", 513, 512, null, 0, 1), started_at: timestamp(10, 18, 32) },
  task_004: status("task_004", "idle", 0, 0, timestamp(10, 15, 11)),
  task_005: { ...status("task_005", "running", 403, 201, null, 0, 2), started_at: timestamp(10, 12, 3) },
  task_006: status("task_006", "failed", 3, 0, timestamp(10, 8, 47), 3),
  task_007: { ...status("task_007", "running", 148, 74, null), started_at: timestamp(10, 5, 36) },
  task_008: status("task_008", "idle", 0, 0, null),
};

export const TASK_PAGE_SHOWCASE_DURATIONS: Record<string, string> = {
  task_001: "00:01:34",
  task_002: "00:00:55",
  task_003: "00:03:21",
  task_004: "--",
  task_005: "00:01:58",
  task_006: "00:00:12",
  task_007: "00:02:33",
  task_008: "--",
};

export const TASK_PAGE_SHOWCASE_COUNTS: Record<string, TaskPageShowcaseCounts> = {
  task_001: { queued: 128, deleteTotal: 2, failed: 0, conflict: 0 },
  task_002: { queued: 86, deleteTotal: 0, failed: 0, conflict: 0 },
  task_003: { queued: 512, deleteTotal: 1, failed: 0, conflict: 1 },
  task_004: { queued: 0, deleteTotal: 0, failed: 0, conflict: 0 },
  task_005: { queued: 201, deleteTotal: 0, failed: 0, conflict: 2 },
  task_006: { queued: 0, deleteTotal: 0, failed: 3, conflict: 0 },
  task_007: { queued: 74, deleteTotal: 0, failed: 0, conflict: 0 },
  task_008: { queued: 0, deleteTotal: 0, failed: 0, conflict: 0 },
};

export function shouldUseTaskPageShowcase(search: string, isDevelopment: boolean): boolean {
  if (!isDevelopment) return false;
  return new URLSearchParams(search).get("ui-data") !== "live";
}

export function useTaskPageShowcase(): boolean {
  const search = typeof window === "undefined" ? "?ui-data=live" : window.location.search;
  return shouldUseTaskPageShowcase(search, import.meta.env.DEV);
}
