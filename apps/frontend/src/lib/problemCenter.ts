import type { Tone } from "../types";

const CATEGORY_LABELS: Record<string, string> = {
  auth_permission: "权限认证",
  upload: "上传失败",
  download: "下载失败",
  conversion: "格式转换",
  deletion: "删除状态",
  conflict: "内容冲突",
  task_config: "任务配置",
  network_remote: "网络与云端",
  local_io: "本地文件",
  system: "系统",
  updater: "更新组件",
};

export function problemCategoryLabel(category: string): string {
  return CATEGORY_LABELS[category] || category;
}

export function problemSeverityTone(severity: string): Tone {
  if (severity === "critical" || severity === "high") return "danger";
  if (severity === "medium") return "warning";
  if (severity === "low") return "info";
  return "neutral";
}

export function shouldKeepProblemSelection(
  selectedId: string | null,
  visibleIds: string[],
): boolean {
  return Boolean(selectedId && visibleIds.includes(selectedId));
}

export const problemStateLabels: Record<string, string> = {
  open: "未解决",
  in_progress: "处理中",
  waiting: "等待验证",
  resolved: "已解决",
  ignored: "已忽略",
};
