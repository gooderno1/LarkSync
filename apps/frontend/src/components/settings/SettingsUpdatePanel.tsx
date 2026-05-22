import type { UpdateStatus } from "../../hooks/useUpdate";
import { cn } from "../../lib/utils";
import { IconFolder } from "../Icons";

type SettingsUpdatePanelProps = {
  status: UpdateStatus;
  inputCls: string;
  autoUpdateEnabled: boolean;
  setAutoUpdateEnabled: (value: boolean | ((prev: boolean) => boolean)) => void;
  updateCheckIntervalHours: string;
  setUpdateCheckIntervalHours: (value: string) => void;
  allowDevToStable: boolean;
  setAllowDevToStable: (value: boolean | ((prev: boolean) => boolean)) => void;
  handleCheckUpdate: () => void;
  checking: boolean;
  handleDownloadUpdate: () => void;
  downloading: boolean;
  installing: boolean;
  handleOpenDownloadedUpdateFolder: () => void;
  openingUpdateFolder: boolean;
  handleInstallDownloadedUpdate: () => void;
  lastCheckLabel: string;
  publishedLabel: string;
};

export function SettingsUpdatePanel({
  status,
  inputCls,
  autoUpdateEnabled,
  setAutoUpdateEnabled,
  updateCheckIntervalHours,
  setUpdateCheckIntervalHours,
  allowDevToStable,
  setAllowDevToStable,
  handleCheckUpdate,
  checking,
  handleDownloadUpdate,
  downloading,
  installing,
  handleOpenDownloadedUpdateFolder,
  openingUpdateFolder,
  handleInstallDownloadedUpdate,
  lastCheckLabel,
  publishedLabel,
}: SettingsUpdatePanelProps) {
  return (
    <div className="mt-6 border-t border-zinc-800/80 pt-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium text-zinc-200">自动更新</h3>
          <p className="mt-1 text-[11px] text-zinc-500">仅检查稳定版（GitHub Releases）。</p>
        </div>
        <button
          className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
          onClick={handleCheckUpdate}
          disabled={checking}
          type="button"
        >
          {checking ? "检查中..." : "检查更新"}
        </button>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">自动更新开关</label>
          <div className="flex items-center gap-3">
            <button
              className={cn(
                "relative h-6 w-11 rounded-full transition",
                autoUpdateEnabled ? "bg-[#3370FF]" : "bg-zinc-700",
              )}
              onClick={() => setAutoUpdateEnabled((prev) => !prev)}
              type="button"
            >
              <span
                className={cn(
                  "absolute top-0.5 h-5 w-5 rounded-full bg-white transition",
                  autoUpdateEnabled ? "left-6" : "left-0.5",
                )}
              />
            </button>
            <span className="text-xs text-zinc-500">{autoUpdateEnabled ? "已启用" : "未启用"}</span>
          </div>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">检查间隔（小时）</label>
          <input
            className={inputCls}
            type="number"
            min="1"
            step="1"
            value={updateCheckIntervalHours}
            onChange={(e) => setUpdateCheckIntervalHours(e.target.value)}
          />
          <p className="mt-1 text-[11px] text-zinc-500">默认 24 小时，可手动触发检查。</p>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">允许 dev 升级到稳定版</label>
          <div className="flex items-center gap-3">
            <button
              className={cn(
                "relative h-6 w-11 rounded-full transition",
                allowDevToStable ? "bg-[#3370FF]" : "bg-zinc-700",
              )}
              onClick={() => setAllowDevToStable((prev) => !prev)}
              type="button"
            >
              <span
                className={cn(
                  "absolute top-0.5 h-5 w-5 rounded-full bg-white transition",
                  allowDevToStable ? "left-6" : "left-0.5",
                )}
              />
            </button>
            <span className="text-xs text-zinc-500">{allowDevToStable ? "已允许" : "默认禁用"}</span>
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 text-xs text-zinc-400">
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <p className="text-zinc-500">当前版本</p>
            <p className="mt-1 text-sm text-zinc-200">{status.current_version || "未知"}</p>
          </div>
          <div>
            <p className="text-zinc-500">最新版本</p>
            <p className="mt-1 text-sm text-zinc-200">{status.latest_version || "—"}</p>
          </div>
          <div>
            <p className="text-zinc-500">上次检查</p>
            <p className="mt-1 text-sm text-zinc-200">{lastCheckLabel}</p>
          </div>
          <div>
            <p className="text-zinc-500">发布时间</p>
            <p className="mt-1 text-sm text-zinc-200">{publishedLabel}</p>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          {status.update_available ? (
            <span className="rounded-full bg-emerald-500/15 px-3 py-1 text-xs text-emerald-300">发现新版本</span>
          ) : (
            <span className="rounded-full bg-zinc-700/40 px-3 py-1 text-xs text-zinc-400">已是最新</span>
          )}
          {status.last_error ? (
            <span className="text-rose-300">检查失败：{status.last_error}</span>
          ) : null}
          {status.asset?.name ? (
            <span className="text-zinc-500">包名：{status.asset.name}</span>
          ) : null}
        </div>
        {status.update_available ? (
          <div className="mt-3">
            <div className="flex flex-wrap gap-2">
              <button
                className="rounded-lg bg-[#3370FF] px-4 py-2 text-xs font-semibold text-white transition hover:bg-[#3370FF]/80 disabled:opacity-50"
                onClick={handleDownloadUpdate}
                disabled={downloading || installing}
                type="button"
              >
                {downloading ? "下载中..." : "下载更新包"}
              </button>
              {status.download_path ? (
                <button
                  className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-900/70 px-4 py-2 text-xs font-medium text-zinc-300 transition hover:bg-zinc-800/60 disabled:opacity-50"
                  onClick={handleOpenDownloadedUpdateFolder}
                  disabled={openingUpdateFolder || installing || downloading}
                  type="button"
                >
                  <IconFolder className="h-3.5 w-3.5" />
                  {openingUpdateFolder ? "打开中..." : "打开安装包目录"}
                </button>
              ) : null}
              {status.download_path ? (
                <button
                  className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-4 py-2 text-xs font-semibold text-emerald-300 transition hover:bg-emerald-500/20 disabled:opacity-50"
                  onClick={handleInstallDownloadedUpdate}
                  disabled={installing || downloading}
                  type="button"
                >
                  {installing ? "启动中..." : "静默安装已下载更新"}
                </button>
              ) : null}
            </div>
            {status.download_path ? (
              <p className="mt-2 break-all text-[11px] text-zinc-500">已下载：{status.download_path}</p>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
