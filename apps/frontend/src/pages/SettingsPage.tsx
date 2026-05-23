/* ------------------------------------------------------------------ */
/*  设置页面 — OAuth + 同步策略（优化设计）                               */
/* ------------------------------------------------------------------ */

import { useEffect, useMemo, useState } from "react";
import { useConfig } from "../hooks/useConfig";
import { useUpdate } from "../hooks/useUpdate";
import { useTasks } from "../hooks/useTasks";
import { syncModeSupportsDownload, syncModeSupportsUpload } from "../lib/constants";
import { apiFetch } from "../lib/api";
import { useToast } from "../components/ui/toast";
import { confirm } from "../components/ui/confirm-dialog";
import { ThemeToggle } from "../components/ThemeToggle";
import { SettingsOAuthPanel } from "../components/settings/SettingsOAuthPanel";
import { SettingsSyncStrategyPanel } from "../components/settings/SettingsSyncStrategyPanel";
import { SettingsMorePanel } from "../components/settings/SettingsMorePanel";
import { SettingsGeneralPanel } from "../components/settings/SettingsGeneralPanel";
import { SettingsUpdatePanel } from "../components/settings/SettingsUpdatePanel";
import { SettingsIgnoredDirectoriesPanel } from "../components/settings/SettingsIgnoredDirectoriesPanel";
import { SettingsMaintenancePanel } from "../components/settings/SettingsMaintenancePanel";

