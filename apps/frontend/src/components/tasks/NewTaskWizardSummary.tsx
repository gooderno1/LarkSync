import { modeLabels } from "../../lib/constants";
import { getNewTaskRiskLevel } from "../../lib/newTaskWizard";
import { deletePolicyLabel } from "../../lib/taskManagement";
import { cn } from "../../lib/utils";

type NewTaskWizardSummaryProps = {
  taskName: string;
  taskLocalPath: string;
  cloudPath: string;
  taskSyncMode: string;
  taskDeletePolicy: "off" | "safe" | "strict";
  taskEnabled: boolean;
};

export function NewTaskWizardSummary({
  taskName,
  taskLocalPath,
  cloudPath,
  taskSyncMode,
  taskDeletePolicy,
  taskEnabled,
}: NewTaskWizardSummaryProps) {
  const risk = getNewTaskRiskLevel(taskSyncMode, taskDeletePolicy);

  return (
    <aside className="h-fit rounded-xl border border-[#d7e4f5] bg-[#f8fbff] p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-[#102033]">配置摘要</h3>
        <span
          className={cn(
            "rounded-full border px-2.5 py-1 text-[11px] font-semibold",
            risk.tone === "safe" && "border-[#10b981]/30 bg-[#ecfdf5] text-[#047857]",
            risk.tone === "warning" && "border-[#f59e0b]/35 bg-[#fffbeb] text-[#b45309]",
            risk.tone === "danger" && "border-[#f43f5e]/35 bg-[#fff1f2] text-[#be123c]",
          )}
        >
          {risk.label}
        </span>
      </div>
      <dl className="mt-4 space-y-3 text-xs">
        {[
          ["任务名称", taskName.trim() || "未命名任务"],
          ["本地目录", taskLocalPath.trim() || "待选择"],
          ["云端目录", cloudPath || "待选择"],
          ["同步模式", modeLabels[taskSyncMode] || taskSyncMode],
          ["删除策略", deletePolicyLabel(taskDeletePolicy)],
          ["创建后", taskEnabled ? "立即启用" : "保持停用"],
        ].map(([label, value]) => (
          <div key={label} className="grid grid-cols-[64px_minmax(0,1fr)] gap-3">
            <dt className="text-[#6b7f96]">{label}</dt>
            <dd className="truncate text-right font-medium text-[#102033]" title={value}>{value}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-4 border-t border-[#d7e4f5] pt-3 text-[11px] leading-5 text-[#52657a]">
        {taskDeletePolicy === "strict"
          ? "严格删除会立即联动删除，请在创建前确认目录范围。"
          : taskSyncMode === "download_only"
            ? "仅下载不会把本地改动上传到云端，适合作为首次同步。"
            : "该模式允许写入云端；冲突时仍遵循云端优先并保留副本。"}
      </div>
    </aside>
  );
}
