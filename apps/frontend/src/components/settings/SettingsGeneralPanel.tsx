import { Switch } from "../ui/switch";

type SettingsGeneralPanelProps = {
  inputCls: string;
  deviceDisplayName: string;
  setDeviceDisplayName: (value: string) => void;
  deviceId?: string | null;
  embedded?: boolean;
  autostartEnabled?: boolean;
  autostartSupported?: boolean;
  autostartLoading?: boolean;
  updatingAutostart?: boolean;
  platform?: "windows" | "macos" | "unsupported";
  onAutostartChange?: (enabled: boolean) => void;
};

export function SettingsGeneralPanel({
  inputCls,
  deviceDisplayName,
  setDeviceDisplayName,
  deviceId,
  embedded = false,
  autostartEnabled = false,
  autostartSupported = true,
  autostartLoading = false,
  updatingAutostart = false,
  platform = "windows",
  onAutostartChange,
}: SettingsGeneralPanelProps) {
  const deviceType =
    platform === "macos" ? "macOS 桌面端" : platform === "windows" ? "Windows 桌面端" : "桌面端";

  return (
    <div data-settings-device-panel={embedded ? "true" : undefined} className={embedded ? "min-w-0 p-4" : "rounded-lg border border-[#d7e4f5] bg-white p-4 shadow-[0_10px_28px_rgba(51,112,255,0.05)]"}>
      <div className={embedded ? "min-w-0" : "grid grid-cols-[140px_minmax(0,1fr)_minmax(0,1.2fr)] items-center gap-4"}>
        <h2 className="text-base font-semibold text-[#102033]">当前设备</h2>
        <div className={embedded ? "mt-3 space-y-3" : "contents"}>
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
          <div className="flex items-center justify-between gap-4 rounded-lg border border-[#d7e4f5] bg-[#f8fbff] px-3 py-2.5">
            <div className="min-w-0">
              <p className="text-xs font-semibold text-[#294662]">开机自启动</p>
              <p className="mt-0.5 text-[11px] leading-4 text-[#7e91a8]">
                {autostartSupported
                  ? "登录当前系统账号后自动启动 LarkSync。此项立即生效，无需点击右上角按钮。"
                  : "当前系统暂不支持由 LarkSync 管理开机自启动。"}
              </p>
            </div>
            <Switch
              label="开机自启动"
              checked={autostartEnabled}
              disabled={!autostartSupported || autostartLoading || updatingAutostart}
              onCheckedChange={(enabled) => onAutostartChange?.(enabled)}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
