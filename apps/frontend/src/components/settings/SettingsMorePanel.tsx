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
    <div className="rounded-lg border border-[#d7e4f5] bg-white p-4 shadow-[0_10px_28px_rgba(51,112,255,0.05)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-[#102033]">更多设置</h2>
          <p className="mt-1 text-xs text-[#58708d]">设备显示名和本地忽略规则，影响本机体验与任务级过滤。</p>
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
            className="rounded-lg border border-[#c9d8eb] bg-white px-4 py-2 text-xs font-medium text-[#52677f] transition hover:border-[#3370FF]/40 hover:bg-[#f2f7ff] hover:text-[#2456d6]"
            onClick={toggleMoreSettings}
            type="button"
          >
            {showMoreSettings ? "收起设置" : "展开设置"}
          </button>
        </div>
      </div>

      {showMoreSettings ? (
        <div className="mt-3 grid grid-cols-[280px_minmax(0,1fr)] gap-3 rounded-lg border border-[#d7e4f5] bg-[#f8fbff] p-3">
          {children}
        </div>
      ) : null}
    </div>
  );
}
