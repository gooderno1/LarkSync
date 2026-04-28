import type { SyncTaskStatus } from "../types";

export type TaskProgress = {
  progress: number | null;
  effectiveTotal: number;
  processed: number;
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
  const effectiveTotal = Math.max(total, 0);
  const processed = Math.min(Math.max(completed + failed + skipped, 0), effectiveTotal);
  if (effectiveTotal <= 0) {
    return {
      progress: null,
      effectiveTotal,
      processed,
      completed,
      failed,
      skipped,
      total,
    };
  }
  const progress = Math.max(0, Math.min(100, Math.round((processed / effectiveTotal) * 100)));
  return {
    progress,
    effectiveTotal,
    processed,
    completed,
    failed,
    skipped,
    total,
  };
}
