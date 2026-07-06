/* ------------------------------------------------------------------ */
/*  日志中心页面：任务诊断 + 系统日志 + 事件管理                         */
/* ------------------------------------------------------------------ */

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useConflicts } from "../hooks/useConflicts";
import { useConflictResolutionQueue } from "../hooks/useConflictResolutionQueue";
import { useLogCenterTaskDiagnostics } from "../hooks/useLogCenterTaskDiagnostics";
import { apiFetch } from "../lib/api";
import { useToast } from "../components/ui/toast";
import { CONFLICT_ACTION_LABELS } from "../lib/conflictResolution";
import { cn } from "../lib/utils";
import { ThemeToggle } from "../components/ThemeToggle";
import { SystemLogPanel } from "../components/log-center/SystemLogPanel";
import { EventManagementPanel } from "../components/log-center/EventManagementPanel";
import { TaskSelectionPanel } from "../components/log-center/TaskSelectionPanel";
import { RunHistoryPanel } from "../components/log-center/RunHistoryPanel";
import { TaskDiagnosticsDetailPanel } from "../components/log-center/TaskDiagnosticsDetailPanel";
import { mapSyncLogResponse, type SyncLogResponse, type SyncLogResponseRaw } from "../lib/logCenter";

type FileLogEntry = {
  timestamp: string;
  level: string;
  message: string;
};

type FileLogResponse = {
  total: number;
  items: FileLogEntry[];
};

const EVENT_MANAGEMENT_STATUSES = ["delete_pending", "delete_failed", "failed", "conflict", "cancelled"];

