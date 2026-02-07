/* ------------------------------------------------------------------ */
/*  静态标签映射 & 常量                                                 */
/* ------------------------------------------------------------------ */

import type { Tone } from "../types";

export const modeLabels: Record<string, string> = {
  bidirectional: "双向同步",
  download_only: "仅下载",
  upload_only: "仅上传",
};

export const updateModeLabels: Record<string, string> = {
  auto: "自动",
  partial: "局部",
  full: "全量",
};

export const intervalUnitLabels: Record<string, string> = {
  seconds: "秒",
  hours: "小时",
  days: "天",
};

export const statusLabelMap: Record<string, string> = {
  downloaded: "下载",
  uploaded: "上传",
  failed: "失败",
  skipped: "跳过",
  started: "开始",
  success: "完成",
  cancelled: "取消",
};

export const stateLabels: Record<string, string> = {
  idle: "空闲",
  running: "同步中",
  success: "完成",
  failed: "失败",
  cancelled: "已取消",
  paused: "已停用",
};

export const stateTones: Record<string, Tone> = {
  idle: "neutral",
  running: "info",
  success: "success",
  failed: "danger",
  cancelled: "warning",
  paused: "warning",
};
