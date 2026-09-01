import { cn } from "../../lib/utils";

type SwitchProps = {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  label: string;
  disabled?: boolean;
  size?: "sm" | "md";
  className?: string;
};

export function Switch({
  checked,
  onCheckedChange,
  label,
  disabled = false,
  size = "md",
  className,
}: SwitchProps) {
  const compact = size === "sm";
  return (
    <button
      type="button"
      role="switch"
      aria-label={label}
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onCheckedChange(!checked)}
      className={cn(
        "inline-flex shrink-0 items-center rounded-full border p-0.5 shadow-inner transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3370ff]/35 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60",
        compact ? "h-5 w-9" : "h-6 w-11",
        checked ? "border-[#3370ff] bg-[#3370ff]" : "border-[#afc1d5] bg-[#c9d8ec]",
        className,
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          "block rounded-full bg-white shadow-sm transition-transform",
          compact ? "h-3.5 w-3.5" : "h-5 w-5",
          checked ? (compact ? "translate-x-4" : "translate-x-5") : "translate-x-0",
        )}
      />
    </button>
  );
}
