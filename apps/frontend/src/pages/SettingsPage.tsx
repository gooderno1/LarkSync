/* ------------------------------------------------------------------ */
/*  设置页面 — OAuth + 同步策略（优化设计）                               */
/* ------------------------------------------------------------------ */

import { useEffect, useMemo, useState } from "react";
import { useConfig } from "../hooks/useConfig";
import { useTasks } from "../hooks/useTasks";
import { useAuth } from "../hooks/useAuth";
import { syncModeSupportsDownload, syncModeSupportsUpload } from "../lib/constants";
import { apiFetch } from "../lib/api";
import { useToast } from "../components/ui/toast";
import { SettingsOAuthPanel } from "../components/settings/SettingsOAuthPanel";
import { SettingsSyncStrategyPanel } from "../components/settings/SettingsSyncStrategyPanel";
import { SettingsGeneralPanel } from "../components/settings/SettingsGeneralPanel";
import { SettingsIgnoredDirectoriesPanel } from "../components/settings/SettingsIgnoredDirectoriesPanel";
import { IconCircleCheck, IconLogout } from "../components/Icons";

export function SettingsPage() {
  const { config, configLoading, saveConfig, saving, saveError } = useConfig();
  const { tasks, updateIgnoredSubpaths, updatingIgnoredSubpaths } = useTasks();
  const { connected, driveOk, accountName, deviceId, logout } = useAuth();
  const { toast } = useToast();

  const [authorizeUrl, setAuthorizeUrl] = useState("");
  const [tokenUrl, setTokenUrl] = useState("");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [syncMode, setSyncMode] = useState("bidirectional");
  const [deletePolicy, setDeletePolicy] = useState<"off" | "safe" | "strict">("safe");
  const [ignoreHiddenCachePaths, setIgnoreHiddenCachePaths] = useState(true);
  const [tokenStore, setTokenStore] = useState("keyring");
  const [uploadValue, setUploadValue] = useState("60");
  const [uploadUnit, setUploadUnit] = useState("seconds");
  const [uploadTime, setUploadTime] = useState("01:00");
  const [downloadValue, setDownloadValue] = useState("1");
  const [downloadUnit, setDownloadUnit] = useState("days");
  const [downloadTime, setDownloadTime] = useState("01:00");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showIgnoredDirectorySettings, setShowIgnoredDirectorySettings] = useState(false);
  const [deviceDisplayName, setDeviceDisplayName] = useState("");
  const [ignoredPathDrafts, setIgnoredPathDrafts] = useState<Record<string, string>>({});
  const [ignoredSubpathsMap, setIgnoredSubpathsMap] = useState<Record<string, string[]>>({});
  const [pickingIgnoredTaskId, setPickingIgnoredTaskId] = useState<string | null>(null);
  const uploadEnabled = syncModeSupportsUpload(syncMode);
  const downloadEnabled = syncModeSupportsDownload(syncMode);

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

  // populate from server data
  useEffect(() => {
    if (!config || configLoading) return;
    setAuthorizeUrl(config.auth_authorize_url || "");
    setTokenUrl(config.auth_token_url || "");
    setClientId(config.auth_client_id || "");
    setSyncMode(config.sync_mode || "bidirectional");
    setDeletePolicy(config.delete_policy || "safe");
    if (config.ignore_hidden_cache_paths != null) {
      setIgnoreHiddenCachePaths(Boolean(config.ignore_hidden_cache_paths));
    }
    setTokenStore(config.token_store || "keyring");
    if (config.upload_interval_value != null) setUploadValue(String(config.upload_interval_value));
    if (config.upload_interval_unit) setUploadUnit(config.upload_interval_unit);
    if (config.upload_daily_time) setUploadTime(config.upload_daily_time);
    if (config.download_interval_value != null) setDownloadValue(String(config.download_interval_value));
    if (config.download_interval_unit) setDownloadUnit(config.download_interval_unit);
    if (config.download_daily_time) setDownloadTime(config.download_daily_time);
    setDeviceDisplayName(config.device_display_name || "");
  }, [config, configLoading]);

  useEffect(() => {
    setIgnoredSubpathsMap((prev) => {
      const next: Record<string, string[]> = {};
      for (const task of tasks) {
        next[task.id] = prev[task.id] ?? task.ignored_subpaths ?? [];
      }
      return next;
    });
  }, [tasks]);

  const normalizeIgnoredSubpath = (value: string): string | null => {
    const normalized = value
      .replace(/\\/g, "/")
      .split("/")
      .map((segment) => segment.trim())
      .filter((segment) => segment && segment !== ".");
    if (!normalized.length) return null;
    if (normalized.some((segment) => segment === ".." || segment.includes(":"))) {
      return null;
    }
    return normalized.join("/");
  };

  const resolvePickedSubpath = (rootPath: string, pickedPath: string): string | null => {
    const normalizeFsPath = (value: string) =>
      value.replace(/\//g, "\\").replace(/[\\/]+$/, "");
    const root = normalizeFsPath(rootPath);
    const picked = normalizeFsPath(pickedPath);
    const rootLower = root.toLowerCase();
    const pickedLower = picked.toLowerCase();
    if (pickedLower === rootLower) return null;
    if (!pickedLower.startsWith(`${rootLower}\\`)) return null;
    const relative = picked.slice(root.length + 1).replace(/\\/g, "/");
    return normalizeIgnoredSubpath(relative);
  };

  const addIgnoredSubpath = (taskId: string, rawValue: string) => {
    const normalized = normalizeIgnoredSubpath(rawValue);
    if (!normalized) {
      toast("请输入本地同步目录下的有效子目录", "danger");
      return;
    }
    setIgnoredSubpathsMap((prev) => {
      const current = prev[taskId] ?? [];
      const normalizedLower = normalized.toLowerCase();
      if (
        current.some((item) => {
          const lower = item.toLowerCase();
          return lower === normalizedLower || normalizedLower.startsWith(`${lower}/`);
        })
      ) {
        return prev;
      }
      const filtered = current.filter((item) => !item.toLowerCase().startsWith(`${normalizedLower}/`));
      return { ...prev, [taskId]: [...filtered, normalized] };
    });
    setIgnoredPathDrafts((prev) => ({ ...prev, [taskId]: "" }));
  };

  const removeIgnoredSubpath = (taskId: string, target: string) => {
    setIgnoredSubpathsMap((prev) => ({
      ...prev,
      [taskId]: (prev[taskId] ?? []).filter((item) => item !== target),
    }));
  };

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
        delete_policy: deletePolicy,
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
    try {
      await saveConfig({
        ignore_hidden_cache_paths: ignoreHiddenCachePaths,
        device_display_name: deviceDisplayName.trim() || null,
      });
      toast("更多设置已保存", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "保存失败", "danger");
    }
  };

  const handleSaveAll = async () => {
    await handleSave();
    await handleSaveMoreSettings();
  };

  const handlePickIgnoredSubpath = async (taskId: string, localPath: string) => {
    setPickingIgnoredTaskId(taskId);
    try {
      const result = await apiFetch<{ path: string }>("/system/select-folder", { method: "POST" });
      const relative = resolvePickedSubpath(localPath, result.path);
      if (!relative) {
        toast("请选择当前任务本地同步目录下的子目录", "danger");
        return;
      }
      addIgnoredSubpath(taskId, relative);
    } catch (err) {
      toast(err instanceof Error ? err.message : "选择目录失败", "danger");
    } finally {
      setPickingIgnoredTaskId(null);
    }
  };

  const handleSaveIgnoredSubpaths = async (taskId: string) => {
    try {
      const updated = await updateIgnoredSubpaths({
        id: taskId,
        ignored_subpaths: ignoredSubpathsMap[taskId] ?? [],
      });
      setIgnoredSubpathsMap((prev) => ({
        ...prev,
        [taskId]: updated.ignored_subpaths ?? [],
      }));
      toast("忽略目录已保存", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "保存忽略目录失败", "danger");
    }
  };

  const inputCls = "h-9 w-full rounded-lg border border-[#c9d8eb] bg-white px-3 text-sm text-[#1f2d3d] outline-none transition placeholder:text-[#8fa1b7] focus:border-[#3370FF] focus:ring-2 focus:ring-[#3370FF]/15";

  return (
    <section className="min-w-0 space-y-4 animate-fade-up">
      <div className="flex min-w-0 flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-[#102033]">设置</h1>
          <p className="mt-1 text-sm text-[#52657A]">飞书账号、当前设备、默认同步策略和忽略规则。</p>
        </div>
        <button
          className="inline-flex h-9 items-center rounded-lg bg-[#3370FF] px-4 text-xs font-semibold text-white shadow-[0_10px_24px_rgba(51,112,255,0.22)] hover:bg-[#2563eb]"
          onClick={() => void handleSaveAll()}
          disabled={saving}
          type="button"
        >
          {saving ? "保存中" : "保存设置"}
        </button>
      </div>

      <div data-settings-context="true" className="grid grid-cols-[minmax(0,0.82fr)_minmax(0,1.18fr)] overflow-hidden rounded-xl border border-[#d7e4f5] bg-white shadow-[0_10px_28px_rgba(51,112,255,0.05)]">
        <div className="border-r border-[#d7e4f5] p-4">
          <div className="grid grid-cols-[112px_minmax(0,1fr)_auto] items-center gap-4">
          <h2 className="text-base font-semibold text-[#102033]">飞书账号</h2>
          <div className="flex min-w-0 items-center gap-4">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#ecfdf5] text-[#10b981]">
              <IconCircleCheck className="h-6 w-6" />
            </span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-[#102033]">{connected ? "飞书已连接" : "飞书未连接"}</p>
              <p className="mt-1 truncate text-xs text-[#6b7f96]">
                {connected ? `${accountName || "当前账号"} · ${driveOk ? "云空间权限正常" : "请检查云空间权限"}` : "请在高级 OAuth 中完成授权"}
              </p>
            </div>
          </div>
          <button
            className="inline-flex h-8 items-center gap-2 rounded-lg border border-[#c9d8eb] bg-white px-3 text-xs font-semibold text-[#52677f] hover:border-[#3370ff]/40 hover:text-[#3370ff]"
            onClick={() => logout()}
            type="button"
          >
            <IconLogout className="h-3.5 w-3.5" />
            {connected ? "登出设备" : "重新授权"}
          </button>
          </div>
        </div>
        <SettingsGeneralPanel
          embedded
          inputCls={inputCls}
          deviceDisplayName={deviceDisplayName}
          setDeviceDisplayName={setDeviceDisplayName}
          deviceId={deviceId}
        />
      </div>

      <SettingsSyncStrategyPanel
        syncMode={syncMode}
        setSyncMode={setSyncMode}
        uploadEnabled={uploadEnabled}
        downloadEnabled={downloadEnabled}
        uploadValue={uploadValue}
        setUploadValue={setUploadValue}
        uploadUnit={uploadUnit}
        setUploadUnit={setUploadUnit}
        uploadTime={uploadTime}
        setUploadTime={setUploadTime}
        downloadValue={downloadValue}
        setDownloadValue={setDownloadValue}
        downloadUnit={downloadUnit}
        setDownloadUnit={setDownloadUnit}
        downloadTime={downloadTime}
        setDownloadTime={setDownloadTime}
        handleSave={handleSave}
        saving={saving}
        deletePolicy={deletePolicy}
        setDeletePolicy={setDeletePolicy}
        showSaveAction={false}
      />

      <SettingsIgnoredDirectoriesPanel
        tasks={tasks}
        showIgnoredDirectorySettings={showIgnoredDirectorySettings}
        toggleIgnoredDirectorySettings={() => setShowIgnoredDirectorySettings((prev) => !prev)}
        ignoreHiddenCachePaths={ignoreHiddenCachePaths}
        setIgnoreHiddenCachePaths={setIgnoreHiddenCachePaths}
        ignoredSubpathsMap={ignoredSubpathsMap}
        ignoredPathDrafts={ignoredPathDrafts}
        setIgnoredPathDrafts={(updater) => setIgnoredPathDrafts(updater)}
        updatingIgnoredSubpaths={updatingIgnoredSubpaths}
        handleSaveIgnoredSubpaths={handleSaveIgnoredSubpaths}
        removeIgnoredSubpath={removeIgnoredSubpath}
        addIgnoredSubpath={addIgnoredSubpath}
        pickingIgnoredTaskId={pickingIgnoredTaskId}
        handlePickIgnoredSubpath={handlePickIgnoredSubpath}
      />

      <SettingsOAuthPanel
        clientId={clientId}
        setClientId={setClientId}
        clientSecret={clientSecret}
        setClientSecret={setClientSecret}
        redirectUri={redirectUri}
        copyRedirectUri={copyRedirectUri}
        handleSave={handleSave}
        saving={saving}
        saveError={saveError}
        showAdvanced={showAdvanced}
        toggleAdvanced={() => setShowAdvanced((prev) => !prev)}
        authorizeUrl={authorizeUrl}
        setAuthorizeUrl={setAuthorizeUrl}
        tokenUrl={tokenUrl}
        setTokenUrl={setTokenUrl}
        tokenStore={tokenStore}
        setTokenStore={setTokenStore}
        inputCls={inputCls}
        showSaveAction={false}
      />

    </section>
  );
}
