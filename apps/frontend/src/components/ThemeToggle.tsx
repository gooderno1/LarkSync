/* 主题切换图标按钮 — 可在任何页面头部区域复用 */

import { useTheme } from "../hooks/useTheme";
import { IconSun, IconMoon } from "./Icons";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-[#bfd8ff] bg-white text-[#3370FF] transition hover:bg-[#eef5ff]"
      onClick={toggle}
      type="button"
      title={theme === "dark" ? "切换明亮模式" : "切换深色模式"}
    >
      {theme === "dark" ? <IconSun className="h-4 w-4" /> : <IconMoon className="h-4 w-4" />}
    </button>
  );
}
