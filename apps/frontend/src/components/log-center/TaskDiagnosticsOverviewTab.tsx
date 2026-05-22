import { formatTimestamp } from "../../lib/formatters";
import type { TaskProgress } from "../../lib/progress";
import { StatusPill } from "../StatusPill";
import { cn } from "../../lib/utils";
import { formatDuration, shortPath } from "../../lib/logCenter";
import type {
  SyncFileEvent,
  SyncTask,
  SyncTaskDiagnosticCounts,
  SyncTaskRunSummary,
  SyncTaskStatus,
} from "../../types";

export type RunAlertMeta = {
  label: string;
  className: string;
  message: string;
};

type TaskDiagnosticsOverviewTabProps = {
  selectedTask: SyncTask;
  selectedRun: SyncTaskRunSummary | null;
  selectedStatus: SyncTaskStatus | null;
  lastActivityAt: number | null;
  progress: TaskProgress;
  diagnosticCounts?: SyncTaskDiagnosticCounts | null;
  currentFile: SyncFileEvent | null;
  runAlert: RunAlertMeta | null;
};

export function TaskDiagnosticsOverviewTab({
  selectedTask,
  selectedRun,
  selectedStatus,
  lastActivityAt,
  progress,
  diagnosticCounts,
  currentFile,
  runAlert,
}: TaskDiagnosticsOverviewTabProps) {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] text-zinc-400">
          <span>开始 {selectedRun?.started_at ? formatTimestamp(selectedRun.started_at) : "暂无"}</span>
          <span>耗时 {formatDuration(selectedRun?.started_at, selectedRun?.finished_at, selectedRun?.last_event_at)}</span>
          <span>进度 {progress.progress === null ? "暂无" : `${progress.progress}%`}</span>
          <span>阶段 {selectedRun?.state === "running" ? "同步进行中" : "本轮已结束"}</span>
        </div>
        <div className="mt-2.5 flex flex-wrap gap-2">
          <StatusPill label={`上传 ${diagnosticCounts?.uploaded ?? 0}`} tone="info" />
          <StatusPill label={`下载 ${diagnosticCounts?.downloaded ?? 0}`} tone="info" />
          <StatusPill label={`删除 ${diagnosticCounts?.deleted ?? 0}`} tone="info" />
          <StatusPill label={`待删除 ${diagnosticCounts?.delete_pending ?? 0}`} tone={(diagnosticCounts?.delete_pending ?? 0) > 0 ? "warning" : "success"} />
          <StatusPill label={`删除失败 ${diagnosticCounts?.delete_failed ?? 0}`} tone={(diagnosticCounts?.delete_failed ?? 0) > 0 ? "danger" : "success"} />
          <StatusPill label={`跳过 ${diagnosticCounts?.skipped ?? 0}`} tone="warning" />
          <StatusPill label={`失败 ${diagnosticCounts?.failed ?? 0}`} tone={(diagnosticCounts?.failed ?? 0) > 0 ? "danger" : "success"} />
          <StatusPill label={`冲突 ${diagnosticCounts?.conflicts ?? 0}`} tone={(diagnosticCounts?.conflicts ?? 0) > 0 ? "warning" : "success"} />
          <StatusPill label={`总数 ${diagnosticCounts?.total ?? 0}`} tone="neutral" />
        </div>
        {currentFile ? (
          <div className="mt-2 space-y-1">
            <p className="truncate text-[11px] text-zinc-500">当前处理：{shortPath(currentFile.path, 110)}</p>
            {currentFile.message ? (
              <p className="truncate text-[11px] text-zinc-600">{currentFile.message}</p>
            ) : null}
          </div>
        ) : null}
      </div>

      {runAlert ? (
        <div className={cn("rounded-xl border px-4 py-2.5 text-sm", runAlert.className)}>
          {runAlert.label}：{runAlert.message}
        </div>
      ) : null}

      <div className="grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-4">
          <p className="text-xs text-zinc-500">同步目标</p>
          <p className="mt-2 text-[11px] text-zinc-500">本地目录</p>
          <p className="mt-1 break-all text-sm text-zinc-200">{shortPath(selectedTask.local_path, 120)}</p>
          <p className="mt-3 text-[11px] text-zinc-500">云端目录</p>
          <p className="mt-1 break-all text-sm text-zinc-200">
            {selectedTask.cloud_folder_name || selectedTask.cloud_folder_token || "未配置"}
          </p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-4">
          <p className="text-xs text-zinc-500">最近活动</p>
          <p className="mt-2 text-sm font-semibold text-zinc-100">
            {lastActivityAt ? formatTimestamp(lastActivityAt) : "暂无"}
          </p>
          <p className="mt-2 text-xs text-zinc-500">
            云端：{selectedTask.cloud_folder_name || selectedTask.cloud_folder_token}
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-4">
        <p className="text-xs text-zinc-500">运行判断</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <StatusPill label={diagnosticCounts?.deleted ? `删除 ${diagnosticCounts.deleted}` : "无删除"} tone={diagnosticCounts?.deleted ? "info" : "neutral"} />
          <StatusPill label={diagnosticCounts?.delete_pending ? `待删除 ${diagnosticCounts.delete_pending}` : "无待删除"} tone={diagnosticCounts?.delete_pending ? "warning" : "success"} />
          <StatusPill label={diagnosticCounts?.delete_failed ? `删除失败 ${diagnosticCounts.delete_failed}` : "无删除失败"} tone={diagnosticCounts?.delete_failed ? "danger" : "success"} />
          <StatusPill label={diagnosticCounts?.failed ? `失败 ${diagnosticCounts.failed}` : "无失败"} tone={diagnosticCounts?.failed ? "danger" : "success"} />
          <StatusPill label={diagnosticCounts?.conflicts ? `冲突 ${diagnosticCounts.conflicts}` : "无冲突"} tone={diagnosticCounts?.conflicts ? "warning" : "success"} />
          <StatusPill label={diagnosticCounts?.skipped ? `跳过 ${diagnosticCounts.skipped}` : "无跳过"} tone={diagnosticCounts?.skipped ? "warning" : "success"} />
          <StatusPill label={selectedStatus?.state === "running" ? "同步进行中" : "本轮已结束"} tone={selectedStatus?.state === "running" ? "info" : "neutral"} />
        </div>
      </div>
    </div>
  );
}
