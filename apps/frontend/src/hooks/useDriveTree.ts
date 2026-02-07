/* ------------------------------------------------------------------ */
/*  云端目录树 Hook                                                     */
/* ------------------------------------------------------------------ */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../lib/api";
import type { DriveNode } from "../types";

export function useDriveTree(enabled: boolean) {
  const qc = useQueryClient();

  const treeQuery = useQuery<DriveNode>({
    queryKey: ["drive-tree"],
    queryFn: () => apiFetch<DriveNode>("/drive/tree"),
    enabled,
    staleTime: 60_000,
  });

  return {
    tree: treeQuery.data ?? null,
    treeLoading: treeQuery.isLoading,
    treeError: treeQuery.error?.message ?? null,
    refreshTree: () => qc.invalidateQueries({ queryKey: ["drive-tree"] }),
  };
}