export function LogCenterPage() {
  const [logTab, setLogTab] = useState<"tasks" | "file-logs" | "events">("tasks");
  const { conflicts, conflictLoading, conflictError, refreshConflicts, resolveConflictAsync } = useConflicts(logTab === "events");
  const { toast } = useToast();
  const taskPickerRef = useRef<HTMLDivElement | null>(null);

  const [fileLogLevel, setFileLogLevel] = useState("");
  const [fileLogSearch, setFileLogSearch] = useState("");
  const [fileLogPage, setFileLogPage] = useState(1);
  const [fileLogPageSize, setFileLogPageSize] = useState(50);
  const [fileLogOrder, setFileLogOrder] = useState<"asc" | "desc">("desc");
  const [showAllEvents, setShowAllEvents] = useState(false);
  const { conflictResolutionStates, queueSummary, handleResolveConflict } = useConflictResolutionQueue({
    resolveConflictAsync,
    toast,
  });
  const {
    selectedTaskId,
    setSelectedRunId,
    taskPickerQuery,
    setTaskPickerQuery,
    taskPickerOpen,
    setTaskPickerOpen,
    showAllTasks,
    setShowAllTasks,
    hiddenTaskCount,
    focusedTaskCount,
    detailTab,
    setDetailTab,
    eventFilter,
    setEventFilter,
    eventSearch,
    setEventSearch,
    eventPage,
    setEventPage,
    eventPageSize,
    setEventPageSize,
    selectTask,
    overviewQuery,
    selectedTask,
    selectedStatus,
    taskPickerOptions,
    diagnosticsQuery,
    recentRuns,
    activeRunId,
    selectedEventsQuery,
    selectedRun,
    selectedTimelineEntries,
    selectedTimelineTotal,
    selectedProblems,
    progress,
    currentFile,
    diagnosticCounts,
    lastActivityAt,
    selectedStateKey,
    runAlert,
    resetEventPage,
    refreshDiagnostics,
  } = useLogCenterTaskDiagnostics(logTab === "tasks");

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (!taskPickerRef.current) return;
      if (!taskPickerRef.current.contains(event.target as Node)) {
        setTaskPickerOpen(false);
      }
    };
    window.addEventListener("mousedown", handlePointerDown);
    return () => window.removeEventListener("mousedown", handlePointerDown);
  }, [setTaskPickerOpen]);

  const fileLogsQuery = useQuery<FileLogResponse>({
    queryKey: ["file-logs", fileLogLevel, fileLogSearch, fileLogOrder, fileLogPage, fileLogPageSize],
    queryFn: () => {
      const params = new URLSearchParams();
      params.set("limit", String(fileLogPageSize));
      params.set("offset", String((fileLogPage - 1) * fileLogPageSize));
      if (fileLogLevel) params.set("level", fileLogLevel);
      if (fileLogSearch) params.set("search", fileLogSearch);
      params.set("order", fileLogOrder);
      return apiFetch<FileLogResponse>(`/sync/logs/file?${params.toString()}`);
    },
    enabled: logTab === "file-logs",
    staleTime: 5_000,
    refetchInterval: logTab === "file-logs" ? 5_000 : false,
    refetchOnWindowFocus: logTab === "file-logs",
    placeholderData: { total: 0, items: [] },
  });

  const eventManagementQuery = useQuery<SyncLogResponse>({
    queryKey: ["event-management-logs", showAllEvents],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("limit", "100");
      params.set("order", "desc");
      if (!showAllEvents) {
        for (const status of EVENT_MANAGEMENT_STATUSES) {
          params.append("statuses", status);
        }
      }
      return mapSyncLogResponse(await apiFetch<SyncLogResponseRaw>(`/sync/logs/sync?${params.toString()}`));
    },
    enabled: logTab === "events",
    staleTime: 5_000,
    refetchInterval: logTab === "events" ? 10_000 : false,
    refetchOnWindowFocus: logTab === "events",
    placeholderData: { total: 0, items: [] },
  });

  const fileLogs = fileLogsQuery.data?.items || [];
  const fileLogTotal = fileLogsQuery.data?.total || 0;
  const eventEntries = eventManagementQuery.data?.items || [];
  const eventTotal = eventManagementQuery.data?.total || 0;

  const resetFileLogPage = () => setFileLogPage(1);

  return (
    <section
      className={cn(
        "animate-fade-up",
        logTab === "tasks" || logTab === "events"
          ? "flex min-h-0 flex-col gap-6 lg:h-[calc(100vh-2.5rem)]"
          : "space-y-6"
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-50">日志中心</h2>
          <p className="mt-1 text-xs text-zinc-400">按任务查看当前同步情况、问题事件与系统日志。</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            className={cn("rounded-lg border px-4 py-2 text-xs font-medium transition", logTab === "tasks" ? "border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]" : "border-zinc-700 text-zinc-300 hover:bg-zinc-800")}
            onClick={() => setLogTab("tasks")}
            type="button"
          >
            任务诊断
          </button>
          <button
            className={cn("rounded-lg border px-4 py-2 text-xs font-medium transition", logTab === "file-logs" ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-zinc-700 text-zinc-300 hover:bg-zinc-800")}
            onClick={() => setLogTab("file-logs")}
            type="button"
          >
            系统日志
          </button>
          <button
            className={cn("rounded-lg border px-4 py-2 text-xs font-medium transition", logTab === "events" ? "border-amber-500/40 bg-amber-500/10 text-amber-300" : "border-zinc-700 text-zinc-300 hover:bg-zinc-800")}
            onClick={() => setLogTab("events")}
            type="button"
          >
            事件管理 {conflicts.filter((c) => !c.resolved).length > 0 ? `(${conflicts.filter((c) => !c.resolved).length})` : ""}
          </button>
          <ThemeToggle />
        </div>
      </div>

      {logTab === "tasks" ? (
        <div className="grid min-h-0 flex-1 gap-5 xl:grid-rows-[auto_minmax(0,1fr)]">
          <TaskSelectionPanel
            taskPickerRef={taskPickerRef}
            selectedTask={selectedTask}
            selectedTaskId={selectedTaskId}
            selectedStatus={selectedStatus}
            selectedStateKey={selectedStateKey}
            lastActivityAt={lastActivityAt}
            overviewQueryIsFetching={overviewQuery.isFetching}
            diagnosticsQueryIsFetching={diagnosticsQuery.isFetching}
            taskPickerOpen={taskPickerOpen}
            setTaskPickerOpen={setTaskPickerOpen}
            showAllTasks={showAllTasks}
            setShowAllTasks={setShowAllTasks}
            hiddenTaskCount={hiddenTaskCount}
            focusedTaskCount={focusedTaskCount}
            taskPickerQuery={taskPickerQuery}
            setTaskPickerQuery={setTaskPickerQuery}
            taskPickerOptions={taskPickerOptions}
            selectTask={selectTask}
            refreshDiagnostics={refreshDiagnostics}
          />

          <div className="grid min-h-[560px] gap-4 xl:min-h-0 xl:grid-cols-[minmax(340px,0.82fr)_minmax(0,1.18fr)]">
            <RunHistoryPanel
              selectedTask={selectedTask}
              diagnosticsQueryIsLoading={diagnosticsQuery.isLoading}
              recentRuns={recentRuns}
              activeRunId={activeRunId}
              setSelectedRunId={setSelectedRunId}
              resetEventPage={resetEventPage}
            />

            <TaskDiagnosticsDetailPanel
              selectedTask={selectedTask}
              selectedRun={selectedRun}
              selectedStatus={selectedStatus}
              selectedStateKey={selectedStateKey}
              lastActivityAt={lastActivityAt}
              activeRunId={activeRunId}
              detailTab={detailTab}
              setDetailTab={setDetailTab}
              diagnosticsQueryIsFetching={diagnosticsQuery.isFetching}
              refreshDiagnostics={refreshDiagnostics}
              progress={progress}
              diagnosticCounts={diagnosticCounts}
              currentFile={currentFile}
              runAlert={runAlert}
              selectedProblems={selectedProblems}
              eventFilter={eventFilter}
              setEventFilter={setEventFilter}
              eventSearch={eventSearch}
              setEventSearch={setEventSearch}
              resetEventPage={resetEventPage}
              selectedEventsQueryIsLoading={selectedEventsQuery.isLoading}
              selectedTimelineEntries={selectedTimelineEntries}
              selectedTimelineTotal={selectedTimelineTotal}
              eventPage={eventPage}
              setEventPage={setEventPage}
              eventPageSize={eventPageSize}
              setEventPageSize={setEventPageSize}
            />
          </div>
        </div>
      ) : null}

      {logTab === "file-logs" ? (
        <SystemLogPanel
          query={fileLogsQuery}
          fileLogs={fileLogs}
          fileLogTotal={fileLogTotal}
          fileLogSearch={fileLogSearch}
          setFileLogSearch={setFileLogSearch}
          fileLogLevel={fileLogLevel}
          setFileLogLevel={setFileLogLevel}
          fileLogOrder={fileLogOrder}
          setFileLogOrder={setFileLogOrder}
          fileLogPage={fileLogPage}
          setFileLogPage={setFileLogPage}
          fileLogPageSize={fileLogPageSize}
          setFileLogPageSize={setFileLogPageSize}
          resetFileLogPage={resetFileLogPage}
        />
      ) : null}

      {logTab === "events" ? (
        <EventManagementPanel
          eventEntries={eventEntries}
          eventTotal={eventTotal}
          eventLoading={eventManagementQuery.isLoading}
          eventError={eventManagementQuery.error?.message ?? null}
          eventWarning={eventManagementQuery.data?.warning ?? null}
          showAllEvents={showAllEvents}
          setShowAllEvents={setShowAllEvents}
          refreshEvents={() => eventManagementQuery.refetch()}
          conflicts={conflicts}
          conflictLoading={conflictLoading}
          conflictError={conflictError}
          refreshConflicts={refreshConflicts}
          queueSummary={queueSummary}
          conflictResolutionStates={conflictResolutionStates}
          onResolveConflict={handleResolveConflict}
          conflictActionLabels={CONFLICT_ACTION_LABELS}
        />
      ) : null}
    </section>
  );
}
