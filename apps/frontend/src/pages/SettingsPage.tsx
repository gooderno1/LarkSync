/* ------------------------------------------------------------------ */
/*  设置页面 — OAuth + 同步策略（优化设计）                               */
/* ------------------------------------------------------------------ */

import { useEffect, useMemo, useState } from "react";
import { useConfig } from "../hooks/useConfig";
import { formatIntervalLabel } from "../lib/formatters";
import { modeLabels } from "../lib/constants";
import { useToast } from "../components/ui/toast";
import { apiUrl } from "../lib/api";
import { IconCopy, IconArrowUp, IconArrowDown, IconArrowRightLeft } from "../components/Icons";
import { cn } from "../lib/utils";

export function SettingsPage() {
  const { config, configLoading, saveConfig, saving, saveError } = useConfig();
  const { toast } = useToast();

  const [authorizeUrl, setAuthorizeUrl] = useState("");
  const [tokenUrl, setTokenUrl] = useState("");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [syncMode, setSyncMode] = useState("bidirectional");
  const [tokenStore, setTokenStore] = useState("keyring");
  const [uploadValue, setUploadValue] = useState("2");
  const [uploadUnit, setUploadUnit] = useState("seconds");
  const [uploadTime, setUploadTime] = useState("01:00");
  const [downloadValue, setDownloadValue] = useState("1");
  const [downloadUnit, setDownloadUnit] = useState("days");
  const [downloadTime, setDownloadTime] = useState("01:00");
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Redirect URI 自动生成
  const redirectUri = useMemo(() => {
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    return `${origin}${apiUrl("/auth/callback")}`;
  }, []);

  const copyRedirectUri = () => {
    navigator.clipboard.writeText(redirectUri).then(
      () => toast("已复制到剪贴板", "success"),
      () => toast("复制失败", "danger")
    );
  };

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

  const inputCls = "w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-200 outline-none focus:border-[#3370FF] placeholder:text-zinc-600";

  return (
    <section className="space-y-6 animate-fade-up">
      {/* OAuth */}
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
        <h2 className="text-lg font-semibold text-zinc-50">OAuth 配置</h2>
        <p className="mt-1 text-xs text-zinc-400">填写飞书开放平台的 App ID 和 App Secret 即可完成授权。</p>

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
              当前：本地上行每 {formatIntervalLabel(uploadValue || "2", uploadUnit, uploadTime)}，云端下行每{" "}
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
    </section>
  );
}
