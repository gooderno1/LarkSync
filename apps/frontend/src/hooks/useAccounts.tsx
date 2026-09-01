import { createContext, useContext, useEffect } from "react";
import type { ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "../lib/api";
import type { AccountSummary } from "../types";

type AccountContextValue = {
  accounts: AccountSummary[];
  activeAccount: AccountSummary | null;
  activeAccountId: string | null;
  loading: boolean;
  switchAccount: (accountId: string) => Promise<void>;
  refreshAccounts: () => Promise<unknown>;
};

const AccountContext = createContext<AccountContextValue | null>(null);
const fallbackAccountContext: AccountContextValue = {
  accounts: [],
  activeAccount: null,
  activeAccountId: null,
  loading: false,
  switchAccount: async () => undefined,
  refreshAccounts: async () => undefined,
};

export function AccountProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const query = useQuery<AccountSummary[]>({
    queryKey: ["accounts-summary"],
    queryFn: () => apiFetch<AccountSummary[]>("/accounts/summary"),
    retry: false,
    refetchInterval: 10_000,
  });
  const accounts = query.data ?? [];
  let storedId: string | null = null;
  try {
    storedId = window.localStorage.getItem("larksync.active-account-id");
  } catch {
    storedId = null;
  }
  const activeAccount =
    accounts.find((item) => item.id === storedId) ??
    accounts.find((item) => item.is_active) ??
    accounts[0] ??
    null;

  useEffect(() => {
    if (!activeAccount) return;
    try {
      window.localStorage.setItem("larksync.active-account-id", activeAccount.id);
    } catch {
      // localStorage 不可用时由后端活动账户兜底。
    }
  }, [activeAccount]);

  const switchMutation = useMutation({
    mutationFn: async (accountId: string) => {
      await apiFetch("/ui/active-account", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ account_id: accountId }),
      });
      try {
        window.localStorage.setItem("larksync.active-account-id", accountId);
      } catch {
        // 后端偏好已保存。
      }
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries();
    },
  });

  const value: AccountContextValue = {
    accounts,
    activeAccount,
    activeAccountId: activeAccount?.id ?? null,
    loading: query.isLoading,
    switchAccount: switchMutation.mutateAsync,
    refreshAccounts: () => query.refetch(),
  };
  return <AccountContext.Provider value={value}>{children}</AccountContext.Provider>;
}

export function useAccounts(): AccountContextValue {
  const value = useContext(AccountContext);
  return value ?? fallbackAccountContext;
}
