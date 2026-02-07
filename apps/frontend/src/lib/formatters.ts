/* ------------------------------------------------------------------ */
/*  时间 / 间隔格式化工具                                               */
/* ------------------------------------------------------------------ */

import { intervalUnitLabels } from "./constants";

export const formatTimestamp = (ts?: number | null): string => {
  if (!ts) return "未知时间";
  const date = new Date(ts * 1000);
  if (Number.isNaN(date.getTime())) return "未知时间";
  return date.toLocaleString();
};

export const formatShortTime = (ts?: number | null): string => {
  if (!ts) return "--:--";
  const date = new Date(ts * 1000);
  if (Number.isNaN(date.getTime())) return "--:--";
  return date.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });
};

export const isTimeValue = (value: string): boolean => {
  const parts = value.split(":");
  if (parts.length !== 2) return false;
  const hour = Number(parts[0]);
  const minute = Number(parts[1]);
  if (Number.isNaN(hour) || Number.isNaN(minute)) return false;
  if (hour < 0 || hour > 23) return false;
  if (minute < 0 || minute > 59) return false;
  return true;
};

export const formatIntervalLabel = (
  value: string,
  unit: string,
  timeValue: string
): string => {
  const safeValue = value || "1";
  const unitLabel = intervalUnitLabels[unit] || unit;
  if (unit === "days") {
    const safeTime = timeValue || "01:00";
    return `${safeValue} ${unitLabel} ${safeTime}`;
  }
  return `${safeValue} ${unitLabel}`;
};

export const isSameDay = (ts: number, compare: Date): boolean => {
  const date = new Date(ts * 1000);
  return (
    date.getFullYear() === compare.getFullYear() &&
    date.getMonth() === compare.getMonth() &&
    date.getDate() === compare.getDate()
  );
};
