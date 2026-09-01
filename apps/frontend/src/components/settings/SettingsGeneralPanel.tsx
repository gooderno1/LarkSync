type SettingsGeneralPanelProps = {
  inputCls: string;
  deviceDisplayName: string;
  setDeviceDisplayName: (value: string) => void;
  deviceId?: string | null;
  embedded?: boolean;
  platform?: "windows" | "macos" | "unsupported";
};

export function SettingsGeneralPanel({
  inputCls,
  deviceDisplayName,
  setDeviceDisplayName,
  deviceId,
  embedded = false,
  platform = "windows",
}: SettingsGeneralPanelProps) {
  const deviceType =
    platform === "macos" ? "macOS 桌面端" : platform === "windows" ? "Windows 桌面端" : "桌面端";

  return (
    <div data-settings-device-panel="true" className={embedded ? "min-w-0" : "rounded-lg border border-[#d7e4f5] bg-white p-4 shadow-[0_10px_28px_rgba(51,112,255,0.05)]"}>
      <div className="min-w-0">
        <h2 className="text-base font-semibold text-[#102033]">当前设备</h2>
        <p className="mt-1 text-[11px] leading-4 text-[#7e91a8]">设备名称用于区分同一账号下的多台电脑。</p>
        <div className="mt-3 space-y-3">
          <label className="text-xs font-medium text-[#52677f]">
            设备名称
            <input
              className={`${inputCls} mt-1`}
              placeholder="例如：家里笔记本 / 公司主力机"
              value={deviceDisplayName}
              onChange={(e) => setDeviceDisplayName(e.target.value)}
            />
          </label>
          <div className="grid grid-cols-[76px_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-xs">
            <span className="text-[#7e91a8]">设备 ID</span>
            <span className="truncate font-mono text-[#34516f]" title={deviceId || undefined}>{deviceId || "由桌面端自动生成"}</span>
            <span className="text-[#7e91a8]">设备类型</span>
            <span className="text-[#34516f]">{deviceType}</span>
            <span className="text-[#7e91a8]">隔离规则</span>
            <span className="text-[#34516f]">任务按设备 ID 隔离</span>
          </div>
        </div>
      </div>
    </div>
  );
}
