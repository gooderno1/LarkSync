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

export type UpdateInstallResponse = {
  queued: boolean;
  installer_path: string;
  silent: boolean;
  restart_path?: string | null;
};

export type UpdateFolderResponse = {
  path: string;
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

  const installMutation = useMutation({
    mutationFn: (downloadPath?: string | null) =>
      apiFetch<UpdateInstallResponse>("/system/update/install", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ download_path: downloadPath || null, silent: true }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["update-status"] }),
  });

  const openFolderMutation = useMutation({
    mutationFn: (downloadPath?: string | null) =>
      apiFetch<UpdateFolderResponse>("/system/update/open-download-folder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ download_path: downloadPath || null }),
      }),
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
    installUpdate: installMutation.mutateAsync,
    installing: installMutation.isPending,
    openUpdateFolder: openFolderMutation.mutateAsync,
    openingUpdateFolder: openFolderMutation.isPending,
    checkError: checkMutation.error?.message ?? null,
    downloadError: downloadMutation.error?.message ?? null,
    installError: installMutation.error?.message ?? null,
    openFolderError: openFolderMutation.error?.message ?? null,
  };
}
