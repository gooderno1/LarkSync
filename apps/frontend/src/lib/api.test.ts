import { afterEach, describe, expect, it, vi } from "vitest";

import { apiFetch, getCurrentAppUrl, getLoginUrl } from "./api";

describe("api helpers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("preserves the current hash route in OAuth login redirects", () => {
    vi.stubGlobal("window", {
      location: {
        href: "http://127.0.0.1:3666/#settings",
      },
    });

    expect(getCurrentAppUrl()).toBe("http://127.0.0.1:3666/#settings");
    expect(getLoginUrl()).toBe(
      "/auth/login?redirect=http%3A%2F%2F127.0.0.1%3A3666%2F%23settings"
    );
  });

  it("falls back to the auth endpoint outside a browser window", () => {
    expect(getCurrentAppUrl()).toBe("");
    expect(getLoginUrl()).toBe("/auth/login");
  });

  it("binds every scoped request to the active account", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("window", {
      localStorage: { getItem: () => "account-a" },
    });
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/sync/tasks");

    const request = fetchMock.mock.calls[0][1] as RequestInit;
    expect(new Headers(request.headers).get("X-LarkSync-Account-ID")).toBe("account-a");
  });
});
