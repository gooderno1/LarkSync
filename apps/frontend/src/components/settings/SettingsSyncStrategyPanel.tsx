import { useState } from "react";
import { formatIntervalLabel } from "../../lib/formatters";
import { cn } from "../../lib/utils";
import { IconArrowDown, IconArrowRightLeft, IconArrowUp } from "../Icons";

type SettingsSyncStrategyPanelProps = {
  syncMode: string;
  setSyncMode: (value: string) => void;
  uploadEnabled: boolean;
  downloadEnabled: boolean;
  uploadValue: string;
  setUploadValue: (value: string) => void;
  uploadUnit: string;
  setUploadUnit: (value: string) => void;
  uploadTime: string;
  setUploadTime: (value: string) => void;
  downloadValue: string;
  setDownloadValue: (value: string) => void;
  downloadUnit: string;
  setDownloadUnit: (value: string) => void;
  downloadTime: string;
  setDownloadTime: (value: string) => void;
  handleSave: () => void;
  saving: boolean;
  deletePolicy?: "off" | "safe" | "strict";
  setDeletePolicy?: (value: "off" | "safe" | "strict") => void;
  showSaveAction?: boolean;
};

const fieldClass =
  "h-8 rounded-lg border border-[#c9d8eb] bg-white px-3 text-sm text-[#1f2d3d] outline-none transition focus:border-[#3370FF] focus:ring-2 focus:ring-[#3370FF]/15";

