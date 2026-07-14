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
  view?: "all" | "mode" | "rules" | "confirm";
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
  view = "all",
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
    <div className="space-y-3">
      {view === "all" || view === "mode" ? (
        <>
      <div>
        <label className="mb-2 block text-xs font-medium text-[#52657a]">同步模式</label>
        <div className="grid grid-cols-3 gap-2">
          {[
            { value: "download_only", label: "仅下载", desc: "推荐首次使用", Icon: IconArrowDown },
            { value: "bidirectional", label: "双向同步", desc: "本地与云端互相更新", Icon: IconArrowRightLeft },
            { value: "upload_only", label: "仅上传", desc: "以本地内容为输入", Icon: IconArrowUp },
          ].map(({ value, label, desc, Icon }) => (
            <button
              key={value}
              className={cn(
                "flex min-h-[112px] flex-col items-start gap-2 rounded-xl border p-4 text-left transition",
                taskSyncMode === value
                  ? "border-[#3370ff]/45 bg-[#eef5ff] text-[#3370ff]"
                  : "border-[#d7e4f5] bg-white text-[#6b7f96] hover:border-[#bfd8ff] hover:bg-[#f6faff]"
              )}
              onClick={() => {
                onTaskSyncModeChange(value);
                if (value === "download_only") {
                  onTaskMdSyncModeChange("download_only");
                } else if (taskMdSyncMode === "download_only") {
                  onTaskMdSyncModeChange("enhanced");
                }
              }}
              type="button"
            >
              <Icon className="h-5 w-5" />
              <span className="text-sm font-semibold">{label}</span>
              <span className="text-xs leading-5 text-[#6b7f96]">{desc}</span>
            </button>
          ))}
        </div>
      </div>

      <details className="rounded-lg border border-[#d7e4f5] bg-[#f8fbff] p-3">
        <summary className="cursor-pointer text-xs font-semibold text-[#3370ff]">高级同步选项</summary>
        <div className="mt-3 space-y-3">
      <div>
        <label className="mb-1.5 block text-xs font-medium text-[#52657a]">更新模式</label>
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
                  ? "border-[#3370ff]/45 bg-[#eef5ff] text-[#3370ff]"
                  : "border-[#d7e4f5] bg-white text-[#6b7f96] hover:border-[#bfd8ff] hover:bg-[#f6faff]"
              )}
              onClick={() => onTaskUpdateModeChange(value)}
              type="button"
            >
              <p className="text-xs font-medium">{label}</p>
              <p className="mt-0.5 text-[10px] text-[#7a8da3]">{desc}</p>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="mb-1.5 block text-xs font-medium text-[#52657a]">MD 上传模式</label>
        {taskUploadEnabled ? (
          <>
            <div className="grid grid-cols-3 gap-2">
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
                      ? "border-[#3370ff]/45 bg-[#eef5ff] text-[#3370ff]"
                      : "border-[#d7e4f5] bg-white text-[#6b7f96] hover:border-[#bfd8ff] hover:bg-[#f6faff]"
                  )}
                  onClick={() =>
                    onTaskMdSyncModeChange(value as "enhanced" | "download_only" | "doc_only")
                  }
                  type="button"
                >
                  <p className="text-xs font-medium">{label}</p>
                  <p className="mt-0.5 text-[10px] text-[#7a8da3]">{desc}</p>
                </button>
              ))}
            </div>
            {taskMdSyncMode === "doc_only" ? (
              <p className="mt-2 text-[11px] text-[#b45309]">
                提示：仅云文档上传会经历 Markdown 转换，复杂内容可能存在格式损耗风险。
              </p>
            ) : null}
          </>
        ) : (
          <div className="rounded-xl border border-dashed border-[#c9d8ec] bg-white px-4 py-3 text-xs text-[#6b7f96]">
            当前任务为仅下载，不会执行任何本地 Markdown 上行，因此无需配置 MD 上传模式。
          </div>
        )}
      </div>
        </div>
      </details>
        </>
      ) : null}

      {view === "all" || view === "rules" ? (
        <>
      <div>
        <label className="mb-2 block text-xs font-medium text-[#52657a]">删除同步策略</label>
        <div className="grid grid-cols-3 gap-2">
          {[
            { value: "off", label: "关闭联动", desc: "删除不传递，最保守" },
            { value: "safe", label: "安全删除", desc: "宽限期后再执行" },
            { value: "strict", label: "严格删除", desc: "立即联动，需谨慎" },
          ].map(({ value, label, desc }) => (
            <button
              key={value}
              className={cn(
                "rounded-xl border p-3 text-left transition",
                taskDeletePolicy === value
                  ? value === "strict"
                    ? "border-[#f43f5e]/45 bg-[#fff1f2] text-[#be123c]"
                    : "border-[#3370ff]/45 bg-[#eef5ff] text-[#3370ff]"
                  : "border-[#d7e4f5] bg-white text-[#334762] hover:border-[#bfd8ff] hover:bg-[#f6faff]",
              )}
              onClick={() => onTaskDeletePolicyChange(value as "off" | "safe" | "strict")}
              type="button"
            >
              <p className="text-xs font-semibold">{label}</p>
              <p className="mt-1 text-[11px] leading-4 text-[#6b7f96]">{desc}</p>
            </button>
          ))}
        </div>
        {taskDeletePolicy === "safe" ? (
          <div className="mt-3 max-w-[260px]">
          <label className="mb-1.5 block text-xs font-medium text-[#52657a]">删除宽限（分钟）</label>
          <input
            className={inputCls}
            type="number"
            min="0"
            step="1"
            value={taskDeleteGraceMinutes}
            onChange={(e) => onTaskDeleteGraceMinutesChange(e.target.value)}
          />
          </div>
        ) : null}
      </div>

      <div className="flex items-center justify-between rounded-lg border border-[#d7e4f5] bg-white px-3 py-3">
        <div>
          <p className="text-sm font-medium text-[#334762]">创建后立即启用</p>
          <p className="mt-0.5 text-[11px] text-[#6b7f96]">关闭时仅保存配置，不会自动执行同步。</p>
        </div>
        <button
          aria-checked={taskEnabled}
          aria-label="创建后立即启用"
          className={cn("h-6 w-11 rounded-full p-0.5 transition", taskEnabled ? "bg-[#3370ff]" : "bg-[#c9d8ec]")}
          onClick={() => onTaskEnabledChange(!taskEnabled)}
          role="switch"
          type="button"
        >
          <span className={cn("block h-5 w-5 rounded-full bg-white transition", taskEnabled && "translate-x-5")} />
        </button>
      </div>
        <div className="rounded-lg border border-[#d7e4f5] bg-[#f8fbff] p-3 text-xs leading-5 text-[#52657a]">
          默认忽略隐藏路径、缓存目录和临时文件；任务创建后可在设置中追加任务级忽略目录。
        </div>
        </>
      ) : null}

      {view === "all" || view === "confirm" ? (
        <>
      <div className="rounded-xl border border-[#d7e4f5] bg-[#f8fbff] p-4">
        <p className="text-xs font-semibold text-[#102033]">任务摘要</p>
        <div className="mt-3 grid grid-cols-2 gap-y-2 text-xs">
          <span className="text-[#6b7f96]">任务名称</span>
          <span className="truncate text-[#334762]">{taskName || "未命名"}</span>
          <span className="text-[#6b7f96]">本地目录</span>
          <span className="truncate text-[#334762]">{taskLocalPath || "—"}</span>
          <span className="text-[#6b7f96]">云端目录</span>
          <span className="truncate text-[#334762]">{selectedCloud?.path || "—"}</span>
          <span className="text-[#6b7f96]">同步模式</span>
          <span className="text-[#334762]">{modeLabels[taskSyncMode]}</span>
          <span className="text-[#6b7f96]">更新模式</span>
          <span className="text-[#334762]">{updateModeLabels[taskUpdateMode]}</span>
          <span className="text-[#6b7f96]">MD 模式</span>
          <span className="text-[#334762]">
            {taskUploadEnabled ? mdSyncModeLabels[taskMdSyncMode] : "不适用（仅下载）"}
          </span>
          <span className="text-[#6b7f96]">删除策略</span>
          <span className="text-[#334762]">{taskDeletePolicy}</span>
        </div>
      </div>

      {error ? <p className="text-sm text-[#be123c]">错误：{error}</p> : null}
        </>
      ) : null}
    </div>
  );
}
