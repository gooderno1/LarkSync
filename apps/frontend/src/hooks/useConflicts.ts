/* ------------------------------------------------------------------ */
/*  冲突 Hook：列表 + 解决                                              */
/* ------------------------------------------------------------------ */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetchForAccount } from "../lib/api";
import type { ConflictItem, ConflictResolutionAction } from "../types";
import { useAccounts } from "./useAccounts";

export function useConflicts(enabled = true) {
  const qc = useQueryClient();
  const { activeAccountId } = useAccounts();
  const accountId = activeAccountId || "";

  const conflictsQuery = useQuery<ConflictItem[]>({
    queryKey: ["conflicts", accountId],
    queryFn: ({ signal }) => apiFetchForAccount<ConflictItem[]>("/conflicts", accountId, { signal }),
    enabled: enabled && Boolean(accountId),
    staleTime: 30_000,
  });

  const resolveConflictAsync = async ({
    id,
    action,
  }: {
    id: string;
    action: ConflictResolutionAction;
  }) => {
    const result = await apiFetchForAccount(`/conflicts/${id}/resolve`, accountId, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    await qc.invalidateQueries({ queryKey: ["conflicts", accountId] });
    return result;
  };

  return {
    conflicts: conflictsQuery.data || [],
    conflictLoading: conflictsQuery.isLoading,
    conflictError: conflictsQuery.error?.message ?? null,
    refreshConflicts: () => qc.invalidateQueries({ queryKey: ["conflicts", accountId] }),
    resolveConflictAsync,
  };
}
