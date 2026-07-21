import { describe, expect, it } from "vitest";

import { getAuthStatusRefetchInterval } from "./useAuth";

describe("useAuth helpers", () => {
  it("polls while disconnected so QR authorization can complete automatically", () => {
    expect(getAuthStatusRefetchInterval(undefined)).toBe(2500);
    expect(getAuthStatusRefetchInterval({ connected: false })).toBe(2500);
  });

  it("keeps polling when the account is connected but drive probe is indeterminate", () => {
    expect(getAuthStatusRefetchInterval({ connected: true })).toBe(5000);
    expect(getAuthStatusRefetchInterval({ connected: true, drive_ok: null })).toBe(5000);
  });

  it("stops polling after drive permission has a definite result", () => {
    expect(getAuthStatusRefetchInterval({ connected: true, drive_ok: true })).toBe(false);
    expect(getAuthStatusRefetchInterval({ connected: true, drive_ok: false })).toBe(false);
  });
});
