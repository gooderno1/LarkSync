/* ------------------------------------------------------------------ */
/*  认证 Hook：连接状态、登录、登出                                      */
/* ------------------------------------------------------------------ */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../lib/api";

type AuthStatus = {
  connected: boolean;
  expires_at?: number | null;
  drive_ok?: boolean;
  open_id?: string | null;
  account_name?: string | null;
  device_id?: string | null;
};

export function useAuth() {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery<AuthStatus>({
    queryKey: ["auth-status"],
    queryFn: () => apiFetch<AuthStatus>("/auth/status"),
    retry: false,
    staleTime: 30_000,
  });

  const logoutMutation = useMutation({
    mutationFn: () => apiFetch("/auth/logout", { method: "POST" }),
    onSettled: () => {
      qc.setQueryData<AuthStatus>(["auth-status"], {
        connected: false,
        expires_at: null,
      });
    },
  });

  return {
    connected: data?.connected ?? false,
    driveOk: data?.drive_ok ?? false,
    expiresAt: data?.expires_at ?? null,
    openId: data?.open_id ?? null,
    accountName: data?.account_name ?? null,
    deviceId: data?.device_id ?? null,
    loading: isLoading,
    logout: logoutMutation.mutate,
  };
}
