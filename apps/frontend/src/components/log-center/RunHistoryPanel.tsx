import { compactRunId, formatDuration } from "../../lib/logCenter";
import { formatTimestamp } from "../../lib/formatters";
import { stateLabels, stateTones } from "../../lib/constants";
import { StatusPill } from "../StatusPill";
import { IconTasks } from "../Icons";
import { cn } from "../../lib/utils";
import type { SyncTask, SyncTaskRunSummary } from "../../types";

type RunHistoryPanelProps = {
  selectedTask: SyncTask | null;
  diagnosticsQueryIsLoading: boolean;
  recentRuns: SyncTaskRunSummary[];
  activeRunId: string | null;
  setSelectedRunId: (runId: string) => void;
  resetEventPage: () => void;
};

export function RunHistoryPanel({
  selectedTask,
  diagnosticsQueryIsLoading,
  recentRuns,
  activeRunId,
  setSelectedRunId,
  resetEventPage,
}: RunHistoryPanelProps) {
  return (
    <section className="flex min-h-0 flex-col rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-zinc-50">运行记录</h3>
        </div>
        <StatusPill label="最近 20 次" tone="info" />
      </div>

      {!selectedTask ? (
        <div className="flex flex-1 items-center justify-center text-center">
          <div>
            <IconTasks className="mx-auto h-10 w-10 text-zinc-700" />
            <p className="mt-3 text-sm text-zinc-500">请选择一个任务查看运行记录。</p>
          </div>
        </div>
      ) : (
        <div className="mt-4 flex-1 min-h-0 space-y-2 overflow-y-auto pr-1 log-scroll-area">
          {diagnosticsQueryIsLoading && recentRuns.length === 0 ? (
            [1, 2, 3].map((item) => <div key={item} className="h-24 animate-pulse rounded-xl bg-zinc-800/50" />)
          ) : recentRuns.length === 0 ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 px-4 py-5 text-center text-sm text-zinc-500">
              暂无运行记录。
            </div>
          ) : (
            recentRuns.map((run) => (
              <button
                key={run.run_id}
                className={cn(
                  "w-full rounded-xl border px-3 py-2 text-left transition",
                  activeRunId === run.run_id
                    ? "border-[#3370FF]/50 bg-[#3370FF]/10"
                    : "border-zinc-800 bg-zinc-950/40 hover:border-zinc-700 hover:bg-zinc-900",
                )}
                onClick={() => {
                  setSelectedRunId(run.run_id);
                  resetEventPage();
                }}
                type="button"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-zinc-100">{compactRunId(run.run_id)}</p>
                    <p className="mt-1 text-[11px] text-zinc-500">
                      {run.started_at ? formatTimestamp(run.started_at) : "开始时间未知"}
                    </p>
                  </div>
                  <StatusPill
                    label={stateLabels[run.state] || run.state}
                    tone={stateTones[run.state] || "neutral"}
                    dot={run.state === "running"}
                  />
                </div>
                <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-zinc-500">
                  <span>上 {run.counts.uploaded}</span>
                  <span>下 {run.counts.downloaded}</span>
                  <span>删 {run.counts.deleted}</span>
                  <span>待删 {run.counts.delete_pending}</span>
                  <span>删失败 {run.counts.delete_failed}</span>
                  <span>失败 {run.counts.failed}</span>
                  <span>冲突 {run.counts.conflicts}</span>
                  <span>耗时 {formatDuration(run.started_at, run.finished_at, run.last_event_at)}</span>
                </div>
                {run.last_error ? (
                  <p className="mt-1.5 truncate text-[11px] text-rose-300">{run.last_error}</p>
                ) : null}
              </button>
            ))
          )}
        </div>
      )}
    </section>
  );
}
