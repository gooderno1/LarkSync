type SettingsGeneralPanelProps = {
  inputCls: string;
  deviceDisplayName: string;
  setDeviceDisplayName: (value: string) => void;
  syncLogRetentionDays: string;
  setSyncLogRetentionDays: (value: string) => void;
  syncLogWarnSizeMb: string;
  setSyncLogWarnSizeMb: (value: string) => void;
  systemLogRetentionDays: string;
  setSystemLogRetentionDays: (value: string) => void;
};

export function SettingsGeneralPanel({
  inputCls,
  deviceDisplayName,
  setDeviceDisplayName,
  syncLogRetentionDays,
  setSyncLogRetentionDays,
  syncLogWarnSizeMb,
  setSyncLogWarnSizeMb,
  systemLogRetentionDays,
  setSystemLogRetentionDays,
}: SettingsGeneralPanelProps) {
  return (
    <>
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
        <label className="mb-1.5 block text-xs font-medium text-zinc-400">
          设备显示名称
        </label>
        <input
          className={inputCls}
          placeholder="例如：家里笔记本 / 公司主力机"
          value={deviceDisplayName}
          onChange={(e) => setDeviceDisplayName(e.target.value)}
        />
        <p className="mt-1 text-[11px] text-zinc-500">
          仅用于页面展示，内部仍使用设备 ID 做归属隔离。
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">同步日志保留天数</label>
          <input
            className={inputCls}
            type="number"
            min="0"
            step="1"
            value={syncLogRetentionDays}
            onChange={(e) => setSyncLogRetentionDays(e.target.value)}
          />
          <p className="mt-1 text-[11px] text-zinc-500">0 表示永久保留（不自动清理）。</p>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">同步日志提醒阈值（MB）</label>
          <input
            className={inputCls}
            type="number"
            min="0"
            step="10"
            value={syncLogWarnSizeMb}
            onChange={(e) => setSyncLogWarnSizeMb(e.target.value)}
          />
          <p className="mt-1 text-[11px] text-zinc-500">超过该体积会提示调整保留天数。</p>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">系统日志保留天数</label>
          <input
            className={inputCls}
            type="number"
            min="1"
            step="1"
            value={systemLogRetentionDays}
            onChange={(e) => setSystemLogRetentionDays(e.target.value)}
          />
          <p className="mt-1 text-[11px] text-zinc-500">默认 1 天，避免系统日志过大。</p>
        </div>
      </div>
    </>
  );
}
