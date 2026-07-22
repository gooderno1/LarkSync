export type WindowLayoutMode = "compact" | "standard" | "wide";

export function nextWindowLayoutMode(
  previous: WindowLayoutMode | null,
  width: number,
  height: number,
): WindowLayoutMode {
  if (previous === "compact") {
    if (width < 1296 || height < 776) return "compact";
    return width >= 1500 && height >= 820 ? "wide" : "standard";
  }
  if (previous === "wide") {
    if (width >= 1484 && height >= 804) return "wide";
    if (width < 1280 || height < 760) return "compact";
    return "standard";
  }
  if (width < 1280 || height < 760) return "compact";
  if (width >= 1500 && height >= 820) return "wide";
  return "standard";
}

export function isLowWindowHeight(height: number): boolean {
  return height < 820;
}
