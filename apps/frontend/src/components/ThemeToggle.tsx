/* 主题切换图标按钮 — 可在任何页面头部区域复用 */

import { useTheme } from "../hooks/useTheme";
import { IconSun, IconMoon } from "./Icons";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      className="inline-flex items-center justify-center rounded-lg border border-zinc-700 p-2 text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-200"
      onClick={toggle}
      type="button"
      title={theme === "dark" ? "切换明亮模式" : "切换深色模式"}
    >
      {theme === "dark" ? <IconSun className="h-4 w-4" /> : <IconMoon className="h-4 w-4" />}
    </button>
  );
}
