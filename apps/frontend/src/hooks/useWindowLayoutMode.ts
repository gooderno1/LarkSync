import { useEffect, useRef, useState } from "react";

import {
  isLowWindowHeight,
  nextWindowLayoutMode,
  type WindowLayoutMode,
} from "../lib/windowLayout";

type WindowLayoutState = {
  mode: WindowLayoutMode;
  lowHeight: boolean;
  physicalWidth: number;
  physicalHeight: number;
};

function readViewport(previous: WindowLayoutMode | null): WindowLayoutState {
  const width = typeof window === "undefined" ? 1360 : window.innerWidth;
  const height = typeof window === "undefined" ? 900 : window.innerHeight;
  return {
    mode: nextWindowLayoutMode(previous, width, height),
    lowHeight: isLowWindowHeight(height),
    physicalWidth: width,
    physicalHeight: height,
  };
}

export function useWindowLayoutMode(): WindowLayoutState {
  const [state, setState] = useState<WindowLayoutState>(() => readViewport(null));
  const modeRef = useRef(state.mode);

  useEffect(() => {
    let timer: number | null = null;
    const settle = () => {
      const next = readViewport(modeRef.current);
      modeRef.current = next.mode;
      setState(next);
    };
    const handleResize = () => {
      if (timer !== null) window.clearTimeout(timer);
      timer = window.setTimeout(settle, 120);
    };
    window.addEventListener("resize", handleResize);
    settle();
    return () => {
      window.removeEventListener("resize", handleResize);
      if (timer !== null) window.clearTimeout(timer);
    };
  }, []);

  return state;
}
