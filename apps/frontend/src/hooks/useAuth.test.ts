import { describe, expect, it } from "vitest";

import { getAuthStatusRefetchInterval } from "./useAuth";

describe("useAuth helpers", () => {
  it("polls while disconnected so QR authorization can complete automatically", () => {
    expect(getAuthStatusRefetchInterval(undefined)).toBe(2500);
    expect(getAuthStatusRefetchInterval({ connected: false })).toBe(2500);
  });

  it("stops polling after the account is connected", () => {
    expect(getAuthStatusRefetchInterval({ connected: true })).toBe(false);
  });
});
