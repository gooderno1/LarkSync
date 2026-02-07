/* ------------------------------------------------------------------ */
/*  骨架屏组件                                                          */
/* ------------------------------------------------------------------ */

import { cn } from "../lib/utils";

export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-xl bg-zinc-800/50", className)}
      {...props}
    />
  );
}

/** 任务列表骨架屏 */
export function TaskListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <Skeleton className="h-5 w-48" />
              <Skeleton className="h-3 w-32" />
            </div>
            <Skeleton className="h-6 w-16 rounded-full" />
          </div>
          <Skeleton className="mt-4 h-20 w-full" />
          <div className="mt-4 flex gap-2">
            <Skeleton className="h-8 w-24 rounded-lg" />
            <Skeleton className="h-8 w-20 rounded-lg" />
            <Skeleton className="h-8 w-20 rounded-lg" />
          </div>
        </div>
      ))}
    </div>
  );
}

/** 日志列表骨架屏 */
export function LogListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1.5">
              <Skeleton className="h-3 w-28" />
              <Skeleton className="h-4 w-36" />
            </div>
            <Skeleton className="h-5 w-14 rounded-full" />
          </div>
          <Skeleton className="mt-2 h-3 w-56" />
        </div>
      ))}
    </div>
  );
}

/** 统计卡片骨架屏 */
export function StatCardSkeleton() {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
      <Skeleton className="h-3 w-16" />
      <Skeleton className="mt-3 h-7 w-12" />
      <Skeleton className="mt-2 h-3 w-24" />
    </div>
  );
}
