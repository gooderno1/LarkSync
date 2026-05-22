import {
  mdSyncModeLabels,
  modeLabels,
  syncModeSupportsUpload,
  updateModeLabels,
} from "../../lib/constants";
import { cn } from "../../lib/utils";
import { IconArrowDown, IconArrowRightLeft, IconArrowUp } from "../Icons";
import type { CloudSelection } from "../../types";

type NewTaskStrategyStepProps = {
  inputCls: string;
  taskName: string;
  taskLocalPath: string;
  selectedCloud: CloudSelection | null;
  taskSyncMode: string;
  taskUpdateMode: string;
  taskMdSyncMode: "enhanced" | "download_only" | "doc_only";
  taskDeletePolicy: "off" | "safe" | "strict";
  taskDeleteGraceMinutes: string;
  taskEnabled: boolean;
  error: string | null;
  onTaskSyncModeChange: (value: string) => void;
  onTaskUpdateModeChange: (value: string) => void;
  onTaskMdSyncModeChange: (value: "enhanced" | "download_only" | "doc_only") => void;
  onTaskDeletePolicyChange: (value: "off" | "safe" | "strict") => void;
  onTaskDeleteGraceMinutesChange: (value: string) => void;
  onTaskEnabledChange: (value: boolean) => void;
};

