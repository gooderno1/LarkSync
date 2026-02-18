import type { SyncTaskStatus } from "../types";

export type TaskProgress = {
  progress: number | null;
  effectiveTotal: number;
  completed: number;
  failed: number;
  skipped: number;
  total: number;
};

export function computeTaskProgress(status?: SyncTaskStatus | null): TaskProgress {
  const total = status?.total_files ?? 0;
  const completed = status?.completed_files ?? 0;
  const failed = status?.failed_files ?? 0;
  const skipped = status?.skipped_files ?? 0;
  const effectiveTotal = Math.max(total - skipped, 0);
  if (effectiveTotal <= 0) {
    return {
      progress: null,
      effectiveTotal,
      completed,
      failed,
      skipped,
      total,
    };
  }
  const safeCompleted = Math.min(Math.max(completed, 0), effectiveTotal);
  const progress = Math.max(0, Math.min(100, Math.round((safeCompleted / effectiveTotal) * 100)));
  return {
    progress,
    effectiveTotal,
    completed,
    failed,
    skipped,
    total,
  };
}
