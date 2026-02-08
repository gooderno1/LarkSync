/* ------------------------------------------------------------------ */
/*  更新检查 Hook                                                     */
/* ------------------------------------------------------------------ */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../lib/api";

export type UpdateStatus = {
  current_version?: string;
  latest_version?: string | null;
  update_available?: boolean;
  channel?: string;
  notes?: string | null;
  published_at?: string | null;
  asset?: { name: string; url: string; size?: number } | null;
  last_check?: number | null;
  last_error?: string | null;
  download_path?: string | null;
};

export function useUpdate() {
  const qc = useQueryClient();

  const statusQuery = useQuery<UpdateStatus>({
    queryKey: ["update-status"],
    queryFn: () => apiFetch<UpdateStatus>("/system/update/status"),
    staleTime: 30_000,
    placeholderData: {},
  });

  const checkMutation = useMutation({
    mutationFn: () => apiFetch<UpdateStatus>("/system/update/check", { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["update-status"] }),
  });

  const downloadMutation = useMutation({
    mutationFn: () => apiFetch<UpdateStatus>("/system/update/download", { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["update-status"] }),
  });

  return {
    status: statusQuery.data || {},
    loading: statusQuery.isLoading,
    error: statusQuery.error?.message ?? null,
    refetchStatus: () => qc.invalidateQueries({ queryKey: ["update-status"] }),
    checkUpdate: checkMutation.mutateAsync,
    checking: checkMutation.isPending,
    downloadUpdate: downloadMutation.mutateAsync,
    downloading: downloadMutation.isPending,
    checkError: checkMutation.error?.message ?? null,
    downloadError: downloadMutation.error?.message ?? null,
  };
}
