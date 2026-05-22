import { DANGER_STATUSES, EVENT_FILTERS, type EventFilter, WARNING_STATUSES } from "../../lib/eventFilters";
import { formatTimestamp } from "../../lib/formatters";
import { statusLabelMap } from "../../lib/constants";
import { statusTone } from "../../lib/logCenter";
import { StatusPill } from "../StatusPill";
import { IconActivity } from "../Icons";
import { Pagination } from "../Pagination";
import { cn } from "../../lib/utils";
import type { SyncLogEntry } from "../../types";

type TaskDiagnosticsEventsTabProps = {
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

export function TaskDiagnosticsEventsTab({
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
}: TaskDiagnosticsEventsTabProps) {
  return (
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
  );
}
