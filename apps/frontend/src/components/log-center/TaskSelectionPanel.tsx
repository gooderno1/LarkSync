import type { MutableRefObject } from "react";

import { formatShortTime } from "../../lib/formatters";
import { modeLabels, stateLabels, stateTones } from "../../lib/constants";
import { diagnosticActivityTime, shortPath } from "../../lib/logCenter";
import { StatusPill } from "../StatusPill";
import { IconRefresh } from "../Icons";
import { cn } from "../../lib/utils";
import type { SyncTask, SyncTaskOverview, SyncTaskStatus } from "../../types";

type TaskSelectionPanelProps = {
  taskPickerRef: MutableRefObject<HTMLDivElement | null>;
  selectedTask: SyncTask | null;
  selectedTaskId: string | null;
  selectedStatus: SyncTaskStatus | null;
  selectedStateKey: string;
  lastActivityAt: number | null;
  overviewQueryIsFetching: boolean;
  diagnosticsQueryIsFetching: boolean;
  taskPickerOpen: boolean;
  setTaskPickerOpen: (value: boolean | ((value: boolean) => boolean)) => void;
  taskPickerQuery: string;
  setTaskPickerQuery: (value: string) => void;
  taskPickerOptions: SyncTaskOverview[];
  selectTask: (taskId: string) => void;
  refreshDiagnostics: () => void;
};

export function TaskSelectionPanel({
  taskPickerRef,
  selectedTask,
  selectedTaskId,
  selectedStatus,
  selectedStateKey,
  lastActivityAt,
  overviewQueryIsFetching,
  diagnosticsQueryIsFetching,
  taskPickerOpen,
  setTaskPickerOpen,
  taskPickerQuery,
  setTaskPickerQuery,
  taskPickerOptions,
  selectTask,
  refreshDiagnostics,
}: TaskSelectionPanelProps) {
  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-3.5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-zinc-50">任务选择</h3>
        </div>
        <div className="flex items-center gap-2">
          {selectedTask ? (
            <StatusPill
              label={stateLabels[selectedStateKey] || selectedStateKey}
              tone={stateTones[selectedStateKey] || "neutral"}
              dot={selectedStatus?.state === "running"}
            />
          ) : null}
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-3 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
            onClick={refreshDiagnostics}
            type="button"
          >
            <IconRefresh className="h-3.5 w-3.5" /> 刷新
          </button>
        </div>
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(420px,1fr)_minmax(0,1fr)_auto]">
        <div className="space-y-1.5" ref={taskPickerRef}>
          <label className="text-[11px] text-zinc-500">当前任务</label>
          <div className="relative">
            <button
              className="flex w-full items-center justify-between rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-left text-sm text-zinc-200 outline-none transition hover:border-zinc-600"
              onClick={() => setTaskPickerOpen((value) => !value)}
              type="button"
            >
              <span className="truncate">{selectedTask?.name || "请选择任务"}</span>
              <span className="text-xs text-zinc-500">{taskPickerOpen ? "收起" : "选择"}</span>
            </button>
            {taskPickerOpen ? (
              <div className="absolute left-0 right-0 top-[calc(100%+8px)] z-20 rounded-xl border border-zinc-800 bg-zinc-950 p-2 shadow-xl">
                <input
                  autoFocus
                  className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
                  placeholder="搜索任务名"
                  value={taskPickerQuery}
                  onChange={(event) => setTaskPickerQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Escape") setTaskPickerOpen(false);
                  }}
                />
                <div className="mt-2 max-h-64 space-y-1 overflow-y-auto pr-1 log-scroll-area">
                  {taskPickerOptions.length === 0 ? (
                    <div className="rounded-lg px-3 py-5 text-center text-xs text-zinc-500">没有匹配的任务</div>
                  ) : (
                    taskPickerOptions.map((overview) => {
                      const task = overview.task;
                      const stateKey = !task.enabled ? "paused" : overview.status?.state || "idle";
                      return (
                        <button
                          key={task.id}
                          className={cn(
                            "w-full rounded-lg border px-3 py-2 text-left transition",
                            selectedTaskId === task.id
                              ? "border-[#3370FF]/50 bg-[#3370FF]/10"
                              : "border-zinc-800 bg-zinc-900/60 hover:border-zinc-700 hover:bg-zinc-900",
                          )}
                          onClick={() => {
                            selectTask(task.id);
                            setTaskPickerOpen(false);
                          }}
                          type="button"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <span className="truncate text-sm font-medium text-zinc-100">{task.name || "未命名任务"}</span>
                            <StatusPill label={stateLabels[stateKey] || stateKey} tone={stateTones[stateKey] || "neutral"} />
                          </div>
                          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-zinc-500">
                            <span>{modeLabels[task.sync_mode] || task.sync_mode}</span>
                            <span>{formatShortTime(diagnosticActivityTime(overview))}</span>
                          </div>
                        </button>
                      );
                    })
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-[11px] text-zinc-500">当前任务信息</label>
          <div className="flex min-h-[40px] flex-wrap items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-950/40 px-3 py-2 text-[11px] text-zinc-500">
            {selectedTask ? (
              <>
                <span>{modeLabels[selectedTask.sync_mode] || selectedTask.sync_mode}</span>
                {lastActivityAt ? (
                  <>
                    <span className="text-zinc-700">|</span>
                    <span>最近活动 {formatShortTime(lastActivityAt)}</span>
                  </>
                ) : null}
                <span className="text-zinc-700">|</span>
                <span className="truncate">{shortPath(selectedTask.local_path, 84)}</span>
              </>
            ) : (
              <span>暂无任务</span>
            )}
          </div>
        </div>

        <div className="flex items-end justify-end text-[11px] text-zinc-500">
          {overviewQueryIsFetching || diagnosticsQueryIsFetching ? (
            <span className="shrink-0">正在刷新…</span>
          ) : null}
        </div>
      </div>
    </section>
  );
}
