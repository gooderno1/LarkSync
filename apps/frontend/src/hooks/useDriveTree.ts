/* ------------------------------------------------------------------ */
/*  云端目录树 Hook                                                     */
/* ------------------------------------------------------------------ */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetchForAccount } from "../lib/api";
import type { DriveNode } from "../types";
import { useAccounts } from "./useAccounts";

export function useDriveTree(enabled: boolean) {
  const qc = useQueryClient();
  const { activeAccountId } = useAccounts();
  const accountId = activeAccountId || "";

  const treeQuery = useQuery<DriveNode>({
    queryKey: ["drive-tree", accountId],
    queryFn: ({ signal }) => apiFetchForAccount<DriveNode>("/drive/tree", accountId, { signal }),
    enabled: enabled && Boolean(accountId),
    staleTime: 60_000,
  });

  return {
    tree: treeQuery.data ?? null,
    treeLoading: treeQuery.isLoading,
    treeError: treeQuery.error?.message ?? null,
    refreshTree: () => qc.invalidateQueries({ queryKey: ["drive-tree", accountId] }),
  };
}
