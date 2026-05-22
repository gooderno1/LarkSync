import type { ReactNode } from "react";

type SettingsMorePanelProps = {
  showMoreSettings: boolean;
  toggleMoreSettings: () => void;
  handleSaveMoreSettings: () => void;
  saving: boolean;
  children?: ReactNode;
};

export function SettingsMorePanel({
  showMoreSettings,
  toggleMoreSettings,
  handleSaveMoreSettings,
  saving,
  children,
}: SettingsMorePanelProps) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-zinc-50">更多设置</h2>
          <p className="mt-1 text-xs text-zinc-400">日志保留与提醒阈值配置（一般无需频繁调整）。</p>
        </div>
        <div className="flex items-center gap-2">
          {showMoreSettings ? (
            <button
              className="rounded-lg bg-[#3370FF] px-4 py-2 text-xs font-semibold text-white transition hover:bg-[#3370FF]/80 disabled:opacity-50"
              onClick={handleSaveMoreSettings}
              disabled={saving}
              type="button"
            >
              {saving ? "保存中..." : "保存更多设置"}
            </button>
          ) : null}
          <button
            className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
            onClick={toggleMoreSettings}
            type="button"
          >
            {showMoreSettings ? "收起设置" : "展开设置"}
          </button>
        </div>
      </div>

      {showMoreSettings ? (
        <div className="mt-5 space-y-4 rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
          {children}
        </div>
      ) : null}
    </div>
  );
}
