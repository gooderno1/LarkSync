/* ------------------------------------------------------------------ */
/*  设置页面 — OAuth + 同步策略（优化设计）                               */
/* ------------------------------------------------------------------ */

import { useEffect, useMemo, useState } from "react";
import { useConfig } from "../hooks/useConfig";
import { useUpdate } from "../hooks/useUpdate";
import { useTasks } from "../hooks/useTasks";
import { formatIntervalLabel } from "../lib/formatters";
import { modeLabels } from "../lib/constants";
import { useToast } from "../components/ui/toast";
import { IconCopy, IconArrowUp, IconArrowDown, IconArrowRightLeft } from "../components/Icons";
import { cn } from "../lib/utils";
import { ThemeToggle } from "../components/ThemeToggle";

export function SettingsPage() {
  const { config, configLoading, saveConfig, saving, saveError } = useConfig();
  const { status, checkUpdate, checking, downloadUpdate, downloading } = useUpdate();
  const { tasks, resetLinks, resettingLinks } = useTasks();
  const { toast } = useToast();

  const [authorizeUrl, setAuthorizeUrl] = useState("");
  const [tokenUrl, setTokenUrl] = useState("");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [syncMode, setSyncMode] = useState("bidirectional");
  const [tokenStore, setTokenStore] = useState("keyring");
  const [uploadValue, setUploadValue] = useState("60");
  const [uploadUnit, setUploadUnit] = useState("seconds");
  const [uploadTime, setUploadTime] = useState("01:00");
  const [downloadValue, setDownloadValue] = useState("1");
  const [downloadUnit, setDownloadUnit] = useState("days");
  const [downloadTime, setDownloadTime] = useState("01:00");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showMoreSettings, setShowMoreSettings] = useState(false);
  const [syncLogRetentionDays, setSyncLogRetentionDays] = useState("0");
  const [syncLogWarnSizeMb, setSyncLogWarnSizeMb] = useState("200");
  const [systemLogRetentionDays, setSystemLogRetentionDays] = useState("1");
  const [autoUpdateEnabled, setAutoUpdateEnabled] = useState(false);
  const [updateCheckIntervalHours, setUpdateCheckIntervalHours] = useState("24");
  const [allowDevToStable, setAllowDevToStable] = useState(false);
  const [deviceDisplayName, setDeviceDisplayName] = useState("");

  // Redirect URI 自动生成（origin 即后端地址，生产模式前后端同源）
  const redirectUri = useMemo(() => {
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    return `${origin}/auth/callback`;
  }, []);

  const copyRedirectUri = () => {
    navigator.clipboard.writeText(redirectUri).then(
      () => toast("已复制到剪贴板", "success"),
      () => toast("复制失败", "danger")
    );
  };

  const lastCheckLabel = useMemo(() => {
    if (!status.last_check) return "未检查";
    try {
      return new Date(status.last_check * 1000).toLocaleString();
    } catch {
      return "未检查";
    }
  }, [status.last_check]);

  const publishedLabel = useMemo(() => {
    if (!status.published_at) return "—";
    try {
      return new Date(status.published_at).toLocaleString();
    } catch {
      return status.published_at;
    }
  }, [status.published_at]);

  // populate from server data
  useEffect(() => {
    if (!config || configLoading) return;
    setAuthorizeUrl(config.auth_authorize_url || "");
    setTokenUrl(config.auth_token_url || "");
    setClientId(config.auth_client_id || "");
    setSyncMode(config.sync_mode || "bidirectional");
    setTokenStore(config.token_store || "keyring");
    if (config.upload_interval_value != null) setUploadValue(String(config.upload_interval_value));
    if (config.upload_interval_unit) setUploadUnit(config.upload_interval_unit);
    if (config.upload_daily_time) setUploadTime(config.upload_daily_time);
    if (config.download_interval_value != null) setDownloadValue(String(config.download_interval_value));
    if (config.download_interval_unit) setDownloadUnit(config.download_interval_unit);
    if (config.download_daily_time) setDownloadTime(config.download_daily_time);
    if (config.sync_log_retention_days != null) setSyncLogRetentionDays(String(config.sync_log_retention_days));
    if (config.sync_log_warn_size_mb != null) setSyncLogWarnSizeMb(String(config.sync_log_warn_size_mb));
    if (config.system_log_retention_days != null) setSystemLogRetentionDays(String(config.system_log_retention_days));
    if (config.auto_update_enabled != null) setAutoUpdateEnabled(Boolean(config.auto_update_enabled));
    if (config.update_check_interval_hours != null) setUpdateCheckIntervalHours(String(config.update_check_interval_hours));
    if (config.allow_dev_to_stable != null) setAllowDevToStable(Boolean(config.allow_dev_to_stable));
    setDeviceDisplayName(config.device_display_name || "");
  }, [config, configLoading]);

  const handleSave = async () => {
    const uVal = uploadValue.trim() ? Number.parseFloat(uploadValue) : null;
    const dVal = downloadValue.trim() ? Number.parseFloat(downloadValue) : null;

    try {
      await saveConfig({
        auth_authorize_url: authorizeUrl.trim() || null,
        auth_token_url: tokenUrl.trim() || null,
        auth_client_id: clientId.trim() || null,
        auth_client_secret: clientSecret.trim() || null,
        auth_redirect_uri: redirectUri,
        sync_mode: syncMode,
        token_store: tokenStore,
        upload_interval_value: uVal,
        upload_interval_unit: uploadUnit,
        upload_daily_time: uploadUnit === "days" ? uploadTime.trim() || null : null,
        download_interval_value: dVal,
        download_interval_unit: downloadUnit,
        download_daily_time: downloadUnit === "days" ? downloadTime.trim() || null : null,
      });
      setClientSecret("");
      toast("配置已保存", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "保存失败", "danger");
    }
  };

  const handleSaveMoreSettings = async () => {
    const syncRetention = syncLogRetentionDays.trim() ? Number.parseInt(syncLogRetentionDays, 10) : null;
    const syncWarnSize = syncLogWarnSizeMb.trim() ? Number.parseInt(syncLogWarnSizeMb, 10) : null;
    const systemRetention = systemLogRetentionDays.trim() ? Number.parseInt(systemLogRetentionDays, 10) : null;
    const updateInterval = updateCheckIntervalHours.trim() ? Number.parseInt(updateCheckIntervalHours, 10) : null;

    try {
      await saveConfig({
        sync_log_retention_days: syncRetention,
        sync_log_warn_size_mb: syncWarnSize,
        system_log_retention_days: systemRetention,
        auto_update_enabled: autoUpdateEnabled,
        update_check_interval_hours: updateInterval,
        allow_dev_to_stable: allowDevToStable,
        device_display_name: deviceDisplayName.trim() || null,
      });
      toast("更多设置已保存", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "保存失败", "danger");
    }
  };

  const handleCheckUpdate = async () => {
    try {
      await checkUpdate();
      toast("已完成更新检查", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "检查更新失败", "danger");
    }
  };

  const handleDownloadUpdate = async () => {
    try {
      const result = await downloadUpdate();
      if (result.download_path) {
        toast(`更新包已下载：${result.download_path}`, "success");
      } else {
        toast("更新包已下载", "success");
      }
    } catch (err) {
      toast(err instanceof Error ? err.message : "下载更新失败", "danger");
    }
  };

  const inputCls = "w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-200 outline-none focus:border-[#3370FF] placeholder:text-zinc-600";

  return (
    <section className="space-y-6 animate-fade-up">
      {/* OAuth */}
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-zinc-50">OAuth 配置</h2>
            <p className="mt-1 text-xs text-zinc-400">填写飞书开放平台的 App ID 和 App Secret 即可完成授权。</p>
          </div>
          <div className="flex items-center gap-2">
            <a
              href="/oauth-guide.html"
              target="_blank"
              rel="noopener noreferrer"
              className="shrink-0 rounded-lg border border-[#3370FF]/30 bg-[#3370FF]/10 px-3 py-1.5 text-xs font-medium text-[#3370FF] transition hover:bg-[#3370FF]/20"
            >
              查看配置教程 ↗
            </a>
            <ThemeToggle />
          </div>
        </div>

        <div className="mt-5 space-y-4">
          {/* App ID */}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">App ID</label>
            <input className={inputCls} placeholder="cli_xxxxxxxxxxxx" value={clientId} onChange={(e) => setClientId(e.target.value)} />
          </div>
          {/* App Secret */}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">App Secret</label>
            <input className={inputCls} placeholder="保存后自动清空" type="password" value={clientSecret} onChange={(e) => setClientSecret(e.target.value)} />
          </div>
          {/* Redirect URI - 自动生成 */}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">
              Redirect URI
              <span className="ml-2 text-zinc-500">（自动生成，请复制填入飞书后台）</span>
            </label>
            <div className="flex gap-2">
              <input className={`${inputCls} bg-zinc-900 text-zinc-300`} value={redirectUri} readOnly />
              <button
                className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-xs font-medium text-zinc-300 transition hover:bg-zinc-700"
                onClick={copyRedirectUri}
                type="button"
              >
                <IconCopy className="h-3.5 w-3.5" />
                复制
              </button>
            </div>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button className="rounded-lg bg-[#3370FF] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#3370FF]/80 disabled:opacity-50" onClick={handleSave} disabled={saving} type="button">
            {saving ? "保存中..." : "保存配置"}
          </button>
          <button className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200" onClick={() => setShowAdvanced((prev) => !prev)} type="button">
            {showAdvanced ? "收起高级设置" : "高级设置"}
          </button>
          {saveError ? <span className="text-sm text-rose-400">错误：{saveError}</span> : null}
        </div>

        {showAdvanced ? (
          <div className="mt-5 space-y-4 rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
            <p className="text-xs font-medium text-zinc-400">高级 OAuth 参数（通常无需修改）</p>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs text-zinc-500">授权地址</label>
                <input className={inputCls} placeholder="默认可空" value={authorizeUrl} onChange={(e) => setAuthorizeUrl(e.target.value)} />
              </div>
              <div>
                <label className="mb-1 block text-xs text-zinc-500">Token 地址</label>
                <input className={inputCls} placeholder="默认可空" value={tokenUrl} onChange={(e) => setTokenUrl(e.target.value)} />
              </div>
              <div>
                <label className="mb-1 block text-xs text-zinc-500">Token 存储方式</label>
                <select className="rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-200 outline-none" value={tokenStore} onChange={(e) => setTokenStore(e.target.value)}>
                  <option value="keyring">系统密钥库</option>
                  <option value="file">文件存储</option>
                </select>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* Sync Strategy — 重新设计 */}
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-zinc-50">同步策略</h2>
            <p className="mt-1 text-xs text-zinc-400">
              当前：本地上行每 {formatIntervalLabel(uploadValue || "60", uploadUnit, uploadTime)}，云端下行每{" "}
              {formatIntervalLabel(downloadValue || "1", downloadUnit, downloadTime)}
            </p>
          </div>
        </div>

        {/* 默认同步模式 — 卡片选择器 */}
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
                    : "border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-800/30"
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

        {/* 上行/下行间隔 — 双列卡片 */}
        <div className="mt-6 grid gap-5 lg:grid-cols-2">
          {/* 本地上行 */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-5">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-emerald-500/15 p-2 text-emerald-400">
                <IconArrowUp className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-medium text-zinc-200">本地上行</p>
                <p className="text-xs text-zinc-500">本地变更推送到云端的频率</p>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-2">
              <span className="text-xs text-zinc-400 shrink-0">每</span>
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
                  <span className="text-xs text-zinc-400 shrink-0">于</span>
                  <input
                    className="w-24 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-center text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
                    type="time"
                    value={uploadTime}
                    onChange={(e) => setUploadTime(e.target.value)}
                  />
                </>
              ) : null}
            </div>
          </div>

          {/* 云端下行 */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-5">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-[#3370FF]/15 p-2 text-[#3370FF]">
                <IconArrowDown className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-medium text-zinc-200">云端下行</p>
                <p className="text-xs text-zinc-500">从云端拉取更新到本地的频率</p>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-2">
              <span className="text-xs text-zinc-400 shrink-0">每</span>
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
                  <span className="text-xs text-zinc-400 shrink-0">于</span>
                  <input
                    className="w-24 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-center text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
                    type="time"
                    value={downloadTime}
                    onChange={(e) => setDownloadTime(e.target.value)}
                  />
                </>
              ) : null}
            </div>
          </div>
        </div>

        {/* 保存按钮 */}
        <div className="mt-5">
          <button className="rounded-lg bg-[#3370FF] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#3370FF]/80 disabled:opacity-50" onClick={handleSave} disabled={saving} type="button">
            {saving ? "保存中..." : "保存策略"}
          </button>
        </div>
      </div>

      {/* 更多设置 */}
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
              onClick={() => setShowMoreSettings((prev) => !prev)}
              type="button"
            >
              {showMoreSettings ? "收起设置" : "展开设置"}
            </button>
          </div>
        </div>

        {showMoreSettings ? (
          <div className="mt-5 space-y-4 rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
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
                        autoUpdateEnabled ? "bg-[#3370FF]" : "bg-zinc-700"
                      )}
                      onClick={() => setAutoUpdateEnabled((prev) => !prev)}
                      type="button"
                    >
                      <span
                        className={cn(
                          "absolute top-0.5 h-5 w-5 rounded-full bg-white transition",
                          autoUpdateEnabled ? "left-6" : "left-0.5"
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
                        allowDevToStable ? "bg-[#3370FF]" : "bg-zinc-700"
                      )}
                      onClick={() => setAllowDevToStable((prev) => !prev)}
                      type="button"
                    >
                      <span
                        className={cn(
                          "absolute top-0.5 h-5 w-5 rounded-full bg-white transition",
                          allowDevToStable ? "left-6" : "left-0.5"
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
                    <button
                      className="rounded-lg bg-[#3370FF] px-4 py-2 text-xs font-semibold text-white transition hover:bg-[#3370FF]/80 disabled:opacity-50"
                      onClick={handleDownloadUpdate}
                      disabled={downloading}
                      type="button"
                    >
                      {downloading ? "下载中..." : "下载更新包"}
                    </button>
                    {status.download_path ? (
                      <p className="mt-2 text-[11px] text-zinc-500">已下载：{status.download_path}</p>
                    ) : null}
                  </div>
                ) : null}
              </div>
            </div>

            {/* 维护工具 */}
            <div className="mt-6 border-t border-zinc-800/80 pt-4">
              <h3 className="text-sm font-medium text-zinc-200">维护工具</h3>
              <p className="mt-1 text-[11px] text-zinc-500">
                当同步映射出现异常时，可重置指定任务的同步映射（SyncLink）。重置后下次同步将重新建立映射关系。
              </p>
              <div className="mt-3 space-y-2">
                {tasks.length === 0 ? (
                  <p className="text-xs text-zinc-500">暂无同步任务。</p>
                ) : (
                  tasks.map((t) => (
                    <div
                      key={t.id}
                      className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-2.5"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm text-zinc-200">{t.name || "未命名任务"}</p>
                        <p className="truncate text-[11px] text-zinc-500">{t.local_path}</p>
                      </div>
                      <button
                        className="ml-3 shrink-0 rounded-lg border border-amber-700/50 bg-amber-500/10 px-3 py-1.5 text-xs font-medium text-amber-300 transition hover:bg-amber-500/20 disabled:opacity-50"
                        disabled={resettingLinks}
                        onClick={async () => {
                          const confirmed = window.confirm(
                            `确定要重置任务「${t.name || t.id}」的同步映射吗？\n\n重置后需要重新同步以建立新的映射关系。`
                          );
                          if (!confirmed) return;
                          try {
                            const result = await resetLinks(t.id);
                            toast(
                              `已清除 ${result.deleted_links} 条同步映射`,
                              "success"
                            );
                          } catch (err) {
                            toast(
                              err instanceof Error ? err.message : "重置失败",
                              "danger"
                            );
                          }
                        }}
                        type="button"
                      >
                        重置映射
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>
        ) : null}
      </div>
    </section>
  );
}
