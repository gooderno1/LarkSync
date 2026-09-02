import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "../lib/api";
import type { AppProfile } from "../types";

export function useAppProfiles() {
  const query = useQuery<AppProfile[]>({
    queryKey: ["app-profiles"],
    queryFn: () => apiFetch<AppProfile[]>("/app-profiles"),
  });

  return {
    profiles: query.data ?? [],
    loading: query.isLoading,
    refreshProfiles: () => query.refetch(),
  };
}
