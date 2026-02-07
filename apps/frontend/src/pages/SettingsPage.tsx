/* ------------------------------------------------------------------ */
/*  设置页面                                                             */
/* ------------------------------------------------------------------ */

import { useEffect, useState } from "react";
import { useConfig } from "../hooks/useConfig";
import { formatIntervalLabel } from "../lib/formatters";
import { useToast } from "../components/ui/toast";

export function SettingsPage() {
  const { config, configLoading, saveConfig, saving, saveError } = useConfig();
  const { toast } = useToast();

  const [authorizeUrl, setAuthorizeUrl] = useState("");
  const [tokenUrl, setTokenUrl] = useState("");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [redirectUri, setRedirectUri] = useState("");
  const [syncMode, setSyncMode] = useState("bidirectional");
  const [tokenStore, setTokenStore] = useState("keyring");
  const [uploadValue, setUploadValue] = useState("2");
  const [uploadUnit, setUploadUnit] = useState("seconds");
  const [uploadTime, setUploadTime] = useState("01:00");
  const [downloadValue, setDownloadValue] = useState("1");
  const [downloadUnit, setDownloadUnit] = useState("days");
  const [downloadTime, setDownloadTime] = useState("01:00");
  const [showAdvanced, setShowAdvanced] = useState(false);

  // populate from server data
  useEffect(() => {
    if (!config || configLoading) return;
    setAuthorizeUrl(config.auth_authorize_url || "");
    setTokenUrl(config.auth_token_url || "");
    setClientId(config.auth_client_id || "");
    setRedirectUri(config.auth_redirect_uri || "");
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
        auth_redirect_uri: redirectUri.trim() || null,
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
        <p className="mt-1 text-xs text-zinc-400">仅填写 App ID / Secret / Redirect URI 即可完成授权。</p>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <input className={inputCls} placeholder="App ID" value={clientId} onChange={(e) => setClientId(e.target.value)} />
          <input className={inputCls} placeholder="App Secret（保存后自动清空）" type="password" value={clientSecret} onChange={(e) => setClientSecret(e.target.value)} />
          <input className={`${inputCls} md:col-span-2`} placeholder="Redirect URI" value={redirectUri} onChange={(e) => setRedirectUri(e.target.value)} />
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button className="rounded-lg bg-[#3370FF] px-5 py-2 text-sm font-semibold text-white transition hover:bg-[#3370FF]/80 disabled:opacity-50" onClick={handleSave} disabled={saving} type="button">
            {saving ? "保存中..." : "保存配置"}
          </button>
          <button className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800" onClick={() => setShowAdvanced((prev) => !prev)} type="button">
            {showAdvanced ? "收起可选设置" : "展开可选设置"}
          </button>
          {saveError ? <span className="text-sm text-rose-400">错误：{saveError}</span> : null}
        </div>
        {showAdvanced ? (
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <input className={inputCls} placeholder="授权地址 auth_authorize_url（默认可空）" value={authorizeUrl} onChange={(e) => setAuthorizeUrl(e.target.value)} />
            <input className={inputCls} placeholder="Token 地址 auth_token_url（默认可空）" value={tokenUrl} onChange={(e) => setTokenUrl(e.target.value)} />
            <select className="rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-200 outline-none" value={tokenStore} onChange={(e) => setTokenStore(e.target.value)}>
              <option value="keyring">密钥库存储</option>
              <option value="file">文件存储</option>
            </select>
          </div>
        ) : null}
      </div>

      {/* Sync Strategy */}
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
        <h2 className="text-lg font-semibold text-zinc-50">同步策略</h2>
        <p className="mt-1 text-xs text-zinc-400">
          默认：本地上行每 {formatIntervalLabel(uploadValue || "2", uploadUnit, uploadTime)}，云端下行每{" "}
          {formatIntervalLabel(downloadValue || "1", downloadUnit, downloadTime)}。
        </p>
        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          {/* Upload interval */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
            <p className="text-xs uppercase tracking-widest text-zinc-500">本地上行</p>
            <div className="mt-3 grid gap-2 md:grid-cols-[1fr_auto]">
              <input className={inputCls} type="number" min="0" step="0.5" placeholder="间隔值" value={uploadValue} onChange={(e) => setUploadValue(e.target.value)} />
              <select className="rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-200 outline-none" value={uploadUnit} onChange={(e) => setUploadUnit(e.target.value)}>
                <option value="seconds">秒</option>
                <option value="hours">小时</option>
                <option value="days">天</option>
              </select>
            </div>
            {uploadUnit === "days" ? (
              <input className={`${inputCls} mt-3`} type="time" value={uploadTime} onChange={(e) => setUploadTime(e.target.value)} />
            ) : null}
          </div>
          {/* Download interval */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
            <p className="text-xs uppercase tracking-widest text-zinc-500">云端下行</p>
            <div className="mt-3 grid gap-2 md:grid-cols-[1fr_auto]">
              <input className={inputCls} type="number" min="0" step="0.5" placeholder="间隔值" value={downloadValue} onChange={(e) => setDownloadValue(e.target.value)} />
              <select className="rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-200 outline-none" value={downloadUnit} onChange={(e) => setDownloadUnit(e.target.value)}>
                <option value="seconds">秒</option>
                <option value="hours">小时</option>
                <option value="days">天</option>
              </select>
            </div>
            {downloadUnit === "days" ? (
              <input className={`${inputCls} mt-3`} type="time" value={downloadTime} onChange={(e) => setDownloadTime(e.target.value)} />
            ) : null}
          </div>
          {/* Default sync mode */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
            <p className="text-xs uppercase tracking-widest text-zinc-500">默认同步模式</p>
            <select className="mt-3 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-200 outline-none" value={syncMode} onChange={(e) => setSyncMode(e.target.value)}>
              <option value="bidirectional">双向同步</option>
              <option value="download_only">仅下载</option>
              <option value="upload_only">仅上传</option>
            </select>
          </div>
        </div>
      </div>
    </section>
  );
}
