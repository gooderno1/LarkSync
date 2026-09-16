// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";

import { NotificationDrawer } from "./NotificationDrawer";

vi.mock("../hooks/useAccounts", () => ({
  useAccounts: () => ({ activeAccountId: "account-a" }),
}));

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  client.setQueryData(["accounts-summary"], []);
  render(<QueryClientProvider client={client}><NotificationDrawer open onClose={vi.fn()} /></QueryClientProvider>);
  return client;
}

const notification = {
  id: "notification-1", account_id: "account-a", category: "sync_error",
  title: "历史同步失败", body: "通知记录会保留", created_at: 1, read_at: null,
};

it("shows the updated count and read state while refreshing the notification badge", async () => {
  let readAt: number | null = null;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "POST") {
      expect(String(input)).toBe("/notifications/read-all?account_id=account-a");
      expect(new Headers(init.headers).get("X-LarkSync-Account-ID")).toBe("account-a");
      readAt = 10;
      return new Response(JSON.stringify({ updated: 1125 }));
    }
    return new Response(JSON.stringify([{ ...notification, read_at: readAt }]));
  });
  vi.stubGlobal("fetch", fetchMock);
  const client = mount();
  await screen.findByText("未读");
  fireEvent.click(screen.getByRole("button", { name: "全部标为已读" }));
  expect((await screen.findByRole("status")).textContent).toBe("已将 1125 条通知标为已读");
  await screen.findByText("已读");
  expect(screen.getByText("历史同步失败")).toBeTruthy();
  expect(client.getQueryState(["accounts-summary"])?.isInvalidated).toBe(true);
  expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
});

it("shows a failure without hiding unread notifications and allows retry", async () => {
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => (
    init?.method === "POST"
      ? new Response(JSON.stringify({ detail: "数据库暂时忙，请重试" }), { status: 503 })
      : new Response(JSON.stringify([notification]))
  )));
  const client = mount();
  await screen.findByText("历史同步失败");
  fireEvent.click(screen.getByRole("button", { name: "全部标为已读" }));
  expect((await screen.findByRole("alert")).textContent).toContain("数据库暂时忙，请重试");
  expect(screen.getByText("未读")).toBeTruthy();
  expect(screen.queryByRole("status")).toBeNull();
  expect(client.getQueryState(["accounts-summary"])?.isInvalidated).toBe(false);
  await waitFor(() => expect(screen.getByRole("button", { name: "全部标为已读" }).hasAttribute("disabled")).toBe(false));
});
