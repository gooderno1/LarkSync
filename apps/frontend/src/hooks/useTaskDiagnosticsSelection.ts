import { useEffect, useMemo, useState } from "react";

import type { SyncTaskOverview } from "../types";
import {
  filterTaskPickerOptions,
  getFocusedTaskOverviews,
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
  const [showAllTasks, setShowAllTasks] = useState(false);

  const focusedOverviews = useMemo(
    () => getFocusedTaskOverviews(sortedOverviews),
    [sortedOverviews],
  );
  const hasHiddenTasks = focusedOverviews.length > 0 && focusedOverviews.length < sortedOverviews.length;
  const visibleOverviews = showAllTasks || !hasHiddenTasks ? sortedOverviews : focusedOverviews;

  useEffect(() => {
    const resolvedTaskId = resolveSelectedTaskId(visibleOverviews, selectedTaskId);
    if (resolvedTaskId !== selectedTaskId) {
      setSelectedTaskId(resolvedTaskId);
    }
    if (resolvedTaskId === null && selectedRunId !== null) {
      setSelectedRunId(null);
    }
  }, [selectedRunId, selectedTaskId, visibleOverviews]);

  useEffect(() => {
    if (!taskPickerOpen) {
      setTaskPickerQuery("");
    }
  }, [taskPickerOpen]);

  const selectedOverview = useMemo(
    () => visibleOverviews.find((overview) => overview.task.id === selectedTaskId) || null,
    [selectedTaskId, visibleOverviews],
  );

  const taskPickerOptions = useMemo(
    () => filterTaskPickerOptions(visibleOverviews, taskPickerQuery),
    [visibleOverviews, taskPickerQuery],
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
    showAllTasks,
    setShowAllTasks,
    hiddenTaskCount: Math.max(0, sortedOverviews.length - visibleOverviews.length),
    focusedTaskCount: focusedOverviews.length,
    selectedOverview,
    taskPickerOptions,
    selectTask,
  };
}
