/* ------------------------------------------------------------------ */
/*  设置页面 — OAuth + 同步策略（优化设计）                               */
/* ------------------------------------------------------------------ */

import { useEffect, useState } from "react";
import { useConfig } from "../hooks/useConfig";
import { useTasks } from "../hooks/useTasks";
import { useAuth } from "../hooks/useAuth";
import { useAutostart } from "../hooks/useAutostart";
import { syncModeSupportsDownload, syncModeSupportsUpload } from "../lib/constants";
import { apiFetch } from "../lib/api";
import { useToast } from "../components/ui/toast";
import { SettingsSyncStrategyPanel } from "../components/settings/SettingsSyncStrategyPanel";
import { SettingsGeneralPanel } from "../components/settings/SettingsGeneralPanel";
import { SettingsIgnoredDirectoriesPanel } from "../components/settings/SettingsIgnoredDirectoriesPanel";
import { IconCircleCheck } from "../components/Icons";
import { SettingsShowcasePage } from "../components/showcase/RemainingPagesShowcase";
import { useRemainingPagesShowcase } from "../lib/remainingPagesShowcase";
import { useAccounts } from "../hooks/useAccounts";
import { AccountConnectPanel } from "../components/AccountConnectPanel";
import { SettingsAccountCard } from "../components/settings/SettingsAccountCard";
import { Switch } from "../components/ui/switch";
import { organizationDisplayName } from "../components/OrganizationAvatar";
import { TenantPermissionPanel, type TenantMetadataResult } from "../components/TenantPermissionPanel";

