import { formatTimestamp } from "../../lib/formatters";
import { statusLabelMap } from "../../lib/constants";
import { StatusPill } from "../StatusPill";
import type { SyncLogEntry } from "../../types";

type TaskDiagnosticsProblemsTabProps = {
  selectedProblems: SyncLogEntry[];
};

export function TaskDiagnosticsProblemsTab({ selectedProblems }: TaskDiagnosticsProblemsTabProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-zinc-500">只显示当前运行的失败、冲突、删除失败和取消事件。</p>
        <StatusPill label={`${selectedProblems.length} 条`} tone={selectedProblems.length ? "danger" : "success"} />
      </div>
      {selectedProblems.length === 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 px-4 py-6 text-center text-sm text-zinc-500">
          最近未发现问题事件。
        </div>
      ) : (
        selectedProblems.map((entry, index) => (
          <div key={`${entry.timestamp}-${index}`} className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-zinc-500">
                {formatTimestamp(entry.timestamp)}
                {entry.runId ? <span className="ml-2 text-zinc-700">运行 {entry.runId}</span> : null}
              </p>
              <StatusPill label={statusLabelMap[entry.status] || entry.status} tone="danger" />
            </div>
            <p className="mt-2 break-all text-xs text-zinc-300">{entry.path}</p>
            {entry.message ? <p className="mt-1 text-xs text-rose-300">{entry.message}</p> : null}
          </div>
        ))
      )}
    </div>
  );
}
