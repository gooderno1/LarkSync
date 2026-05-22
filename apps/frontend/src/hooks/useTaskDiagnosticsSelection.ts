import { useEffect, useMemo, useState } from "react";

import type { SyncTaskOverview } from "../types";
import {
  filterTaskPickerOptions,
  resolveSelectedTaskId,
} from "../lib/taskDiagnosticsSelection";

type UseTaskDiagnosticsSelectionOptions = {
  sortedOverviews: SyncTaskOverview[];
};

export function useTaskDiagnosticsSelection({
  sortedOverviews,
}: UseTaskDiagnosticsSelectionOptions) {
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [taskPickerQuery, setTaskPickerQuery] = useState("");
  const [taskPickerOpen, setTaskPickerOpen] = useState(false);

  useEffect(() => {
    const resolvedTaskId = resolveSelectedTaskId(sortedOverviews, selectedTaskId);
    if (resolvedTaskId !== selectedTaskId) {
      setSelectedTaskId(resolvedTaskId);
    }
    if (resolvedTaskId === null && selectedRunId !== null) {
      setSelectedRunId(null);
    }
  }, [selectedRunId, selectedTaskId, sortedOverviews]);

  useEffect(() => {
    if (!taskPickerOpen) {
      setTaskPickerQuery("");
    }
  }, [taskPickerOpen]);

  const selectedOverview = useMemo(
    () => sortedOverviews.find((overview) => overview.task.id === selectedTaskId) || null,
    [selectedTaskId, sortedOverviews],
  );

  const taskPickerOptions = useMemo(
    () => filterTaskPickerOptions(sortedOverviews, taskPickerQuery),
    [sortedOverviews, taskPickerQuery],
  );

  const selectTask = (taskId: string) => {
    setSelectedTaskId(taskId);
  };

  return {
    selectedTaskId,
    setSelectedTaskId,
    selectedRunId,
    setSelectedRunId,
    taskPickerQuery,
    setTaskPickerQuery,
    taskPickerOpen,
    setTaskPickerOpen,
    selectedOverview,
    taskPickerOptions,
    selectTask,
  };
}
