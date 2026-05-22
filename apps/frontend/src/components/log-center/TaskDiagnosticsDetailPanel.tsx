import { EVENT_FILTERS, type EventFilter, DANGER_STATUSES, WARNING_STATUSES } from "../../lib/eventFilters";
import { formatTimestamp } from "../../lib/formatters";
import { stateLabels, stateTones, statusLabelMap } from "../../lib/constants";
import { compactRunId, formatDuration, shortPath, statusTone } from "../../lib/logCenter";
import type { TaskProgress } from "../../lib/progress";
import { StatusPill } from "../StatusPill";
import { IconActivity, IconRefresh } from "../Icons";
import { Pagination } from "../Pagination";
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

type RunAlertMeta = {
  label: string;
  className: string;
  message: string;
};

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
            ) : null}

            {detailTab === "problems" ? (
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
            ) : null}

            {detailTab === "events" ? (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  {EVENT_FILTERS.map((filter) => (
                    <button
                      key={filter.value}
                      className={cn(
                        "rounded-lg border px-3 py-1.5 text-xs transition",
                        eventFilter === filter.value
                          ? "border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]"
                          : "border-zinc-700 text-zinc-400 hover:bg-zinc-800",
                      )}
                      onClick={() => {
                        setEventFilter(filter.value);
                        resetEventPage();
                      }}
                      type="button"
                    >
                      {filter.label}
                    </button>
                  ))}
                </div>
                <input
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
                  placeholder="搜索当前运行的文件路径或错误信息"
                  value={eventSearch}
                  onChange={(event) => {
                    setEventSearch(event.target.value);
                    resetEventPage();
                  }}
                />
                <div className="space-y-3">
                  {selectedEventsQueryIsLoading && selectedTimelineEntries.length === 0 ? (
                    [1, 2, 3, 4].map((item) => <div key={item} className="h-16 animate-pulse rounded-xl bg-zinc-800/50" />)
                  ) : selectedTimelineEntries.length === 0 ? (
                    <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 py-8 text-center">
                      <IconActivity className="mx-auto h-10 w-10 text-zinc-700" />
                      <p className="mt-3 text-sm text-zinc-500">暂无匹配事件。</p>
                    </div>
                  ) : (
                    selectedTimelineEntries.map((entry, index) => (
                      <div key={`${entry.timestamp}-${index}`} className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0 space-y-1">
                            <p className="text-xs text-zinc-500">{formatTimestamp(entry.timestamp)}</p>
                            {entry.runId ? <p className="text-[11px] text-zinc-700">运行 {entry.runId}</p> : null}
                            <p className="break-all text-xs text-zinc-400">{entry.path}</p>
                          </div>
                          <StatusPill
                            label={statusLabelMap[entry.status] || entry.status}
                            tone={statusTone(entry.status, DANGER_STATUSES, WARNING_STATUSES)}
                          />
                        </div>
                        {entry.message ? <p className="mt-2 text-xs text-zinc-600">{entry.message}</p> : null}
                      </div>
                    ))
                  )}
                </div>
                {(selectedTimelineTotal > 0 || selectedTimelineEntries.length > 0) ? (
                  <div className="border-t border-zinc-800 pt-4">
                    <Pagination
                      page={eventPage}
                      pageSize={eventPageSize}
                      total={selectedTimelineTotal}
                      onPageChange={setEventPage}
                      onPageSizeChange={(size) => {
                        setEventPageSize(size);
                        resetEventPage();
                      }}
                      pageSizeOptions={[20, 30, 50, 100]}
                    />
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        </>
      )}
    </section>
  );
}
