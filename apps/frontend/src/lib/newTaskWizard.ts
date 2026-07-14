import type { CloudSelection } from "../types";

export type NewTaskPayloadInput = {
  taskName: string;
  taskLocalPath: string;
  taskCloudToken: string;
  selectedCloud: CloudSelection | null;
  taskBasePath: string;
  taskSyncMode: string;
  taskUpdateMode: string;
  taskMdSyncMode: "enhanced" | "download_only" | "doc_only";
  taskUploadEnabled: boolean;
  taskDeletePolicy: "off" | "safe" | "strict";
  taskDeleteGraceMinutes: string;
  taskEnabled: boolean;
};

export type NewTaskRiskLevel = {
  label: "低风险" | "中风险" | "高风险";
  tone: "safe" | "warning" | "danger";
};

export function getWizardMaxAccessibleStep(localPath: string, cloudToken: string): number {
  if (!localPath.trim()) return 1;
  if (!cloudToken.trim()) return 2;
  return 5;
}

export function getNewTaskRiskLevel(
  syncMode: string,
  deletePolicy: "off" | "safe" | "strict",
): NewTaskRiskLevel {
  if (deletePolicy === "strict") return { label: "高风险", tone: "danger" };
  if (syncMode !== "download_only") return { label: "中风险", tone: "warning" };
  return { label: "低风险", tone: "safe" };
}

export function extractCloudFolderToken(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const urlMatch = trimmed.match(/folder\/([A-Za-z0-9_-]+)(?:[/?#]|$)/);
  if (urlMatch) return urlMatch[1];
  if (/^[A-Za-z0-9_-]+$/.test(trimmed)) return trimmed;
  return null;
}

export function resolveManualCloudSelection(
  input: string,
  displayName: string
): { selection: CloudSelection | null; error: string | null } {
  const token = extractCloudFolderToken(input);
  if (!token) {
    return {
      selection: null,
      error: "未识别到有效的共享链接或 Token。",
    };
  }
  const label = displayName.trim() || token;
  return {
    selection: {
      token,
      name: label,
      path: label,
    },
    error: null,
  };
}

export function buildCreateTaskPayload(input: NewTaskPayloadInput): Record<string, unknown> {
  return {
    name: input.taskName.trim() || null,
    local_path: input.taskLocalPath.trim(),
    cloud_folder_token: input.taskCloudToken.trim(),
    cloud_folder_name: input.selectedCloud?.path || null,
    base_path: input.taskBasePath.trim() || null,
    sync_mode: input.taskSyncMode,
    update_mode: input.taskUpdateMode,
    md_sync_mode: input.taskUploadEnabled ? input.taskMdSyncMode : "download_only",
    delete_policy: input.taskDeletePolicy,
    delete_grace_minutes:
      input.taskDeletePolicy === "strict"
        ? 0
        : Math.max(0, Number.parseInt(input.taskDeleteGraceMinutes || "0", 10) || 0),
    enabled: input.taskEnabled,
  };
}
