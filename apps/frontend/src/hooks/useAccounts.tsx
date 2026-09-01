import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "../lib/api";
import type { AccountSummary } from "../types";

type AccountContextValue = {
  accounts: AccountSummary[];
  activeAccount: AccountSummary | null;
  activeAccountId: string | null;
  loading: boolean;
  switchingAccountId: string | null;
  switchAccount: (accountId: string) => Promise<void>;
  refreshAccounts: () => Promise<unknown>;
};

const AccountContext = createContext<AccountContextValue | null>(null);
const fallbackAccountContext: AccountContextValue = {
  accounts: [],
  activeAccount: null,
  activeAccountId: null,
  loading: false,
  switchingAccountId: null,
  switchAccount: async () => undefined,
  refreshAccounts: async () => undefined,
};

export function AccountProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const switchQueueRef = useRef<Promise<void>>(Promise.resolve());
  const switchSequenceRef = useRef(0);
  const [switchingAccountId, setSwitchingAccountId] = useState<string | null>(null);
  const [activeAccountId, setActiveAccountId] = useState<string | null>(() => {
    try {
      return window.localStorage.getItem("larksync.active-account-id");
    } catch {
      return null;
    }
  });
  const query = useQuery<AccountSummary[]>({
    queryKey: ["accounts-summary"],
    queryFn: () => apiFetch<AccountSummary[]>("/accounts/summary"),
    retry: false,
    refetchInterval: 10_000,
  });
  const accounts = query.data ?? [];
  const activeAccount =
    accounts.find((item) => item.id === activeAccountId) ??
    accounts.find((item) => item.is_active) ??
    accounts[0] ??
    null;

  useEffect(() => {
    if (!activeAccount) return;
    if (activeAccount.id !== activeAccountId) setActiveAccountId(activeAccount.id);
    try {
      window.localStorage.setItem("larksync.active-account-id", activeAccount.id);
    } catch {
      // localStorage 不可用时由后端活动账户兜底。
    }
  }, [activeAccount, activeAccountId]);

  const switchAccount = useCallback(async (accountId: string) => {
    const sequence = ++switchSequenceRef.current;
    setSwitchingAccountId(accountId);
    const operation = switchQueueRef.current
      .catch(() => undefined)
      .then(async () => {
        const previousAccountId = activeAccountId;
        if (previousAccountId) {
          await queryClient.cancelQueries({
            predicate: (item) => item.queryKey.includes(previousAccountId),
          });
        }
        await apiFetch("/ui/active-account", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ account_id: accountId }),
        });
      });
    switchQueueRef.current = operation.then(() => undefined, () => undefined);
    try {
      await operation;
      if (sequence !== switchSequenceRef.current) return;
      setActiveAccountId(accountId);
      try {
        window.localStorage.setItem("larksync.active-account-id", accountId);
      } catch {
        // 后端偏好已保存。
      }
      await query.refetch();
    } finally {
      if (sequence === switchSequenceRef.current) setSwitchingAccountId(null);
    }
  }, [activeAccountId, query, queryClient]);

  const value: AccountContextValue = {
    accounts,
    activeAccount,
    activeAccountId: activeAccount?.id ?? activeAccountId,
    loading: query.isLoading,
    switchingAccountId,
    switchAccount,
    refreshAccounts: () => query.refetch(),
  };
  return <AccountContext.Provider value={value}>{children}</AccountContext.Provider>;
}

export function useAccounts(): AccountContextValue {
  const value = useContext(AccountContext);
  return value ?? fallbackAccountContext;
}
