import { IconArrowRightLeft, IconCloud, IconFolder } from "../Icons";
import { cn } from "../../lib/utils";

type NewTaskWizardStepIndicatorProps = {
  step: number;
  taskLocalPath: string;
  taskCloudToken: string;
  onSelectStep: (step: number) => void;
};

export function NewTaskWizardStepIndicator({
  step,
  taskLocalPath,
  taskCloudToken,
  onSelectStep,
}: NewTaskWizardStepIndicatorProps) {
  const stepMeta = [
    { num: 1, label: "选择本地目录", icon: IconFolder, done: Boolean(taskLocalPath.trim()) },
    { num: 2, label: "选择云端目录", icon: IconCloud, done: Boolean(taskCloudToken.trim()) },
    { num: 3, label: "配置与确认", icon: IconArrowRightLeft, done: false },
  ];

  return (
    <div className="flex border-b border-zinc-800">
      {stepMeta.map((item) => {
        const isActive = step === item.num;
        const isPast = step > item.num;
        return (
          <button
            key={item.num}
            className={cn(
              "flex flex-1 items-center justify-center gap-2.5 px-4 py-3.5 text-xs font-medium transition",
              isActive
                ? "border-b-2 border-[#3370FF] bg-[#3370FF]/5 text-[#3370FF]"
                : isPast
                  ? "text-emerald-400"
                  : "text-zinc-500"
            )}
            onClick={() => onSelectStep(item.num)}
            type="button"
          >
            <span
              className={cn(
                "flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-bold",
                isActive
                  ? "bg-[#3370FF] text-white"
                  : isPast
                    ? "bg-emerald-500/20 text-emerald-400"
                    : "bg-zinc-800 text-zinc-500"
              )}
            >
              {isPast ? "✓" : item.num}
            </span>
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
