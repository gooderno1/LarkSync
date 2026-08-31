import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../lib/api";

export type AutostartStatus = {
  supported: boolean;
  enabled: boolean;
  platform: "windows" | "macos" | "unsupported";
};

export function useAutostart() {
  const queryClient = useQueryClient();
  const query = useQuery<AutostartStatus>({
    queryKey: ["system", "autostart"],
    queryFn: () => apiFetch<AutostartStatus>("/system/autostart"),
    staleTime: 30_000,
  });
  const mutation = useMutation({
    mutationFn: (enabled: boolean) =>
      apiFetch<AutostartStatus>("/system/autostart", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      }),
    onSuccess: (status) => {
      queryClient.setQueryData(["system", "autostart"], status);
    },
  });

  return {
    autostart: query.data,
    autostartLoading: query.isLoading,
    autostartError: query.error?.message ?? null,
    setAutostart: mutation.mutateAsync,
    updatingAutostart: mutation.isPending,
  };
}
