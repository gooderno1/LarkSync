import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "../lib/api";

export type DesktopStatus = {
  runtime: {
    backend_running: boolean;
    frontend_static_available: boolean;
    data_dir: string;
    database_url: string;
    packaged: boolean;
    profile: "production" | "synthetic_test" | "snapshot_test" | "live_readonly" | "live_bidirectional";
    cloud_write_policy: "deny" | "allowlisted" | "normal";
    scheduler_disabled: boolean;
    watcher_disabled: boolean;
  };
  auth: {
    connected: boolean;
    oauth_configured: boolean;
    open_id?: string | null;
    account_name?: string | null;
    device_id: string;
    expires_at?: number | null;
  };
  tasks: {
    total: number;
    enabled: number;
    paused: number;
    running: number;
    failed: number;
    last_error?: string | null;
    last_sync_time?: number | null;
  };
  conflicts: {
    unresolved: number;
  };
  update: {
    current_version: string;
    latest_version?: string | null;
    update_available: boolean;
    last_check?: number | null;
    last_error?: string | null;
    download_path?: string | null;
  };
};

export const desktopStatusPlaceholder: DesktopStatus = {
  runtime: {
    backend_running: true,
    frontend_static_available: false,
    data_dir: "",
    database_url: "",
    packaged: false,
    profile: "production",
    cloud_write_policy: "normal",
    scheduler_disabled: false,
    watcher_disabled: false,
  },
  auth: {
    connected: false,
    oauth_configured: false,
    open_id: null,
    account_name: null,
    device_id: "",
    expires_at: null,
  },
  tasks: {
    total: 0,
    enabled: 0,
    paused: 0,
    running: 0,
    failed: 0,
    last_error: null,
    last_sync_time: null,
  },
  conflicts: {
    unresolved: 0,
  },
  update: {
    current_version: "v0.8.0-dev.1",
    latest_version: null,
    update_available: false,
    last_check: null,
    last_error: null,
    download_path: null,
  },
};

export function useDesktopStatus() {
  const query = useQuery<DesktopStatus>({
    queryKey: ["desktop-status"],
    queryFn: () => apiFetch<DesktopStatus>("/system/desktop/status"),
    staleTime: 5_000,
    refetchInterval: 10_000,
    placeholderData: desktopStatusPlaceholder,
  });

  return {
    status: query.data ?? desktopStatusPlaceholder,
    loading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error?.message ?? null,
    refetch: query.refetch,
  };
}
