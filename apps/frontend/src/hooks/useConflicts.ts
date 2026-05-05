/* ------------------------------------------------------------------ */
/*  冲突 Hook：列表 + 解决                                              */
/* ------------------------------------------------------------------ */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../lib/api";
import type { ConflictItem, ConflictResolutionAction } from "../types";

export function useConflicts() {
  const qc = useQueryClient();

  const conflictsQuery = useQuery<ConflictItem[]>({
    queryKey: ["conflicts"],
    queryFn: () => apiFetch<ConflictItem[]>("/conflicts"),
    placeholderData: [],
    staleTime: 30_000,
  });

  const resolveConflictAsync = async ({
    id,
    action,
  }: {
    id: string;
    action: ConflictResolutionAction;
  }) => {
    const result = await apiFetch(`/conflicts/${id}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    await qc.invalidateQueries({ queryKey: ["conflicts"] });
    return result;
  };

  return {
    conflicts: conflictsQuery.data || [],
    conflictLoading: conflictsQuery.isLoading,
    conflictError: conflictsQuery.error?.message ?? null,
    refreshConflicts: () => qc.invalidateQueries({ queryKey: ["conflicts"] }),
    resolveConflictAsync,
  };
}
