/* ------------------------------------------------------------------ */
/*  仪表盘统计卡片                                                      */
/* ------------------------------------------------------------------ */

import type { ReactNode } from "react";
import { cn } from "../lib/utils";
import type { Tone } from "../types";

const toneStyles: Record<Tone, string> = {
  neutral: "border-[#d7e4f5]",
  info: "border-[#d7e4f5]",
  success: "border-[#d7e4f5]",
  warning: "border-[#d7e4f5]",
  danger: "border-[#d7e4f5]",
};

const iconStyles: Record<Tone, string> = {
  neutral: "bg-[#edf5ff] text-[#3370ff]",
  info: "bg-[#e9f1ff] text-[#3370ff]",
  success: "bg-[#ecfdf5] text-[#10b981]",
  warning: "bg-[#fff7ed] text-[#f59e0b]",
  danger: "bg-[#fff1f2] text-[#f43f5e]",
};

const plainIconStyles: Record<Tone, string> = {
  neutral: "text-[#3370ff]",
  info: "text-[#3370ff]",
  success: "text-[#10b981]",
  warning: "text-[#f59e0b]",
  danger: "text-[#f43f5e]",
};

const valueStyles: Record<Tone, string> = {
  neutral: "text-[#102033]",
  info: "text-[#3370ff]",
  success: "text-[#10b981]",
  warning: "text-[#f59e0b]",
  danger: "text-[#f43f5e]",
};

export function StatCard({
  label,
  value,
  hint,
  tone = "neutral",
  icon,
  iconFrame = "circle",
  valueClassName,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: Tone;
  icon?: ReactNode;
  iconFrame?: "circle" | "plain";
  valueClassName?: string;
}) {
  const iconFrameClassName =
    iconFrame === "plain"
      ? cn("grid h-16 w-16 shrink-0 place-items-center", plainIconStyles[tone])
      : cn("grid h-14 w-14 shrink-0 place-items-center rounded-full", iconStyles[tone]);

  return (
    <div
      className={cn(
        "flex min-h-[146px] items-center rounded-lg border bg-white px-5 py-5 shadow-[0_8px_22px_rgba(51,112,255,0.03)]",
        iconFrame === "plain" ? "gap-3" : "gap-4",
        toneStyles[tone]
      )}
    >
      <div className={iconFrameClassName}>{icon}</div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-medium text-[#52657a]">{label}</p>
        <p
          className={cn(
            "mt-2 whitespace-nowrap font-semibold leading-none",
            "text-[24px]",
            valueStyles[tone],
            valueClassName
          )}
          title={value}
        >
          {value}
        </p>
        {hint ? (
          <p className="mt-3 line-clamp-2 text-[11px] leading-4 text-[#6b7f96]" title={hint}>
            {hint}
          </p>
        ) : null}
      </div>
    </div>
  );
}
