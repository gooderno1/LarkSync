/* ------------------------------------------------------------------ */
/*  同步任务 Hook：CRUD + 状态轮询                                       */
/* ------------------------------------------------------------------ */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../lib/api";
import type { SyncTask, SyncTaskStatus } from "../types";

export function useTasks() {
  const qc = useQueryClient();

  const tasksQuery = useQuery<SyncTask[]>({
    queryKey: ["tasks"],
    queryFn: () => apiFetch<SyncTask[]>("/sync/tasks"),
    placeholderData: [],
    staleTime: 10_000,
  });

  const statusQuery = useQuery<Record<string, SyncTaskStatus>>({
    queryKey: ["task-status"],
    queryFn: async () => {
      const data = await apiFetch<SyncTaskStatus[]>("/sync/tasks/status");
      if (!Array.isArray(data)) return {};
      const mapped: Record<string, SyncTaskStatus> = {};
      for (const item of data) {
        if (item?.task_id) mapped[item.task_id] = item;
      }
      return mapped;
    },
    refetchInterval: tasksQuery.data && tasksQuery.data.length > 0 ? 5000 : false,
    placeholderData: {},
  });

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      apiFetch("/sync/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      qc.invalidateQueries({ queryKey: ["task-status"] });
    },
  });

  const toggleMutation = useMutation({
    mutationFn: (task: SyncTask) =>
      apiFetch(`/sync/tasks/${task.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !task.enabled }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      qc.invalidateQueries({ queryKey: ["task-status"] });
    },
  });

  const updateSyncModeMutation = useMutation({
    mutationFn: ({ id, sync_mode }: { id: string; sync_mode: string }) =>
      apiFetch<SyncTask>(`/sync/tasks/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sync_mode }),
      }),
    onSuccess: (updated: SyncTask) => {
      qc.setQueryData<SyncTask[]>(["tasks"], (prev) =>
        (prev || []).map((t) => (t.id === updated.id ? updated : t))
      );
    },
  });

  const updateModeMutation = useMutation({
    mutationFn: ({ id, update_mode }: { id: string; update_mode: string }) =>
      apiFetch(`/sync/tasks/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ update_mode }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  const runMutation = useMutation({
    mutationFn: (task: SyncTask) =>
      apiFetch(`/sync/tasks/${task.id}/run`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["task-status"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (task: SyncTask) =>
      apiFetch(`/sync/tasks/${task.id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      qc.invalidateQueries({ queryKey: ["task-status"] });
    },
  });

  return {
    tasks: tasksQuery.data || [],
    taskLoading: tasksQuery.isLoading,
    taskError: tasksQuery.error?.message ?? null,
    statusMap: statusQuery.data || {},
    refreshTasks: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
    refreshStatus: () => qc.invalidateQueries({ queryKey: ["task-status"] }),
    createTask: createMutation.mutateAsync,
    toggleTask: toggleMutation.mutate,
    updateSyncMode: updateSyncModeMutation.mutate,
    updateMode: updateModeMutation.mutate,
    runTask: runMutation.mutate,
    deleteTask: deleteMutation.mutate,
    creating: createMutation.isPending,
  };
}
