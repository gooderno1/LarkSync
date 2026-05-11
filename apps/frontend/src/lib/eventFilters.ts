export type EventFilter =
  | "all"
  | "uploaded"
  | "downloaded"
  | "deleted"
  | "problems"
  | "skipped"
  | "changes";

export const PROBLEM_STATUS_VALUES = ["failed", "delete_failed", "conflict", "cancelled"] as const;
export const WARNING_STATUS_VALUES = ["skipped", "delete_pending", "cancelled", "queued"] as const;
export const DANGER_STATUS_VALUES = ["failed", "delete_failed", "conflict"] as const;
export const CHANGE_STATUS_VALUES = ["uploaded", "downloaded", "deleted", "mirrored", "delete_pending", "conflict"] as const;
export const DELETE_STATUS_VALUES = ["deleted", "delete_pending", "delete_failed"] as const;

export const PROBLEM_STATUSES = new Set<string>(PROBLEM_STATUS_VALUES);
export const WARNING_STATUSES = new Set<string>(WARNING_STATUS_VALUES);
export const DANGER_STATUSES = new Set<string>(DANGER_STATUS_VALUES);

export const EVENT_FILTERS: Array<{ value: EventFilter; label: string }> = [
  { value: "all", label: "全部事件" },
  { value: "uploaded", label: "上传" },
  { value: "downloaded", label: "下载" },
  { value: "deleted", label: "删除" },
  { value: "problems", label: "问题" },
  { value: "skipped", label: "跳过" },
  { value: "changes", label: "实际变更" },
];

export function buildStatusParams(filter: EventFilter): string[] {
  switch (filter) {
    case "uploaded":
      return ["uploaded"];
    case "downloaded":
      return ["downloaded"];
    case "deleted":
      return [...DELETE_STATUS_VALUES];
    case "problems":
      return [...PROBLEM_STATUS_VALUES];
    case "skipped":
      return ["skipped"];
    case "changes":
      return [...CHANGE_STATUS_VALUES];
    case "all":
    default:
      return [];
  }
}
