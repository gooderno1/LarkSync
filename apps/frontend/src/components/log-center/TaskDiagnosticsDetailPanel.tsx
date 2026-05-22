import type { EventFilter } from "../../lib/eventFilters";
import { formatTimestamp } from "../../lib/formatters";
import type { RunAlertMeta } from "../../lib/taskDiagnosticsState";
import { stateLabels, stateTones } from "../../lib/constants";
import { compactRunId, shortPath } from "../../lib/logCenter";
import type { TaskProgress } from "../../lib/progress";
import { StatusPill } from "../StatusPill";
import { IconActivity, IconRefresh } from "../Icons";
import { cn } from "../../lib/utils";
import type {
  SyncFileEvent,
  SyncLogEntry,
  SyncTask,
  SyncTaskDiagnosticCounts,
  SyncTaskRunSummary,
  SyncTaskStatus,
} from "../../types";
import type { DetailTab } from "../../hooks/useLogCenterTaskDiagnostics";
import { TaskDiagnosticsOverviewTab } from "./TaskDiagnosticsOverviewTab";
import { TaskDiagnosticsProblemsTab } from "./TaskDiagnosticsProblemsTab";
import { TaskDiagnosticsEventsTab } from "./TaskDiagnosticsEventsTab";

type TaskDiagnosticsDetailPanelProps = {
  selectedTask: SyncTask | null;
  selectedRun: SyncTaskRunSummary | null;
  selectedStatus: SyncTaskStatus | null;
  selectedStateKey: string;
  lastActivityAt: number | null;
  activeRunId: string | null;
  detailTab: DetailTab;
  setDetailTab: (tab: DetailTab) => void;
  diagnosticsQueryIsFetching: boolean;
  refreshDiagnostics: () => void;
  progress: TaskProgress;
  diagnosticCounts?: SyncTaskDiagnosticCounts | null;
  currentFile: SyncFileEvent | null;
  runAlert: RunAlertMeta | null;
  selectedProblems: SyncLogEntry[];
  eventFilter: EventFilter;
  setEventFilter: (value: EventFilter) => void;
  eventSearch: string;
  setEventSearch: (value: string) => void;
  resetEventPage: () => void;
  selectedEventsQueryIsLoading: boolean;
  selectedTimelineEntries: SyncLogEntry[];
  selectedTimelineTotal: number;
  eventPage: number;
  setEventPage: (page: number) => void;
  eventPageSize: number;
  setEventPageSize: (size: number) => void;
};

export function TaskDiagnosticsDetailPanel({
  selectedTask,
  selectedRun,
  selectedStatus,
  selectedStateKey,
  lastActivityAt,
  activeRunId,
  detailTab,
  setDetailTab,
  diagnosticsQueryIsFetching,
  refreshDiagnostics,
  progress,
  diagnosticCounts,
  currentFile,
  runAlert,
  selectedProblems,
  eventFilter,
  setEventFilter,
  eventSearch,
  setEventSearch,
  resetEventPage,
  selectedEventsQueryIsLoading,
  selectedTimelineEntries,
  selectedTimelineTotal,
  eventPage,
  setEventPage,
  eventPageSize,
  setEventPageSize,
}: TaskDiagnosticsDetailPanelProps) {
  return (
    <section className="flex min-h-0 flex-col rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
      {!selectedTask ? (
        <div className="flex flex-1 items-center justify-center text-center">
          <div>
            <IconActivity className="mx-auto h-10 w-10 text-zinc-700" />
            <p className="mt-3 text-sm text-zinc-500">请选择一个任务查看运行详情。</p>
          </div>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-3">
                <StatusPill
                  label={stateLabels[selectedRun?.state || selectedStateKey] || selectedRun?.state || selectedStateKey}
                  tone={stateTones[selectedRun?.state || selectedStateKey] || "neutral"}
                  dot={selectedRun?.state === "running"}
                />
                <h3 className="truncate text-base font-semibold text-zinc-50">
                  {selectedTask.name || "未命名任务"}
                </h3>
                {lastActivityAt ? <span className="text-[11px] text-zinc-500">最近活动 {formatTimestamp(lastActivityAt)}</span> : null}
              </div>
              <p className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-zinc-500">
                <span>运行 {compactRunId(selectedRun?.run_id || activeRunId || selectedStatus?.current_run_id || null)}</span>
                <span>{shortPath(selectedTask.local_path, 92)}</span>
              </p>
            </div>
            <button
              className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
              onClick={refreshDiagnostics}
              type="button"
            >
              <IconRefresh className="h-3.5 w-3.5" /> 刷新诊断
            </button>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            {[
              ["overview", "概览"],
              ["problems", "问题"],
              ["events", "事件"],
            ].map(([value, label]) => (
              <button
                key={value}
                className={cn(
                  "rounded-lg border px-3 py-1.5 text-xs transition",
                  detailTab === value
                    ? "border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]"
                    : "border-zinc-700 text-zinc-400 hover:bg-zinc-800",
                )}
                onClick={() => setDetailTab(value as DetailTab)}
                type="button"
              >
                {label}
              </button>
            ))}
            {diagnosticsQueryIsFetching ? <span className="ml-auto text-xs text-zinc-500">正在更新当前详情…</span> : null}
          </div>

          <div className="mt-4 flex-1 min-h-0 overflow-y-auto pr-1 log-scroll-area">
            {detailTab === "overview" ? (
              <TaskDiagnosticsOverviewTab
                selectedTask={selectedTask}
                selectedRun={selectedRun}
                selectedStatus={selectedStatus}
                lastActivityAt={lastActivityAt}
                progress={progress}
                diagnosticCounts={diagnosticCounts}
                currentFile={currentFile}
                runAlert={runAlert}
              />
            ) : null}

            {detailTab === "problems" ? (
              <TaskDiagnosticsProblemsTab selectedProblems={selectedProblems} />
            ) : null}

            {detailTab === "events" ? (
              <TaskDiagnosticsEventsTab
                eventFilter={eventFilter}
                setEventFilter={setEventFilter}
                eventSearch={eventSearch}
                setEventSearch={setEventSearch}
                resetEventPage={resetEventPage}
                selectedEventsQueryIsLoading={selectedEventsQueryIsLoading}
                selectedTimelineEntries={selectedTimelineEntries}
                selectedTimelineTotal={selectedTimelineTotal}
                eventPage={eventPage}
                setEventPage={setEventPage}
                eventPageSize={eventPageSize}
                setEventPageSize={setEventPageSize}
              />
            ) : null}
          </div>
        </>
      )}
    </section>
  );
}