export function SettingsSyncStrategyPanel({
  syncMode,
  setSyncMode,
  uploadEnabled,
  downloadEnabled,
  uploadValue,
  setUploadValue,
  uploadUnit,
  setUploadUnit,
  uploadTime,
  setUploadTime,
  downloadValue,
  setDownloadValue,
  downloadUnit,
  setDownloadUnit,
  downloadTime,
  setDownloadTime,
  handleSave,
  saving,
  deletePolicy = "safe",
  setDeletePolicy = () => undefined,
  showSaveAction = true,
}: SettingsSyncStrategyPanelProps) {
  const [showSchedule, setShowSchedule] = useState(false);

  return (
    <div className="rounded-lg border border-[#d7e4f5] bg-white p-4 shadow-[0_10px_28px_rgba(51,112,255,0.05)]">
      <div className="grid grid-cols-[140px_minmax(0,1fr)_280px] items-start gap-4">
        <div>
          <h2 className="text-base font-semibold text-[#102033]">默认同步策略</h2>
          <p className="mt-1 text-xs leading-5 text-[#58708d]">新建任务时的默认同步方向。</p>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {[
            { value: "bidirectional", label: "双向同步", desc: "本地与云端互相同步", Icon: IconArrowRightLeft },
            { value: "download_only", label: "仅下载", desc: "仅从云端拉取到本地", Icon: IconArrowDown },
            { value: "upload_only", label: "仅上传", desc: "仅从本地推送到云端", Icon: IconArrowUp },
          ].map(({ value, label, desc, Icon }) => (
            <button
              key={value}
              className={cn(
                "flex min-h-[72px] items-center justify-center gap-2 rounded-lg border px-3 py-2 text-left transition",
                syncMode === value
                  ? "border-[#3370FF]/55 bg-[#edf4ff] text-[#2456d6] shadow-[0_10px_28px_rgba(51,112,255,0.12)]"
                  : "border-[#d7e4f5] bg-[#f8fbff] text-[#52677f] hover:border-[#3370FF]/35 hover:bg-[#f2f7ff]",
              )}
              onClick={() => setSyncMode(value)}
              type="button"
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="min-w-0">
                <span className="block text-sm font-semibold">{label}</span>
                <span className="block truncate text-[10px] leading-4 text-[#7e91a8]">{desc}</span>
              </span>
            </button>
          ))}
        </div>
        <div className="border-l border-[#d7e4f5] pl-4">
          <label className="block text-xs font-medium text-[#52677f]">删除策略</label>
          <select
            className="mt-2 h-8 w-full rounded-lg border border-[#c9d8eb] bg-white px-3 text-xs text-[#1f2d3d] outline-none focus:border-[#3370FF]"
            value={deletePolicy}
            onChange={(event) => setDeletePolicy(event.target.value as "off" | "safe" | "strict")}
          >
            <option value="safe">安全删除（不删除云端文件）</option>
            <option value="strict">严格联动删除</option>
            <option value="off">关闭删除联动</option>
          </select>
          <button
            className="mt-2 text-xs font-semibold text-[#3370ff] hover:text-[#2456d6]"
            onClick={() => setShowSchedule((value) => !value)}
            type="button"
          >
            {showSchedule ? "收起计划设置" : "计划设置"}
          </button>
        </div>
      </div>

      {showSchedule ? <div className="mt-3 grid grid-cols-2 gap-3 border-t border-[#e4edf8] pt-3">
        <div className="rounded-lg border border-[#d7e4f5] bg-[#f8fbff] p-3">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-[#e8faf6] p-2 text-[#0f9f8f]">
              <IconArrowUp className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-semibold text-[#102033]">本地上行</p>
              <p className="text-xs text-[#7e91a8]">
                {uploadEnabled ? "本地变更推送到云端的频率" : "当前默认模式为仅下载，本地上行配置不适用"}
              </p>
            </div>
          </div>
          {uploadEnabled ? (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="shrink-0 text-xs text-[#52677f]">每</span>
              <input
                className={`${fieldClass} w-20 text-center`}
                type="number"
                min="0"
                step="0.5"
                value={uploadValue}
                onChange={(e) => setUploadValue(e.target.value)}
              />
              <select
                className={fieldClass}
                value={uploadUnit}
                onChange={(e) => setUploadUnit(e.target.value)}
              >
                <option value="seconds">秒</option>
                <option value="hours">小时</option>
                <option value="days">天</option>
              </select>
              {uploadUnit === "days" ? (
                <>
                  <span className="shrink-0 text-xs text-[#52677f]">于</span>
                  <input
                    className={`${fieldClass} w-24 text-center`}
                    type="time"
                    value={uploadTime}
                    onChange={(e) => setUploadTime(e.target.value)}
                  />
                </>
              ) : null}
            </div>
          ) : (
            <div className="mt-4 rounded-lg border border-dashed border-[#c9d8eb] bg-white px-4 py-3 text-xs text-[#7e91a8]">
              仅下载模式不会使用本地上行频率；切回“双向同步”或“仅上传”后再配置即可。
            </div>
          )}
        </div>

        <div className="rounded-lg border border-[#d7e4f5] bg-[#f8fbff] p-3">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-[#edf4ff] p-2 text-[#3370FF]">
              <IconArrowDown className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-semibold text-[#102033]">云端下行</p>
              <p className="text-xs text-[#7e91a8]">
                {downloadEnabled ? "从云端拉取更新到本地的频率" : "当前默认模式为仅上传，云端下行配置不适用"}
              </p>
            </div>
          </div>
          {downloadEnabled ? (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="shrink-0 text-xs text-[#52677f]">每</span>
              <input
                className={`${fieldClass} w-20 text-center`}
                type="number"
                min="0"
                step="0.5"
                value={downloadValue}
                onChange={(e) => setDownloadValue(e.target.value)}
              />
              <select
                className={fieldClass}
                value={downloadUnit}
                onChange={(e) => setDownloadUnit(e.target.value)}
              >
                <option value="seconds">秒</option>
                <option value="hours">小时</option>
                <option value="days">天</option>
              </select>
              {downloadUnit === "days" ? (
                <>
                  <span className="shrink-0 text-xs text-[#52677f]">于</span>
                  <input
                    className={`${fieldClass} w-24 text-center`}
                    type="time"
                    value={downloadTime}
                    onChange={(e) => setDownloadTime(e.target.value)}
                  />
                </>
              ) : null}
            </div>
          ) : (
            <div className="mt-4 rounded-lg border border-dashed border-[#c9d8eb] bg-white px-4 py-3 text-xs text-[#7e91a8]">
              仅上传模式不会使用云端下行频率；切回“双向同步”或“仅下载”后再配置即可。
            </div>
          )}
        </div>
      </div> : null}

      <div className="mt-3 flex items-center justify-between border-t border-[#e4edf8] pt-3">
        <p className="text-[11px] text-[#7e91a8]">
          {uploadEnabled ? `上行 ${formatIntervalLabel(uploadValue || "60", uploadUnit, uploadTime)}` : "上行关闭"}
          <span className="px-2">·</span>
          {downloadEnabled ? `下行 ${formatIntervalLabel(downloadValue || "1", downloadUnit, downloadTime)}` : "下行关闭"}
        </p>
        {showSaveAction ? (
          <button
            className="h-8 rounded-lg bg-[#3370FF] px-4 text-xs font-semibold text-white transition hover:bg-[#2456d6] disabled:opacity-50"
            onClick={handleSave}
            disabled={saving}
            type="button"
          >
            {saving ? "保存中..." : "保存策略"}
          </button>
        ) : <span className="text-[11px] font-medium text-[#3370ff]">由页面右上角统一保存</span>}
      </div>
    </div>
  );
}
