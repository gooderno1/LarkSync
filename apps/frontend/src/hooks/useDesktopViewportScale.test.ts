import { describe, expect, it } from "vitest";

import {
  DESKTOP_DESIGN_HEIGHT,
  DESKTOP_DESIGN_WIDTH,
  calculateDesktopViewportScale,
} from "./useDesktopViewportScale";

describe("desktop viewport scale", () => {
  it("keeps Codex Companion's normal desktop canvas at 1:1", () => {
    expect(DESKTOP_DESIGN_WIDTH).toBe(1360);
    expect(DESKTOP_DESIGN_HEIGHT).toBe(900);
    expect(calculateDesktopViewportScale(1360, 900)).toBe(1);
  });

  it("only scales down when the viewport is smaller than the design canvas", () => {
    expect(calculateDesktopViewportScale(1280, 820)).toBeCloseTo(820 / 900);
    expect(calculateDesktopViewportScale(1080, 720)).toBeCloseTo(1080 / 1360);
  });

  it("does not enlarge the interface in oversized windows", () => {
    expect(calculateDesktopViewportScale(2048, 1104)).toBe(1);
  });
});
