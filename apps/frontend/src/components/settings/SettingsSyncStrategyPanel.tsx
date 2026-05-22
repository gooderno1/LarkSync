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
};

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
}: SettingsSyncStrategyPanelProps) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-zinc-50">同步策略</h2>
          <p className="mt-1 text-xs text-zinc-400">
            当前：
            {uploadEnabled
              ? ` 本地上行每 ${formatIntervalLabel(uploadValue || "60", uploadUnit, uploadTime)}，`
              : " 本地上行已关闭，"}
            {downloadEnabled
              ? ` 云端下行每 ${formatIntervalLabel(downloadValue || "1", downloadUnit, downloadTime)}`
              : " 云端下行已关闭"}
          </p>
        </div>
      </div>

      <div className="mt-5">
        <label className="mb-2 block text-xs font-medium text-zinc-400">默认同步模式</label>
        <div className="grid grid-cols-3 gap-3">
          {[
            { value: "bidirectional", label: "双向同步", desc: "本地与云端互相同步", Icon: IconArrowRightLeft },
            { value: "download_only", label: "仅下载", desc: "仅从云端拉取到本地", Icon: IconArrowDown },
            { value: "upload_only", label: "仅上传", desc: "仅从本地推送到云端", Icon: IconArrowUp },
          ].map(({ value, label, desc, Icon }) => (
            <button
              key={value}
              className={cn(
                "flex flex-col items-center gap-2 rounded-xl border p-5 text-center transition",
                syncMode === value
                  ? "border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]"
                  : "border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-800/30",
              )}
              onClick={() => setSyncMode(value)}
              type="button"
            >
              <Icon className="h-6 w-6" />
              <span className="text-sm font-medium">{label}</span>
              <span className="text-[11px] text-zinc-500">{desc}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-emerald-500/15 p-2 text-emerald-400">
              <IconArrowUp className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-medium text-zinc-200">本地上行</p>
              <p className="text-xs text-zinc-500">
                {uploadEnabled ? "本地变更推送到云端的频率" : "当前默认模式为仅下载，本地上行配置不适用"}
              </p>
            </div>
          </div>
          {uploadEnabled ? (
            <div className="mt-4 flex items-center gap-2">
              <span className="shrink-0 text-xs text-zinc-400">每</span>
              <input
                className="w-20 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-center text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
                type="number"
                min="0"
                step="0.5"
                value={uploadValue}
                onChange={(e) => setUploadValue(e.target.value)}
              />
              <select
                className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none"
                value={uploadUnit}
                onChange={(e) => setUploadUnit(e.target.value)}
              >
                <option value="seconds">秒</option>
                <option value="hours">小时</option>
                <option value="days">天</option>
              </select>
              {uploadUnit === "days" ? (
                <>
                  <span className="shrink-0 text-xs text-zinc-400">于</span>
                  <input
                    className="w-24 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-center text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
                    type="time"
                    value={uploadTime}
                    onChange={(e) => setUploadTime(e.target.value)}
                  />
                </>
              ) : null}
            </div>
          ) : (
            <div className="mt-4 rounded-lg border border-dashed border-zinc-800 bg-zinc-950/70 px-4 py-3 text-xs text-zinc-500">
              仅下载模式不会使用本地上行频率；切回“双向同步”或“仅上传”后再配置即可。
            </div>
          )}
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-[#3370FF]/15 p-2 text-[#3370FF]">
              <IconArrowDown className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-medium text-zinc-200">云端下行</p>
              <p className="text-xs text-zinc-500">
                {downloadEnabled ? "从云端拉取更新到本地的频率" : "当前默认模式为仅上传，云端下行配置不适用"}
              </p>
            </div>
          </div>
          {downloadEnabled ? (
            <div className="mt-4 flex items-center gap-2">
              <span className="shrink-0 text-xs text-zinc-400">每</span>
              <input
                className="w-20 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-center text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
                type="number"
                min="0"
                step="0.5"
                value={downloadValue}
                onChange={(e) => setDownloadValue(e.target.value)}
              />
              <select
                className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none"
                value={downloadUnit}
                onChange={(e) => setDownloadUnit(e.target.value)}
              >
                <option value="seconds">秒</option>
                <option value="hours">小时</option>
                <option value="days">天</option>
              </select>
              {downloadUnit === "days" ? (
                <>
                  <span className="shrink-0 text-xs text-zinc-400">于</span>
                  <input
                    className="w-24 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-center text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
                    type="time"
                    value={downloadTime}
                    onChange={(e) => setDownloadTime(e.target.value)}
                  />
                </>
              ) : null}
            </div>
          ) : (
            <div className="mt-4 rounded-lg border border-dashed border-zinc-800 bg-zinc-950/70 px-4 py-3 text-xs text-zinc-500">
              仅上传模式不会使用云端下行频率；切回“双向同步”或“仅下载”后再配置即可。
            </div>
          )}
        </div>
      </div>

      <div className="mt-5">
        <button className="rounded-lg bg-[#3370FF] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#3370FF]/80 disabled:opacity-50" onClick={handleSave} disabled={saving} type="button">
          {saving ? "保存中..." : "保存策略"}
        </button>
      </div>
    </div>
  );
}
