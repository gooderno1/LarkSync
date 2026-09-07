// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";
import { KeychainAccessBoundary } from "./KeychainAccessBoundary";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><KeychainAccessBoundary><div>同步页面</div></KeychainAccessBoundary></QueryClientProvider>);
  return client;
}

it("does not request authorization automatically and restores the page after explicit retry", async () => {
  let blocked = true;
  const requests: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    requests.push(`${init?.method || "GET"} ${input}`);
    if (String(input).endsWith("/retry")) blocked = false;
    return new Response(JSON.stringify({ supported: true, blocked, retrying: false }));
  }));
  mount();
  const button = await screen.findByRole("button", { name: "重试钥匙串访问" });
  expect(requests).toEqual(["GET /auth/keychain/status"]);
  expect(screen.queryByText("同步页面")).toBeNull();
  fireEvent.click(button);
  await screen.findByText("同步页面");
  expect(requests.filter((value) => value.startsWith("POST"))).toEqual(["POST /auth/keychain/retry"]);
});

it("keeps a cancelled retry visible without retrying automatically", async () => {
  const calls: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    calls.push(String(input));
    if (String(input).endsWith("/retry")) return new Response(JSON.stringify({ detail: "系统授权已取消，请重试" }), { status: 503 });
    return new Response(JSON.stringify({ supported: true, blocked: true, retrying: false }));
  }));
  mount();
  fireEvent.click(await screen.findByRole("button", { name: "重试钥匙串访问" }));
  await screen.findByText("系统授权已取消，请重试");
  await waitFor(() => expect(screen.getByRole("button", { name: "重试钥匙串访问" }).hasAttribute("disabled")).toBe(false));
  expect(calls.filter((value) => value.endsWith("/retry"))).toHaveLength(1);
});

it("shows ordinary content on Windows without a keychain warning", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ supported: false, blocked: false, retrying: false }))));
  const client = mount();
  await act(async () => { await client.refetchQueries(); });
  expect(screen.getByText("同步页面")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "重试钥匙串访问" })).toBeNull();
});
