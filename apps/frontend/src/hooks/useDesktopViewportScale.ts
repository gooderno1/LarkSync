import { useEffect, useState } from "react";
import type { CSSProperties } from "react";

export const DESKTOP_DESIGN_WIDTH = 1536;
export const DESKTOP_DESIGN_HEIGHT = 1024;
export const DESKTOP_MIN_SCALE = 1080 / DESKTOP_DESIGN_WIDTH;

function readViewportScale(): number {
  if (typeof window === "undefined") return 1;
  const width = Number(window.innerWidth) || DESKTOP_DESIGN_WIDTH;
  const height = Number(window.innerHeight) || DESKTOP_DESIGN_HEIGHT;
  const scale = Math.min(width / DESKTOP_DESIGN_WIDTH, height / DESKTOP_DESIGN_HEIGHT);
  if (!Number.isFinite(scale) || scale <= 0) return 1;
  return Math.max(DESKTOP_MIN_SCALE, scale);
}

export function useDesktopViewportScale() {
  const [scale, setScale] = useState(readViewportScale);

  useEffect(() => {
    let frame = 0;
    const updateScale = () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => setScale(readViewportScale()));
    };

    updateScale();
    window.addEventListener("resize", updateScale);
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", updateScale);
    };
  }, []);

  const viewportStyle: CSSProperties = {
    width: "100vw",
    height: "100vh",
  };

  const canvasStyle: CSSProperties & { "--desktop-scale": number } = {
    width: `calc(100vw / ${scale})`,
    height: `calc(100vh / ${scale})`,
    transform: `scale(${scale})`,
    transformOrigin: "top left",
    "--desktop-scale": scale,
  };

  return {
    scale,
    viewportStyle,
    canvasStyle,
  };
}