export function NewTaskStrategyStep({
  inputCls,
  taskName,
  taskLocalPath,
  selectedCloud,
  taskSyncMode,
  taskUpdateMode,
  taskMdSyncMode,
  taskDeletePolicy,
  taskDeleteGraceMinutes,
  taskEnabled,
  error,
  onTaskSyncModeChange,
  onTaskUpdateModeChange,
  onTaskMdSyncModeChange,
  onTaskDeletePolicyChange,
  onTaskDeleteGraceMinutesChange,
  onTaskEnabledChange,
}: NewTaskStrategyStepProps) {
  const taskUploadEnabled = syncModeSupportsUpload(taskSyncMode);

  return (
    <div className="space-y-5">
      <div>
        <label className="mb-2 block text-xs font-medium text-zinc-400">同步模式</label>
        <div className="grid grid-cols-3 gap-2">
          {[
            { value: "bidirectional", label: "双向同步", Icon: IconArrowRightLeft },
            { value: "download_only", label: "仅下载", Icon: IconArrowDown },
            { value: "upload_only", label: "仅上传", Icon: IconArrowUp },
          ].map(({ value, label, Icon }) => (
            <button
              key={value}
              className={cn(
                "flex flex-col items-center gap-1.5 rounded-xl border p-3.5 transition",
                taskSyncMode === value
                  ? "border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]"
                  : "border-zinc-800 text-zinc-500 hover:border-zinc-700 hover:bg-zinc-800/30"
              )}
              onClick={() => {
                onTaskSyncModeChange(value);
                if (value === "download_only") {
                  onTaskMdSyncModeChange("download_only");
                }
              }}
              type="button"
            >
              <Icon className="h-5 w-5" />
              <span className="text-xs font-medium">{label}</span>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="mb-1.5 block text-xs font-medium text-zinc-400">更新模式</label>
        <div className="grid grid-cols-3 gap-2">
          {[
            { value: "auto", label: "自动", desc: "智能选择" },
            { value: "partial", label: "局部更新", desc: "仅更新变更块" },
            { value: "full", label: "全量覆盖", desc: "完整替换" },
          ].map(({ value, label, desc }) => (
            <button
              key={value}
              className={cn(
                "rounded-xl border p-3 text-center transition",
                taskUpdateMode === value
                  ? "border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]"
                  : "border-zinc-800 text-zinc-500 hover:border-zinc-700 hover:bg-zinc-800/30"
              )}
              onClick={() => onTaskUpdateModeChange(value)}
              type="button"
            >
              <p className="text-xs font-medium">{label}</p>
              <p className="mt-0.5 text-[10px] text-zinc-600">{desc}</p>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="mb-1.5 block text-xs font-medium text-zinc-400">MD 上传模式</label>
        {taskUploadEnabled ? (
          <>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
              {[
                {
                  value: "enhanced",
                  label: "增强 MD 上传",
                  desc: "上传云文档并维护云端 MD 副本",
                },
                {
                  value: "download_only",
                  label: "MD 仅下载",
                  desc: "仅云端下行，不执行本地 MD 上行",
                },
                {
                  value: "doc_only",
                  label: "仅云文档上传",
                  desc: "仅更新云文档，不保留云端 MD 副本",
                },
              ].map(({ value, label, desc }) => (
                <button
                  key={value}
                  className={cn(
                    "rounded-xl border p-3 text-left transition",
                    taskMdSyncMode === value
                      ? "border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]"
                      : "border-zinc-800 text-zinc-500 hover:border-zinc-700 hover:bg-zinc-800/30"
                  )}
                  onClick={() =>
                    onTaskMdSyncModeChange(value as "enhanced" | "download_only" | "doc_only")
                  }
                  type="button"
                >
                  <p className="text-xs font-medium">{label}</p>
                  <p className="mt-0.5 text-[10px] text-zinc-600">{desc}</p>
                </button>
              ))}
            </div>
            {taskMdSyncMode === "doc_only" ? (
              <p className="mt-2 text-[11px] text-amber-300">
                提示：仅云文档上传会经历 Markdown 转换，复杂内容可能存在格式损耗风险。
              </p>
            ) : null}
          </>
        ) : (
          <div className="rounded-xl border border-dashed border-zinc-800 bg-zinc-950/50 px-4 py-3 text-xs text-zinc-500">
            当前任务为仅下载，不会执行任何本地 Markdown 上行，因此无需配置 MD 上传模式。
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">删除同步策略</label>
          <select
            className={inputCls}
            value={taskDeletePolicy}
            onChange={(e) => onTaskDeletePolicyChange(e.target.value as "off" | "safe" | "strict")}
          >
            <option value="off">关闭（不联动）</option>
            <option value="safe">安全模式（宽限后）</option>
            <option value="strict">严格模式（立即）</option>
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">删除宽限（分钟）</label>
          <input
            className={inputCls}
            type="number"
            min="0"
            step="1"
            value={taskDeleteGraceMinutes}
            onChange={(e) => onTaskDeleteGraceMinutesChange(e.target.value)}
            disabled={taskDeletePolicy === "strict"}
          />
        </div>
      </div>

      <label className="flex items-center gap-2.5 text-sm text-zinc-200">
        <input
          type="checkbox"
          checked={taskEnabled}
          onChange={(e) => onTaskEnabledChange(e.target.checked)}
          className="h-4 w-4 accent-[#3370FF]"
        />
        创建后立即启用
      </label>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
        <p className="text-xs font-semibold text-zinc-300">任务摘要</p>
        <div className="mt-3 grid grid-cols-2 gap-y-2 text-xs">
          <span className="text-zinc-500">任务名称</span>
          <span className="truncate text-zinc-200">{taskName || "未命名"}</span>
          <span className="text-zinc-500">本地目录</span>
          <span className="truncate text-zinc-200">{taskLocalPath || "—"}</span>
          <span className="text-zinc-500">云端目录</span>
          <span className="truncate text-zinc-200">{selectedCloud?.path || "—"}</span>
          <span className="text-zinc-500">同步模式</span>
          <span className="text-zinc-200">{modeLabels[taskSyncMode]}</span>
          <span className="text-zinc-500">更新模式</span>
          <span className="text-zinc-200">{updateModeLabels[taskUpdateMode]}</span>
          <span className="text-zinc-500">MD 模式</span>
          <span className="text-zinc-200">
            {taskUploadEnabled ? mdSyncModeLabels[taskMdSyncMode] : "不适用（仅下载）"}
          </span>
          <span className="text-zinc-500">删除策略</span>
          <span className="text-zinc-200">{taskDeletePolicy}</span>
        </div>
      </div>

      {error ? <p className="text-sm text-rose-400">错误：{error}</p> : null}
    </div>
  );
}
