import { useCallback, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "../lib/api";
import {
  buildTaskEventQueryPath,
  shouldPollTaskEventTimeline,
} from "../lib/taskEventTimeline";
import {
  mapSyncLogResponse,
  type SyncLogResponse,
  type SyncLogResponseRaw,
} from "../lib/logCenter";
import type { DetailTab } from "./useLogCenterTaskDiagnostics";
import type { EventFilter } from "../lib/eventFilters";

type UseTaskEventTimelineOptions = {
  enabled: boolean;
  detailTab: DetailTab;
  selectedTaskId: string | null;
  activeRunId: string | null;
  activeRunState?: string | null;
};

export function useTaskEventTimeline({
  enabled,
  detailTab,
  selectedTaskId,
  activeRunId,
  activeRunState,
}: UseTaskEventTimelineOptions) {
  const [eventFilter, setEventFilter] = useState<EventFilter>("all");
  const [eventSearch, setEventSearch] = useState("");
  const [eventPage, setEventPage] = useState(1);
  const [eventPageSize, setEventPageSize] = useState(30);
  const [eventSince, setEventSince] = useState<number | null>(null);
  const [eventUntil, setEventUntil] = useState<number | null>(null);

  const selectedEventsQuery = useQuery<SyncLogResponse>({
    queryKey: [
      "sync-log-task-events",
      selectedTaskId,
      activeRunId,
      detailTab,
      eventFilter,
      eventSearch,
      eventPage,
      eventPageSize,
      eventSince,
      eventUntil,
    ],
    queryFn: async () => {
      const raw = await apiFetch<SyncLogResponseRaw>(
        buildTaskEventQueryPath({
          selectedTaskId,
          activeRunId,
          eventFilter,
          eventSearch,
          eventPage,
          eventPageSize,
          since: eventSince,
          until: eventUntil,
        }),
      );
      return mapSyncLogResponse(raw);
    },
    enabled: enabled && detailTab === "events" && Boolean(selectedTaskId) && Boolean(activeRunId),
    placeholderData: (previousData) => previousData ?? { total: 0, items: [] },
    staleTime: 5_000,
    refetchInterval: shouldPollTaskEventTimeline({
      enabled,
      detailTab,
      activeRunState,
    }),
  });

  useEffect(() => {
    setEventPage(1);
  }, [activeRunId, selectedTaskId]);

  const setEventTimeRange = useCallback((since: number | null, until: number | null = null) => {
    setEventSince(since);
    setEventUntil(until);
    setEventPage(1);
  }, []);

  const selectedTimelineEntries = selectedEventsQuery.data?.items || [];
  const selectedTimelineTotal = selectedEventsQuery.data?.total || 0;

  const resetEventPage = () => setEventPage(1);

  return {
    eventFilter,
    setEventFilter,
    eventSearch,
    setEventSearch,
    eventPage,
    setEventPage,
    eventPageSize,
    setEventPageSize,
    eventSince,
    eventUntil,
    setEventTimeRange,
    selectedEventsQuery,
    selectedTimelineEntries,
    selectedTimelineTotal,
    resetEventPage,
  };
}
