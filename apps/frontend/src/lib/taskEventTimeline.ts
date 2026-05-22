import { buildStatusParams, type EventFilter } from "./eventFilters";

type BuildTaskEventQueryPathOptions = {
  selectedTaskId: string | null;
  activeRunId: string | null;
  eventFilter: EventFilter;
  eventSearch: string;
  eventPage: number;
  eventPageSize: number;
};

export function buildTaskEventQueryPath({
  selectedTaskId,
  activeRunId,
  eventFilter,
  eventSearch,
  eventPage,
  eventPageSize,
}: BuildTaskEventQueryPathOptions): string {
  const params = new URLSearchParams();
  params.set("limit", String(eventPageSize));
  params.set("offset", String((eventPage - 1) * eventPageSize));
  params.set("order", "desc");
  if (selectedTaskId) params.append("task_ids", selectedTaskId);
  if (activeRunId) params.append("run_ids", activeRunId);
  for (const status of buildStatusParams(eventFilter)) {
    params.append("statuses", status);
  }
  const trimmedSearch = eventSearch.trim();
  if (trimmedSearch) params.set("search", trimmedSearch);
  return `/sync/logs/sync?${params.toString()}`;
}

export function shouldPollTaskEventTimeline(options: {
  enabled: boolean;
  detailTab: "overview" | "problems" | "events";
  activeRunState?: string | null;
}): number | false {
  return options.enabled && options.detailTab === "events" && options.activeRunState === "running"
    ? 5_000
    : false;
}
