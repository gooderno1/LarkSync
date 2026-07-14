import { IconArrowRightLeft, IconCloud, IconFolder } from "../Icons";
import { cn } from "../../lib/utils";

type NewTaskWizardStepIndicatorProps = {
  step: number;
  taskLocalPath: string;
  taskCloudToken: string;
  maxAccessibleStep: number;
  onSelectStep: (step: number) => void;
};

export function NewTaskWizardStepIndicator({
  step,
  taskLocalPath,
  taskCloudToken,
  maxAccessibleStep,
  onSelectStep,
}: NewTaskWizardStepIndicatorProps) {
  const stepMeta = [
    { num: 1, label: "选择本地目录", icon: IconFolder, done: Boolean(taskLocalPath.trim()) },
    { num: 2, label: "选择云端目录", icon: IconCloud, done: Boolean(taskCloudToken.trim()) },
    { num: 3, label: "同步模式", icon: IconArrowRightLeft, done: step > 3 },
    { num: 4, label: "删除与忽略", icon: IconFolder, done: step > 4 },
    { num: 5, label: "确认", icon: IconCloud, done: false },
  ];

  return (
    <div className="flex border-b border-[#edf3fb] bg-[#f8fbff]">
      {stepMeta.map((item) => {
        const isActive = step === item.num;
        const isPast = step > item.num;
        const isDisabled = item.num > maxAccessibleStep;
        return (
          <button
            key={item.num}
            aria-current={isActive ? "step" : undefined}
            className={cn(
              "flex flex-1 items-center justify-center gap-2 px-2 py-3 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-45",
              isActive
                ? "border-b-2 border-[#3370ff] bg-[#eef5ff] text-[#3370ff]"
                : isPast
                  ? "text-[#047857]"
                  : "text-[#6b7f96]"
            )}
            onClick={() => onSelectStep(item.num)}
            disabled={isDisabled}
            type="button"
          >
            <span
              className={cn(
                "flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-bold",
                isActive
                  ? "bg-[#3370ff] text-white"
                  : isPast
                    ? "bg-[#ecfdf5] text-[#047857]"
                    : "bg-[#edf3fb] text-[#6b7f96]"
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
