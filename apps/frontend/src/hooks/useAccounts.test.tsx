// @vitest-environment jsdom

import type { ReactNode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AccountProvider, useAccounts } from "./useAccounts";

const accounts = [
  { id: "account-a", account_name: "A", state: "connected", is_active: true },
  { id: "account-b", account_name: "B", state: "connected", is_active: false },
];

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function wrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}><AccountProvider>{children}</AccountProvider></QueryClientProvider>
  );
}

describe("AccountProvider switching transaction", () => {
  beforeEach(() => {
    const values = new Map<string, string>();
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: {
        getItem: (key: string) => values.get(key) ?? null,
        setItem: (key: string, value: string) => values.set(key, String(value)),
        removeItem: (key: string) => values.delete(key),
        clear: () => values.clear(),
      },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("serializes rapid A to B to A switches and keeps the latest account", async () => {
    window.localStorage.setItem("larksync.active-account-id", "account-a");
    let releaseB: (() => void) | undefined;
    const waitForB = new Promise<void>((resolve) => { releaseB = resolve; });
    let backendActive = "account-a";
    const switchCalls: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) === "/accounts/summary") {
        return jsonResponse(accounts.map((account) => ({ ...account, is_active: account.id === backendActive })));
      }
      if (String(input) === "/ui/active-account") {
        const accountId = String(JSON.parse(String(init?.body)).account_id);
        switchCalls.push(accountId);
        if (accountId === "account-b") await waitForB;
        backendActive = accountId;
        return jsonResponse({ active_account_id: accountId });
      }
      return jsonResponse({});
    }));

    const rendered = renderHook(() => useAccounts(), { wrapper: wrapper() });
    await waitFor(() => expect(rendered.result.current.activeAccountId).toBe("account-a"));

    let first!: Promise<void>;
    let second!: Promise<void>;
    act(() => {
      first = rendered.result.current.switchAccount("account-b");
      second = rendered.result.current.switchAccount("account-a");
    });
    releaseB?.();
    await act(async () => { await Promise.all([first, second]); });

    expect(switchCalls).toEqual(["account-b", "account-a"]);
    expect(backendActive).toBe("account-a");
    expect(rendered.result.current.activeAccountId).toBe("account-a");
    expect(window.localStorage.getItem("larksync.active-account-id")).toBe("account-a");
  });

  it("keeps the original account when a switch fails", async () => {
    window.localStorage.setItem("larksync.active-account-id", "account-a");
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input) === "/accounts/summary") return jsonResponse(accounts);
      if (String(input) === "/ui/active-account") return jsonResponse({ detail: "切换失败" }, 500);
      return jsonResponse({});
    }));

    const rendered = renderHook(() => useAccounts(), { wrapper: wrapper() });
    await waitFor(() => expect(rendered.result.current.activeAccountId).toBe("account-a"));
    await expect(rendered.result.current.switchAccount("account-b")).rejects.toThrow("切换失败");

    expect(rendered.result.current.activeAccountId).toBe("account-a");
    expect(window.localStorage.getItem("larksync.active-account-id")).toBe("account-a");
  });
});
