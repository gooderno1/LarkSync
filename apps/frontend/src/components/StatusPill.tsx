/* ------------------------------------------------------------------ */
/*  状态胶囊组件                                                        */
/* ------------------------------------------------------------------ */

import { cn } from "../lib/utils";
import type { Tone } from "../types";

const toneStyles: Record<Tone, string> = {
  neutral: "border-[#c9d8ec] text-[#52657a] bg-white",
  info: "border-[#3370ff]/25 text-[#1d4ed8] bg-[#eef5ff]",
  success: "border-[#10b981]/25 text-[#047857] bg-[#ecfdf5]",
  warning: "border-[#f59e0b]/30 text-[#b45309] bg-[#fffbeb]",
  danger: "border-[#f43f5e]/30 text-[#be123c] bg-[#fff1f2]",
};

export function StatusPill({
  label,
  tone = "neutral",
  dot = false,
}: {
  label: string;
  tone?: Tone;
  dot?: boolean;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 whitespace-nowrap rounded-full border px-3 py-1 text-xs font-medium",
        toneStyles[tone]
      )}
    >
      {dot ? <span className="h-2 w-2 rounded-full bg-current" /> : null}
      {label}
    </span>
  );
}
