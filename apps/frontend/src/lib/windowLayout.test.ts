import { describe, expect, it } from "vitest";

import { nextWindowLayoutMode } from "./windowLayout";

describe("nextWindowLayoutMode", () => {
  it("uses physical viewport thresholds for the initial mode", () => {
    expect(nextWindowLayoutMode(null, 1080, 720)).toBe("compact");
    expect(nextWindowLayoutMode(null, 1360, 900)).toBe("standard");
    expect(nextWindowLayoutMode(null, 1536, 960)).toBe("wide");
    expect(nextWindowLayoutMode(null, 1600, 740)).toBe("compact");
  });

  it("keeps compact until both exit thresholds are satisfied", () => {
    expect(nextWindowLayoutMode("compact", 1295, 900)).toBe("compact");
    expect(nextWindowLayoutMode("compact", 1400, 775)).toBe("compact");
    expect(nextWindowLayoutMode("compact", 1296, 776)).toBe("standard");
  });

  it("keeps wide inside the hysteresis band", () => {
    expect(nextWindowLayoutMode("wide", 1490, 900)).toBe("wide");
    expect(nextWindowLayoutMode("wide", 1600, 810)).toBe("wide");
    expect(nextWindowLayoutMode("wide", 1483, 900)).toBe("standard");
    expect(nextWindowLayoutMode("wide", 1600, 803)).toBe("standard");
  });
});
