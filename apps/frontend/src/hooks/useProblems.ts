import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "../lib/api";
import type {
  ProblemActionRecord,
  ProblemDetail,
  ProblemItem,
  ProblemSummary,
} from "../types";

export type ProblemFilters = {
  state: string;
  categories: string[];
  severities: string[];
  taskId: string;
  search: string;
  since: number | null;
  offset: number;
  limit: number;
};

type ProblemListResponse = {
  total: number;
  items: ProblemItem[];
};

export function buildProblemQuery(filters: ProblemFilters): string {
  const params = new URLSearchParams({
    state: filters.state,
    task_id: filters.taskId,
    search: filters.search,
    offset: String(filters.offset),
    limit: String(filters.limit),
  });
  for (const category of filters.categories) params.append("categories", category);
  for (const severity of filters.severities) params.append("severities", severity);
  if (filters.since !== null) params.set("since", String(filters.since));
  params.set("refresh", "false");
  return `/problems?${params.toString()}`;
}

export function useProblemSummary(enabled = true) {
  const query = useQuery<ProblemSummary>({
    queryKey: ["problems-summary"],
    queryFn: () => apiFetch<ProblemSummary>("/problems/summary?refresh=false"),
    enabled,
    placeholderData: (previous) => previous,
    staleTime: 5_000,
    refetchInterval: enabled ? 10_000 : false,
  });
  return {
    summary: query.data,
    error: query.error?.message ?? null,
  };
}

export function useProblems(
  filters: ProblemFilters,
  selectedProblemId: string | null,
  enabled = true,
) {
  const queryClient = useQueryClient();
  const listQuery = useQuery<ProblemListResponse>({
    queryKey: ["problems", filters],
    queryFn: () => apiFetch<ProblemListResponse>(buildProblemQuery(filters)),
    enabled,
    placeholderData: (previous) => previous,
    staleTime: 5_000,
    refetchInterval: enabled ? 10_000 : false,
  });
  const summaryQuery = useQuery<ProblemSummary>({
    queryKey: ["problems-summary"],
    queryFn: () => apiFetch<ProblemSummary>("/problems/summary?refresh=false"),
    enabled,
    placeholderData: (previous) => previous,
    staleTime: 5_000,
    refetchInterval: enabled ? 10_000 : false,
  });
  const detailQuery = useQuery<ProblemDetail>({
    queryKey: ["problem-detail", selectedProblemId],
    queryFn: () => apiFetch<ProblemDetail>(`/problems/${selectedProblemId}`),
    enabled: enabled && Boolean(selectedProblemId),
    placeholderData: (previous) => previous,
    staleTime: 3_000,
  });
  const actionMutation = useMutation({
    mutationFn: ({ problemId, actionKey }: { problemId: string; actionKey: string }) =>
      apiFetch<ProblemActionRecord>(`/problems/${problemId}/actions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action_key: actionKey }),
      }),
    onSettled: async (_data, _error, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["problems"] }),
        queryClient.invalidateQueries({ queryKey: ["problems-summary"] }),
        queryClient.invalidateQueries({ queryKey: ["problem-detail", variables.problemId] }),
      ]);
    },
  });
  const verifyMutation = useMutation({
    mutationFn: (problemId: string) =>
      apiFetch<ProblemItem>(`/problems/${problemId}/verify`, { method: "POST" }),
    onSettled: async (_data, _error, problemId) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["problems"] }),
        queryClient.invalidateQueries({ queryKey: ["problems-summary"] }),
        queryClient.invalidateQueries({ queryKey: ["problem-detail", problemId] }),
      ]);
    },
  });

  return {
    problems: listQuery.data?.items ?? [],
    total: listQuery.data?.total ?? 0,
    summary: summaryQuery.data,
    detail: detailQuery.data?.problem.id === selectedProblemId ? detailQuery.data : null,
    loading: listQuery.isLoading,
    fetching: listQuery.isFetching || summaryQuery.isFetching,
    error: listQuery.error?.message ?? summaryQuery.error?.message ?? null,
    detailLoading: detailQuery.isLoading,
    detailError: detailQuery.error?.message ?? null,
    executeAction: actionMutation.mutateAsync,
    actionPending: actionMutation.isPending,
    verifyProblem: verifyMutation.mutateAsync,
    verifyPending: verifyMutation.isPending,
    refresh: async () => {
      await Promise.all([listQuery.refetch(), summaryQuery.refetch(), detailQuery.refetch()]);
    },
  };
}