export function SettingsPage() {
  const { config, configLoading, saveConfig, saving, saveError } = useConfig();
  const {
    status,
    checkUpdate,
    checking,
    downloadUpdate,
    downloading,
    installUpdate,
    installing,
    openUpdateFolder,
    openingUpdateFolder,
  } = useUpdate();
  const { tasks, resetLinks, resettingLinks, updateIgnoredSubpaths, updatingIgnoredSubpaths } = useTasks();
  const { toast } = useToast();

  const [authorizeUrl, setAuthorizeUrl] = useState("");
  const [tokenUrl, setTokenUrl] = useState("");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [syncMode, setSyncMode] = useState("bidirectional");
  const [ignoreHiddenCachePaths, setIgnoreHiddenCachePaths] = useState(true);
  const [tokenStore, setTokenStore] = useState("keyring");
  const [uploadValue, setUploadValue] = useState("60");
  const [uploadUnit, setUploadUnit] = useState("seconds");
  const [uploadTime, setUploadTime] = useState("01:00");
  const [downloadValue, setDownloadValue] = useState("1");
  const [downloadUnit, setDownloadUnit] = useState("days");
  const [downloadTime, setDownloadTime] = useState("01:00");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showMoreSettings, setShowMoreSettings] = useState(false);
  const [showIgnoredDirectorySettings, setShowIgnoredDirectorySettings] = useState(false);
  const [syncLogRetentionDays, setSyncLogRetentionDays] = useState("0");
  const [syncLogWarnSizeMb, setSyncLogWarnSizeMb] = useState("200");
  const [systemLogRetentionDays, setSystemLogRetentionDays] = useState("1");
  const [autoUpdateEnabled, setAutoUpdateEnabled] = useState(false);
  const [updateCheckIntervalHours, setUpdateCheckIntervalHours] = useState("24");
  const [allowDevToStable, setAllowDevToStable] = useState(false);
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
    if (config.sync_log_retention_days != null) setSyncLogRetentionDays(String(config.sync_log_retention_days));
    if (config.sync_log_warn_size_mb != null) setSyncLogWarnSizeMb(String(config.sync_log_warn_size_mb));
    if (config.system_log_retention_days != null) setSystemLogRetentionDays(String(config.system_log_retention_days));
    if (config.auto_update_enabled != null) setAutoUpdateEnabled(Boolean(config.auto_update_enabled));
    if (config.update_check_interval_hours != null) setUpdateCheckIntervalHours(String(config.update_check_interval_hours));
    if (config.allow_dev_to_stable != null) setAllowDevToStable(Boolean(config.allow_dev_to_stable));
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
        ignore_hidden_cache_paths: ignoreHiddenCachePaths,
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
        const confirmed = await confirm({
          title: "安装已下载更新",
          description: `更新包已下载：\n${result.download_path}\n\n继续后 LarkSync 会退出并开始静默安装；安装向导界面不会出现，但 Windows 仍可能弹出系统权限确认。`,
          confirmLabel: "开始安装",
          tone: "warning",
        });
        if (confirmed) {
          await installUpdate(result.download_path);
          toast("正在开始静默安装，LarkSync 即将退出并在完成后自动重启", "success");
          return;
        }
        toast(`更新包已下载：${result.download_path}`, "success");
      } else {
        toast("更新包已下载", "success");
      }
    } catch (err) {
      toast(err instanceof Error ? err.message : "下载更新失败", "danger");
    }
  };

  const handleInstallDownloadedUpdate = async () => {
    const downloadPath = status.download_path;
    if (!downloadPath) {
      toast("尚未下载更新包", "danger");
      return;
    }
    const confirmed = await confirm({
      title: "静默安装已下载更新",
      description: `即将安装：\n${downloadPath}\n\n继续后 LarkSync 会退出并在完成后自动重启；安装向导界面不会出现，但 Windows 仍可能弹出系统权限确认。`,
      confirmLabel: "开始安装",
      tone: "warning",
    });
    if (!confirmed) return;
    try {
      await installUpdate(downloadPath);
      toast("正在开始静默安装，LarkSync 即将退出并在完成后自动重启", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "启动安装失败", "danger");
    }
  };

  const handleOpenDownloadedUpdateFolder = async () => {
    const downloadPath = status.download_path;
    if (!downloadPath) {
      toast("尚未下载更新包", "danger");
      return;
    }
    try {
      const result = await openUpdateFolder(downloadPath);
      toast(`已打开目录：${result.path}`, "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "打开目录失败", "danger");
    }
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

  const handleResetTask = async (task: (typeof tasks)[number]) => {
    const confirmed = await confirm({
      title: "重置同步映射",
      description: `任务：${task.name || task.id}\n\n此操作会清除该任务的 SyncLink 映射，下次同步将重新建立本地文件与飞书文件的对应关系。\n\n不会删除本地文件，也不会删除飞书文件。`,
      confirmLabel: "重置映射",
      tone: "warning",
    });
    if (!confirmed) return;
    try {
      const result = await resetLinks(task.id);
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
  };

  const inputCls = "w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-200 outline-none focus:border-[#3370FF] placeholder:text-zinc-600";

  return (
    <section className="space-y-6 animate-fade-up">
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
        themeSlot={<ThemeToggle />}
      />

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
      />

      <SettingsMorePanel
        showMoreSettings={showMoreSettings}
        toggleMoreSettings={() => setShowMoreSettings((prev) => !prev)}
        handleSaveMoreSettings={handleSaveMoreSettings}
        saving={saving}
      >
        <SettingsGeneralPanel
          inputCls={inputCls}
          deviceDisplayName={deviceDisplayName}
          setDeviceDisplayName={setDeviceDisplayName}
          syncLogRetentionDays={syncLogRetentionDays}
          setSyncLogRetentionDays={setSyncLogRetentionDays}
          syncLogWarnSizeMb={syncLogWarnSizeMb}
          setSyncLogWarnSizeMb={setSyncLogWarnSizeMb}
          systemLogRetentionDays={systemLogRetentionDays}
          setSystemLogRetentionDays={setSystemLogRetentionDays}
        />
        <SettingsUpdatePanel
          status={status}
          inputCls={inputCls}
          autoUpdateEnabled={autoUpdateEnabled}
          setAutoUpdateEnabled={setAutoUpdateEnabled}
          updateCheckIntervalHours={updateCheckIntervalHours}
          setUpdateCheckIntervalHours={setUpdateCheckIntervalHours}
          allowDevToStable={allowDevToStable}
          setAllowDevToStable={setAllowDevToStable}
          handleCheckUpdate={handleCheckUpdate}
          checking={checking}
          handleDownloadUpdate={handleDownloadUpdate}
          downloading={downloading}
          installing={installing}
          handleOpenDownloadedUpdateFolder={handleOpenDownloadedUpdateFolder}
          openingUpdateFolder={openingUpdateFolder}
          handleInstallDownloadedUpdate={handleInstallDownloadedUpdate}
          lastCheckLabel={lastCheckLabel}
          publishedLabel={publishedLabel}
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
        <SettingsMaintenancePanel
          tasks={tasks}
          resettingLinks={resettingLinks}
          onResetTask={handleResetTask}
        />
      </SettingsMorePanel>
    </section>
  );
}