function SettingsLivePage() {
  const { config, configLoading, saveConfig, saving } = useConfig();
  const { tasks, updateIgnoredSubpaths, updatingIgnoredSubpaths } = useTasks();
  const { deviceId } = useAuth();
  const { accounts, activeAccount, switchAccount, refreshAccounts } = useAccounts();
  const { autostart, autostartLoading, setAutostart, updatingAutostart } = useAutostart();
  const { toast } = useToast();

  const [syncMode, setSyncMode] = useState("bidirectional");
  const [deletePolicy, setDeletePolicy] = useState<"off" | "safe" | "strict">("safe");
  const [ignoreHiddenCachePaths, setIgnoreHiddenCachePaths] = useState(true);
  const [uploadValue, setUploadValue] = useState("60");
  const [uploadUnit, setUploadUnit] = useState("seconds");
  const [uploadTime, setUploadTime] = useState("01:00");
  const [downloadValue, setDownloadValue] = useState("1");
  const [downloadUnit, setDownloadUnit] = useState("days");
  const [downloadTime, setDownloadTime] = useState("01:00");
  const [showIgnoredDirectorySettings, setShowIgnoredDirectorySettings] = useState(false);
  const [deviceDisplayName, setDeviceDisplayName] = useState("");
  const [ignoredPathDrafts, setIgnoredPathDrafts] = useState<Record<string, string>>({});
  const [ignoredSubpathsMap, setIgnoredSubpathsMap] = useState<Record<string, string[]>>({});
  const [pickingIgnoredTaskId, setPickingIgnoredTaskId] = useState<string | null>(null);
  const [reauthorizeAccountId, setReauthorizeAccountId] = useState<string | null>(null);
  const [refreshingAccountId, setRefreshingAccountId] = useState<string | null>(null);
  const [refreshingTenantAccountId, setRefreshingTenantAccountId] = useState<string | null>(null);
  const [tenantPermission, setTenantPermission] = useState<{ accountId: string; organizationName: string; permissionUrl: string } | null>(null);
  const uploadEnabled = syncModeSupportsUpload(syncMode);
  const downloadEnabled = syncModeSupportsDownload(syncMode);

  // populate from server data
  useEffect(() => {
    if (!config || configLoading) return;
    setSyncMode(config.sync_mode || "bidirectional");
    setDeletePolicy(config.delete_policy || "safe");
    if (config.ignore_hidden_cache_paths != null) {
      setIgnoreHiddenCachePaths(Boolean(config.ignore_hidden_cache_paths));
    }
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

  useEffect(() => {
    const requestedId = window.localStorage.getItem("larksync.reauthorize-account-id");
    if (!requestedId || !accounts.some((account) => account.id === requestedId)) return;
    window.localStorage.removeItem("larksync.reauthorize-account-id");
    setReauthorizeAccountId(requestedId);
  }, [accounts]);

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

  const handleAutostartChange = async (enabled: boolean) => {
    try {
      const status = await setAutostart(enabled);
      toast(status.enabled ? "已启用开机自启动" : "已关闭开机自启动", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "开机自启动设置失败", "danger");
    }
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
        sync_mode: syncMode,
        delete_policy: deletePolicy,
        upload_interval_value: uVal,
        upload_interval_unit: uploadUnit,
        upload_daily_time: uploadUnit === "days" ? uploadTime.trim() || null : null,
        download_interval_value: dVal,
        download_interval_unit: downloadUnit,
        download_daily_time: downloadUnit === "days" ? downloadTime.trim() || null : null,
      });
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

  const accountAction = async (accountId: string, action: "pause" | "resume" | "disconnect" | "remove") => {
    if (action === "remove" && !window.confirm("从本机移除此账号？任务与历史数据仍会保留，可重新登录恢复。")) return;
    try {
      await apiFetch(action === "remove" ? `/accounts/${accountId}` : `/accounts/${accountId}/${action}`, {
        method: action === "remove" ? "DELETE" : "POST",
      });
      await refreshAccounts();
      toast(action === "pause" ? "账号同步已暂停" : action === "resume" ? "账号同步已恢复" : action === "disconnect" ? "账号已从本机断开" : "账号已移除", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "账号操作失败", "danger");
    }
  };

  const refreshAccountAuthorization = async (accountId: string) => {
    setRefreshingAccountId(accountId);
    try {
      await apiFetch(`/accounts/${accountId}/refresh`, { method: "POST" });
      await refreshAccounts();
      toast("授权信息已刷新", "success");
    } catch (err) {
      await refreshAccounts();
      toast(err instanceof Error ? err.message : "授权刷新失败，请重新授权", "danger");
    } finally {
      setRefreshingAccountId(null);
    }
  };

  const refreshTenantMetadata = async (accountId: string) => {
    setRefreshingTenantAccountId(accountId);
    try {
      const result = await apiFetch<TenantMetadataResult>(`/accounts/${accountId}/tenant-metadata/refresh`, { method: "POST" });
      await refreshAccounts();
      if (result.status === "ready") {
        toast("组织信息已更新", "success");
      } else if (result.status === "permission_required") {
        const account = accounts.find((item) => item.id === accountId);
        const permissionUrl = result.permission_url || account?.tenant_permission_url;
        if (permissionUrl) {
          setTenantPermission({ accountId, organizationName: organizationDisplayName(account), permissionUrl });
        } else {
          toast("飞书未返回可安全使用的官方权限地址，请在开发者后台为当前应用开通组织信息只读权限。", "info");
        }
      } else if (result.status === "unavailable") {
        toast(result.message || "当前应用暂不支持读取组织信息，账号与同步功能可继续使用。", "info");
      } else {
        toast(result.message || "组织信息更新失败", "danger");
      }
    } catch (err) {
      toast(err instanceof Error ? err.message : "组织信息更新失败", "danger");
    } finally {
      setRefreshingTenantAccountId(null);
    }
  };

  const editAccountAlias = async (accountId: string, currentAlias?: string | null) => {
    const value = window.prompt("输入组织显示名；留空将恢复官方组织名称。", currentAlias || "");
    if (value === null) return;
    try {
      await apiFetch(`/accounts/${accountId}/display`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ account_alias: value.trim() || null }),
      });
      await refreshAccounts();
      toast(value.trim() ? "组织显示名已更新" : "已恢复官方组织名称", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "组织显示名更新失败", "danger");
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

  const inputCls = "h-9 w-full rounded-lg border border-[#c9d8eb] bg-white px-3 text-sm text-[#1f2d3d] outline-none transition placeholder:text-[#8fa1b7] focus:border-[#3370FF] focus:ring-2 focus:ring-[#3370FF]/15";

  return (
    <section data-settings-page="true" className="mx-auto min-w-0 max-w-[1440px] animate-fade-up">
      <div className="flex min-w-0 flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-[#102033]">设置</h1>
          <p className="mt-1 text-sm text-[#52657A]">管理飞书账号、当前设备、默认同步行为和本地规则。</p>
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

      <div
        data-settings-workspace="true"
        className="mt-5 grid min-w-0 grid-cols-1 items-start gap-4 min-[900px]:grid-cols-[minmax(0,1fr)_minmax(380px,420px)] min-[1200px]:gap-5"
      >
        <main data-settings-primary-column="true" className="min-w-0 space-y-4">
          <section data-settings-current-account="true" data-settings-account-panel="true" className="rounded-xl border border-[#d7e4f5] bg-white p-4 shadow-[0_10px_28px_rgba(51,112,255,0.05)]">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-base font-semibold text-[#102033]">当前飞书账号</h2>
                    <p className="mt-1 text-xs text-[#71869d]">当前视图与快捷操作作用于此账号，其他账号仍在后台独立同步。</p>
                  </div>
                  <button
                    className="inline-flex h-8 shrink-0 items-center gap-2 rounded-lg border border-[#c9d8eb] bg-white px-3 text-xs font-semibold text-[#52677f] hover:border-[#3370ff]/40 hover:text-[#3370ff]"
                    onClick={() => activeAccount && void accountAction(activeAccount.id, activeAccount.paused ? "resume" : "pause")}
                    type="button"
                  >
                    {activeAccount?.paused ? "恢复同步" : "暂停同步"}
                  </button>
                </div>
                <div className="mt-4 flex min-w-0 items-center gap-3 rounded-xl border border-[#e0eaf6] bg-[#f8fbff] px-4 py-3">
                    <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${activeAccount?.state === "connected" ? "bg-[#ecfdf5] text-[#10b981]" : "bg-[#fff1f2] text-[#f43f5e]"}`}>
                      <IconCircleCheck className="h-6 w-6" />
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-[#102033]">{activeAccount?.state === "connected" ? "飞书已连接" : "飞书需重新授权"}</p>
                      <p className="mt-1 truncate text-xs text-[#6b7f96]">
                        {organizationDisplayName(activeAccount)} · {activeAccount?.account_name || "飞书成员"} · {activeAccount?.auth_protocol === "device_v2" ? "Device Flow V2" : "OAuth V1 兼容"}
                      </p>
                    </div>
                </div>
                <div data-settings-autostart="true" className="mt-3 flex items-center justify-between gap-4 rounded-xl border border-[#d7e4f5] px-4 py-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-[#294662]">开机自启动</p>
                    <p className="mt-1 text-xs leading-5 text-[#71869d]">
                      {autostart?.supported ?? true
                        ? "登录当前系统账号后自动启动 LarkSync。开关立即生效，无需点击右上角按钮。"
                        : "当前系统暂不支持由 LarkSync 管理开机自启动。"}
                    </p>
                  </div>
                  <Switch
                    label="开机自启动"
                    checked={autostart?.enabled ?? false}
                    disabled={!(autostart?.supported ?? true) || autostartLoading || updatingAutostart}
                    onCheckedChange={(enabled) => void handleAutostartChange(enabled)}
                  />
                </div>
          </section>

          <section className="rounded-xl border border-[#d7e4f5] bg-white p-4 shadow-[0_10px_28px_rgba(51,112,255,0.05)]">
            <div><h2 className="text-base font-semibold text-[#102033]">账号管理</h2><p className="mt-1 text-xs text-[#58708d]">每个账号的凭据、任务、状态和通知相互隔离；暂停不会退出登录。</p></div>
            <div className="mt-4 grid gap-3">
              {accounts.map((account) => (
                <SettingsAccountCard
                  key={account.id}
                  account={account}
                  active={account.id === activeAccount?.id}
                  refreshing={refreshingAccountId === account.id}
                  refreshingTenant={refreshingTenantAccountId === account.id}
                  onSwitch={() => void switchAccount(account.id)}
                  onRefresh={() => void refreshAccountAuthorization(account.id)}
                  onRefreshTenant={() => void refreshTenantMetadata(account.id)}
                  onEditAlias={() => void editAccountAlias(account.id, account.account_alias)}
                  onReauthorize={() => setReauthorizeAccountId(account.id)}
                  onAction={(action) => void accountAction(account.id, action)}
                />
              ))}
            </div>
          </section>

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
        </main>

        <aside data-settings-auxiliary-column="true" className="min-w-0 space-y-4">
          <SettingsGeneralPanel
            inputCls={inputCls}
            deviceDisplayName={deviceDisplayName}
            setDeviceDisplayName={setDeviceDisplayName}
            deviceId={deviceId}
            platform={autostart?.platform}
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
          <section className="rounded-lg border border-[#b9e8d8] bg-[#f2fbf8] p-4">
            <div className="flex items-center gap-2 text-[#047857]">
              <IconCircleCheck className="h-5 w-5" />
              <h2 className="text-sm font-semibold">数据保护</h2>
            </div>
            <ul className="mt-3 space-y-1.5 text-xs leading-5 text-[#52657a]">
              <li>OAuth Token 存储于系统凭证库。</li>
              <li>云端内容作为冲突判断的事实来源。</li>
              <li>覆盖前保留冲突副本，避免静默丢失。</li>
            </ul>
          </section>
        </aside>
      </div>
      {reauthorizeAccountId ? <div className="fixed inset-0 z-[90] grid place-items-center overflow-y-auto bg-[#102033]/25 p-6 backdrop-blur-[2px]" onMouseDown={() => setReauthorizeAccountId(null)}><div className="w-full max-w-3xl rounded-3xl border border-[#d6e3f3] bg-[#f8fbff] p-6 shadow-2xl" onMouseDown={(event) => event.stopPropagation()}><div className="mb-5 flex items-center justify-between"><div><h2 className="text-xl font-semibold text-[#102033]">重新授权账号</h2><p className="mt-1 text-xs text-[#71869d]">成功后将切换到 Device Flow V2，账号数据保持不变。</p></div><button type="button" onClick={() => setReauthorizeAccountId(null)} className="rounded-lg border border-[#cbd9ea] px-3 py-1.5 text-sm text-[#52657a]">关闭</button></div><AccountConnectPanel mode="reauthorize" accountId={reauthorizeAccountId} onCancel={() => setReauthorizeAccountId(null)} onConnected={() => { setReauthorizeAccountId(null); toast("账号已重新授权并升级为 V2", "success"); }} /></div></div> : null}
      {tenantPermission ? <TenantPermissionPanel accountId={tenantPermission.accountId} organizationName={tenantPermission.organizationName} permissionUrl={tenantPermission.permissionUrl} onClose={() => setTenantPermission(null)} onResolved={async () => { await refreshAccounts(); toast("组织信息权限已开通", "success"); }} /> : null}
    </section>
  );
}

export function SettingsPage() {
  return useRemainingPagesShowcase() ? <SettingsShowcasePage /> : <SettingsLivePage />;
}
