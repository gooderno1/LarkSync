/* ------------------------------------------------------------------ */
/*  主题 Hook：dark / light 切换，持久化到 localStorage                  */
/* ------------------------------------------------------------------ */

import { useCallback, useEffect, useState } from "react";

type Theme = "dark" | "light";

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window === "undefined") return "light";
    const saved = window.localStorage.getItem("larksync-theme");
    if (saved === "dark" || saved === "light") {
      return saved;
    }
    return "light";
  });

  useEffect(() => {
    if (typeof document === "undefined") return;
    document.documentElement.dataset.theme = theme;
    try {
      window.localStorage.setItem("larksync-theme", theme);
    } catch {
      // ignore
    }
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  return { theme, toggle };
}
