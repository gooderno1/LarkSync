/* ------------------------------------------------------------------ */
/*  状态胶囊组件                                                        */
/* ------------------------------------------------------------------ */

import { cn } from "../lib/utils";
import type { Tone } from "../types";

const toneStyles: Record<Tone, string> = {
  neutral: "border-zinc-700 text-zinc-300 bg-zinc-800/50",
  info: "border-blue-500/40 text-blue-300 bg-blue-500/15",
  success: "border-emerald-500/40 text-emerald-300 bg-emerald-500/15",
  warning: "border-amber-500/40 text-amber-300 bg-amber-500/15",
  danger: "border-rose-500/40 text-rose-300 bg-rose-500/15",
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
        "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium",
        toneStyles[tone]
      )}
    >
      {dot ? <span className="h-2 w-2 rounded-full bg-current" /> : null}
      {label}
    </span>
  );
}
