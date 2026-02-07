/* ------------------------------------------------------------------ */
/*  仪表盘统计卡片                                                      */
/* ------------------------------------------------------------------ */

import type { ReactNode } from "react";
import { cn } from "../lib/utils";
import type { Tone } from "../types";

const toneStyles: Record<Tone, string> = {
  neutral: "border-zinc-700/70",
  info: "border-blue-500/40",
  success: "border-emerald-500/40",
  warning: "border-amber-500/40",
  danger: "border-rose-500/40",
};

export function StatCard({
  label,
  value,
  hint,
  tone = "neutral",
  icon,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: Tone;
  icon?: ReactNode;
}) {
  return (
    <div className={cn("rounded-2xl border bg-zinc-900/60 p-4", toneStyles[tone])}>
      <div className="flex items-center justify-between">
        <p className="text-xs uppercase tracking-widest text-zinc-400">{label}</p>
        {icon ? <span className="text-zinc-400">{icon}</span> : null}
      </div>
      <p className="mt-3 text-2xl font-semibold text-zinc-50">{value}</p>
      {hint ? <p className="mt-2 text-xs text-zinc-400">{hint}</p> : null}
    </div>
  );
}
