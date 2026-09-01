import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetchForAccount } from "../lib/api";
import type {
  ProblemActionRecord,
  ProblemDetail,
  ProblemItem,
  ProblemSummary,
} from "../types";
import { useAccounts } from "./useAccounts";

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
  const { activeAccountId } = useAccounts();
  const accountId = activeAccountId || "";
  const query = useQuery<ProblemSummary>({
    queryKey: ["problems-summary", accountId],
    queryFn: ({ signal }) => apiFetchForAccount<ProblemSummary>("/problems/summary?refresh=false", accountId, { signal }),
    enabled: enabled && Boolean(accountId),
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
  const { activeAccountId } = useAccounts();
  const accountId = activeAccountId || "";
  const listQuery = useQuery<ProblemListResponse>({
    queryKey: ["problems", accountId, filters],
    queryFn: ({ signal }) => apiFetchForAccount<ProblemListResponse>(buildProblemQuery(filters), accountId, { signal }),
    enabled: enabled && Boolean(accountId),
    staleTime: 5_000,
    refetchInterval: enabled ? 10_000 : false,
  });
  const summaryQuery = useQuery<ProblemSummary>({
    queryKey: ["problems-summary", accountId],
    queryFn: ({ signal }) => apiFetchForAccount<ProblemSummary>("/problems/summary?refresh=false", accountId, { signal }),
    enabled: enabled && Boolean(accountId),
    staleTime: 5_000,
    refetchInterval: enabled ? 10_000 : false,
  });
  const detailQuery = useQuery<ProblemDetail>({
    queryKey: ["problem-detail", accountId, selectedProblemId],
    queryFn: ({ signal }) => apiFetchForAccount<ProblemDetail>(`/problems/${selectedProblemId}`, accountId, { signal }),
    enabled: enabled && Boolean(accountId) && Boolean(selectedProblemId),
    staleTime: 3_000,
  });
  const actionMutation = useMutation({
    mutationFn: ({ problemId, actionKey }: { problemId: string; actionKey: string }) =>
      apiFetchForAccount<ProblemActionRecord>(`/problems/${problemId}/actions`, accountId, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action_key: actionKey }),
      }),
    onSettled: async (_data, _error, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["problems", accountId] }),
        queryClient.invalidateQueries({ queryKey: ["problems-summary", accountId] }),
        queryClient.invalidateQueries({ queryKey: ["problem-detail", accountId, variables.problemId] }),
      ]);
    },
  });
  const verifyMutation = useMutation({
    mutationFn: (problemId: string) =>
      apiFetchForAccount<ProblemItem>(`/problems/${problemId}/verify`, accountId, { method: "POST" }),
    onSettled: async (_data, _error, problemId) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["problems", accountId] }),
        queryClient.invalidateQueries({ queryKey: ["problems-summary", accountId] }),
        queryClient.invalidateQueries({ queryKey: ["problem-detail", accountId, problemId] }),
      ]);
    },
  });
  const ignoreMutation = useMutation({
    mutationFn: ({ problemId, reason }: { problemId: string; reason: string }) =>
      apiFetchForAccount<ProblemItem>(`/problems/${problemId}/ignore`, accountId, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      }),
    onSettled: async (_data, _error, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["problems", accountId] }),
        queryClient.invalidateQueries({ queryKey: ["problems-summary", accountId] }),
        queryClient.invalidateQueries({ queryKey: ["problem-detail", accountId, variables.problemId] }),
      ]);
    },
  });
  const restoreMutation = useMutation({
    mutationFn: (problemId: string) =>
      apiFetchForAccount<ProblemItem>(`/problems/${problemId}/restore`, accountId, { method: "POST" }),
    onSettled: async (_data, _error, problemId) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["problems", accountId] }),
        queryClient.invalidateQueries({ queryKey: ["problems-summary", accountId] }),
        queryClient.invalidateQueries({ queryKey: ["problem-detail", accountId, problemId] }),
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
    ignoreProblem: ignoreMutation.mutateAsync,
    restoreProblem: restoreMutation.mutateAsync,
    lifecyclePending: ignoreMutation.isPending || restoreMutation.isPending,
    refresh: async () => {
      await Promise.all([listQuery.refetch(), summaryQuery.refetch(), detailQuery.refetch()]);
    },
  };
}
