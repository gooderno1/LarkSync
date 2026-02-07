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
  enabled: boolean;
  created_at: number;
  updated_at: number;
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
  last_files: SyncFileEvent[];
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
};
