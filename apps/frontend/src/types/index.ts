/* ------------------------------------------------------------------ */
/*  LarkSync 前端共享类型                                              */
/* ------------------------------------------------------------------ */

export type ShortcutInfo = {
  target_token: string;
  target_type: string;
};

export type DriveNode = {
  token: string;
  name: string;
  type: string;
  parent_token?: string | null;
  url?: string | null;
  created_time?: string | null;
  modified_time?: string | null;
  owner_id?: string | null;
  shortcut_info?: ShortcutInfo | null;
  children?: DriveNode[];
};

export type ConflictItem = {
  id: string;
  local_path: string;
  cloud_token: string;
  local_hash: string;
  db_hash: string;
  cloud_version: number;
  db_version: number;
  local_preview?: string | null;
  cloud_preview?: string | null;
  created_at: number;
  resolved: boolean;
  resolved_action?: string | null;
};

export type SyncTask = {
  id: string;
  name?: string | null;
  local_path: string;
  cloud_folder_token: string;
  cloud_folder_name?: string | null;
  base_path?: string | null;
  sync_mode: string;
  update_mode?: string | null;
  md_sync_mode?: "enhanced" | "download_only" | "doc_only" | null;
  delete_policy?: "off" | "safe" | "strict" | null;
  delete_grace_minutes?: number | null;
  is_test?: boolean;
  enabled: boolean;
  created_at: number;
  updated_at: number;
  last_run_at?: number | null;
};

export type SyncFileEvent = {
  path: string;
  status: string;
  message?: string | null;
  timestamp?: number | null;
};

export type SyncTaskStatus = {
  task_id: string;
  state: "idle" | "running" | "success" | "failed" | "cancelled";
  started_at?: number | null;
  finished_at?: number | null;
  total_files: number;
  completed_files: number;
  failed_files: number;
  skipped_files: number;
  last_error?: string | null;
  current_run_id?: string | null;
  last_files: SyncFileEvent[];
};

export type SyncTaskDiagnosticCounts = {
  total: number;
  processed: number;
  completed: number;
  failed: number;
  skipped: number;
  uploaded: number;
  downloaded: number;
  deleted: number;
  conflicts: number;
  delete_pending: number;
  delete_failed: number;
};

export type SyncTaskOverview = {
  task: SyncTask;
  status: SyncTaskStatus;
  last_event_at?: number | null;
  last_result?: string | null;
  problem_count: number;
  counts: SyncTaskDiagnosticCounts;
  current_file?: SyncFileEvent | null;
};

export type SyncTaskDiagnostics = {
  overview: SyncTaskOverview;
  recent_events: SyncLogEntry[];
  problems: SyncLogEntry[];
};

export type CloudSelection = {
  token: string;
  name: string;
  path: string;
};

export type NavKey = "dashboard" | "tasks" | "logcenter" | "settings";

export type Tone = "neutral" | "info" | "success" | "warning" | "danger";

export type SyncLogEntry = {
  taskId: string;
  taskName: string;
  timestamp: number;
  status: string;
  path: string;
  message?: string | null;
  runId?: string | null;
};
