/* ------------------------------------------------------------------ */
/*  冲突 Hook：列表 + 解决                                              */
/* ------------------------------------------------------------------ */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../lib/api";
import type { ConflictItem } from "../types";

export function useConflicts() {
  const qc = useQueryClient();

  const conflictsQuery = useQuery<ConflictItem[]>({
    queryKey: ["conflicts"],
    queryFn: () => apiFetch<ConflictItem[]>("/conflicts"),
    placeholderData: [],
    staleTime: 30_000,
  });

  const resolveMutation = useMutation({
    mutationFn: ({
      id,
      action,
    }: {
      id: string;
      action: "use_local" | "use_cloud" | "keep_both";
    }) =>
      apiFetch(`/conflicts/${id}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["conflicts"] });
    },
  });

  return {
    conflicts: conflictsQuery.data || [],
    conflictLoading: conflictsQuery.isLoading,
    conflictError: conflictsQuery.error?.message ?? null,
    refreshConflicts: () => qc.invalidateQueries({ queryKey: ["conflicts"] }),
    resolveConflict: resolveMutation.mutate,
    resolving: resolveMutation.isPending,
  };
}
