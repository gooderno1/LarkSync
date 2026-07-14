import type { SyncTask } from "../types";
import { syncModeSupportsUpload } from "./constants";
import { parseDeleteGraceMinutes } from "./taskManagement";

export type TaskSettingsDraft = {
  syncMode: string;
  updateMode: string;
  mdSyncMode: "enhanced" | "download_only" | "doc_only";
  deletePolicy: "off" | "safe" | "strict";
  deleteGraceMinutes: string;
};

export type TaskSettingsRisk = {
  label: "低风险" | "中风险" | "高风险";
  tone: "safe" | "warning" | "danger";
  description: string;
};

export function createTaskSettingsDraft(task: SyncTask): TaskSettingsDraft {
  return {
    syncMode: task.sync_mode,
    updateMode: task.update_mode || "auto",
    mdSyncMode: (task.md_sync_mode || "enhanced") as TaskSettingsDraft["mdSyncMode"],
    deletePolicy: (task.delete_policy || "safe") as TaskSettingsDraft["deletePolicy"],
    deleteGraceMinutes: String(task.delete_grace_minutes ?? 30),
  };
}

function persistedDeleteGrace(task: SyncTask): number {
  return parseDeleteGraceMinutes(
    (task.delete_policy || "safe") as TaskSettingsDraft["deletePolicy"],
    String(task.delete_grace_minutes ?? 30),
    30,
  );
}

export function countTaskSettingsChanges(task: SyncTask, draft: TaskSettingsDraft): number {
  return countTaskSettingsDraftChanges(createTaskSettingsDraft(task), draft);
}

export function countTaskSettingsDraftChanges(
  baseline: TaskSettingsDraft,
  draft: TaskSettingsDraft,
): number {
  let changes = 0;
  if (draft.syncMode !== baseline.syncMode) changes += 1;
  if (draft.updateMode !== baseline.updateMode) changes += 1;
  if (draft.mdSyncMode !== baseline.mdSyncMode) changes += 1;
  const draftGrace = parseDeleteGraceMinutes(draft.deletePolicy, draft.deleteGraceMinutes, 30);
  const baselineGrace = parseDeleteGraceMinutes(
    baseline.deletePolicy,
    baseline.deleteGraceMinutes,
    30,
  );
  if (draft.deletePolicy !== baseline.deletePolicy || draftGrace !== baselineGrace) {
    changes += 1;
  }
  return changes;
}

export function buildTaskSettingsPatch(
  task: SyncTask,
  draft: TaskSettingsDraft,
): Record<string, unknown> {
  const patch: Record<string, unknown> = {};
  if (draft.syncMode !== task.sync_mode) patch.sync_mode = draft.syncMode;
  if (draft.updateMode !== (task.update_mode || "auto")) patch.update_mode = draft.updateMode;
  if (draft.mdSyncMode !== (task.md_sync_mode || "enhanced")) patch.md_sync_mode = draft.mdSyncMode;

  const draftGrace = parseDeleteGraceMinutes(draft.deletePolicy, draft.deleteGraceMinutes, 30);
  if (draft.deletePolicy !== (task.delete_policy || "safe") || draftGrace !== persistedDeleteGrace(task)) {
    patch.delete_policy = draft.deletePolicy;
    patch.delete_grace_minutes = draftGrace;
  }
  return patch;
}

export function getTaskSettingsRisk(
  syncMode: string,
  deletePolicy: TaskSettingsDraft["deletePolicy"],
): TaskSettingsRisk {
  if (deletePolicy === "strict") {
    return {
      label: "高风险",
      tone: "danger",
      description: "删除会立即联动执行，请先确认本地与云端目录范围。",
    };
  }
  if (syncModeSupportsUpload(syncMode)) {
    return {
      label: "中风险",
      tone: "warning",
      description: "该模式可以写入云端，修改前请确认内容流向。",
    };
  }
  return {
    label: "低风险",
    tone: "safe",
    description: "仅下载不会把本地改动写入云端。",
  };
}
