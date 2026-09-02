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
import { confirm } from "../components/ui/confirm-dialog";
import { NameEditDialog } from "../components/ui/name-edit-dialog";
import { SettingsSyncStrategyPanel } from "../components/settings/SettingsSyncStrategyPanel";
import { SettingsGeneralPanel } from "../components/settings/SettingsGeneralPanel";
import { SettingsIgnoredDirectoriesPanel } from "../components/settings/SettingsIgnoredDirectoriesPanel";
import { IconCircleCheck } from "../components/Icons";
import { SettingsShowcasePage } from "../components/showcase/RemainingPagesShowcase";
import { useRemainingPagesShowcase } from "../lib/remainingPagesShowcase";
import { useAccounts } from "../hooks/useAccounts";
import { AccountConnectPanel } from "../components/AccountConnectPanel";
import { SettingsAccountCard } from "../components/settings/SettingsAccountCard";
import { SettingsAppProfilesPanel } from "../components/settings/SettingsAppProfilesPanel";
import { Switch } from "../components/ui/switch";
import { organizationDisplayName } from "../components/OrganizationAvatar";
import { useAppProfiles } from "../hooks/useAppProfiles";
import type { AppProfile } from "../types";

type NameEditTarget = {
  kind: "account" | "profile";
  id: string;
  title: string;
  description: string;
  label: string;
  value: string;
};

function SettingsLivePage() {
  const { config, configLoading, saveConfig, saving } = useConfig();
  const { tasks, updateIgnoredSubpaths, updatingIgnoredSubpaths } = useTasks();
  const { deviceId } = useAuth();
  const { accounts, activeAccount, switchAccount, refreshAccounts } = useAccounts();
  const { profiles, refreshProfiles } = useAppProfiles();
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
  const [addAccountOpen, setAddAccountOpen] = useState(false);
  const [refreshingAccountId, setRefreshingAccountId] = useState<string | null>(null);
  const [expandedAccountId, setExpandedAccountId] = useState<string | null>(null);
  const [nameEditTarget, setNameEditTarget] = useState<NameEditTarget | null>(null);
  const [nameEditValue, setNameEditValue] = useState("");
  const [nameEditSaving, setNameEditSaving] = useState(false);
  const [nameEditError, setNameEditError] = useState<string | null>(null);
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
    if (action === "remove") {
      const account = accounts.find((item) => item.id === accountId);
      const accepted = await confirm({
        title: `从本机移除“${organizationDisplayName(account)}”？`,
        description: "该账号会停止同步并清除本机登录凭据。任务、同步历史、映射、问题和本地文件都会保留。以后选用同一个应用配置并由同一个飞书账号扫码，可以恢复原账号和数据。",
        confirmLabel: "移除账号",
        cancelLabel: "取消",
        tone: "danger",
      });
      if (!accepted) return;
    }
    try {
      await apiFetch(action === "remove" ? `/accounts/${accountId}` : `/accounts/${accountId}/${action}`, {
        method: action === "remove" ? "DELETE" : "POST",
      });
      await Promise.all([refreshAccounts(), refreshProfiles()]);
      toast(action === "pause" ? "账号同步已暂停" : action === "resume" ? "账号同步已恢复" : action === "disconnect" ? "账号已从本机断开" : "已从本机移除，任务与历史数据已保留", "success");
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

  const editAccountAlias = (accountId: string) => {
    const account = accounts.find((item) => item.id === accountId);
    const value = organizationDisplayName(account);
    setNameEditValue(value);
    setNameEditError(null);
    setNameEditTarget({
      kind: "account",
      id: accountId,
      title: "修改组织名称",
      description: "只改变 LarkSync 中的显示，不修改飞书组织，也不影响权限和数据隔离。",
      label: "组织名称",
      value,
    });
  };

  const editAppProfile = (profile: AppProfile) => {
    const value = profile.display_name || "";
    setNameEditValue(value);
    setNameEditError(null);
    setNameEditTarget({
      kind: "profile",
      id: profile.id,
      title: "修改应用名称",
      description: "名称只用于在 LarkSync 中区分不同 App ID，不会修改飞书后台显示的应用名称。",
      label: "应用名称",
      value,
    });
  };

  const saveEditedName = async () => {
    if (!nameEditTarget || !nameEditValue.trim()) return;
    setNameEditSaving(true);
    setNameEditError(null);
    try {
      await apiFetch(
        nameEditTarget.kind === "account"
          ? `/accounts/${nameEditTarget.id}/display`
          : `/app-profiles/${nameEditTarget.id}/display`,
        {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          nameEditTarget.kind === "account"
            ? { account_alias: nameEditValue.trim() }
            : { display_name: nameEditValue.trim() },
        ),
      });
      await Promise.all([refreshAccounts(), refreshProfiles()]);
      toast(nameEditTarget.kind === "account" ? "组织名称已更新" : "应用名称已更新", "success");
      setNameEditTarget(null);
    } catch (err) {
      setNameEditError(err instanceof Error ? err.message : "名称更新失败");
    } finally {
      setNameEditSaving(false);
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
          <p className="mt-1 text-sm text-[#52657A]">管理账号、应用、本机与默认同步规则。</p>
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
        className="mt-5 grid min-w-0 grid-cols-1 items-start gap-4 min-[900px]:grid-cols-[minmax(0,7fr)_minmax(340px,5fr)] min-[1200px]:gap-5"
      >
        <main data-settings-primary-column="true" className="min-w-0 space-y-4">
          <section data-settings-account-panel="true" className="rounded-xl border border-[#d7e4f5] bg-white p-4 shadow-[0_10px_28px_rgba(51,112,255,0.05)]">
            <div><h2 className="text-base font-semibold text-[#102033]">账号管理</h2><p className="mt-1 text-xs text-[#58708d]">每个账号的凭据、任务、状态和通知相互隔离；暂停不会退出登录。</p></div>
            <div className="mt-4 grid gap-3">
              {accounts.map((account) => (
                <SettingsAccountCard
                  key={account.id}
                  account={account}
                  active={account.id === activeAccount?.id}
                  expanded={expandedAccountId === account.id}
                  refreshing={refreshingAccountId === account.id}
                  onToggle={() => setExpandedAccountId((current) => current === account.id ? null : account.id)}
                  onSwitch={() => void switchAccount(account.id)}
                  onRefresh={() => void refreshAccountAuthorization(account.id)}
                  onEditAlias={() => editAccountAlias(account.id)}
                  onReauthorize={() => setReauthorizeAccountId(account.id)}
                  onAction={(action) => void accountAction(account.id, action)}
                />
              ))}
            </div>
            <button type="button" onClick={() => setAddAccountOpen(true)} className="mt-3 h-10 w-full rounded-xl border border-dashed border-[#9fc0ee] text-sm font-semibold text-[#3370ff] hover:bg-[#f5f9ff]">＋ 添加飞书组织或账号</button>
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
          <section className="rounded-xl border border-[#d7e4f5] bg-white p-4 shadow-[0_10px_28px_rgba(51,112,255,0.05)]">
            <SettingsGeneralPanel
              inputCls={inputCls}
              deviceDisplayName={deviceDisplayName}
              setDeviceDisplayName={setDeviceDisplayName}
              deviceId={deviceId}
              platform={autostart?.platform}
              embedded
            />
            <div data-settings-autostart="true" className="mt-4 flex items-center justify-between gap-4 border-t border-[#e4edf8] pt-4">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-[#294662]">开机自启动</p>
                <p className="mt-1 text-xs leading-5 text-[#71869d]">
                  {autostart?.supported ?? true
                    ? "登录当前系统账号后自动启动 LarkSync。开关立即生效。"
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
          <SettingsAppProfilesPanel
            profiles={profiles}
            activeProfileId={activeAccount?.app_profile_id}
            onEdit={editAppProfile}
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
      <NameEditDialog
        open={Boolean(nameEditTarget)}
        title={nameEditTarget?.title || "修改名称"}
        description={nameEditTarget?.description || ""}
        label={nameEditTarget?.label || "名称"}
        value={nameEditValue}
        saving={nameEditSaving}
        error={nameEditError}
        onChange={setNameEditValue}
        onCancel={() => { setNameEditTarget(null); setNameEditError(null); }}
        onSave={() => void saveEditedName()}
      />
      {addAccountOpen ? <div className="fixed inset-0 z-[90] grid place-items-center overflow-y-auto bg-[#102033]/25 p-6 backdrop-blur-[2px]" onMouseDown={() => setAddAccountOpen(false)}><div className="w-full max-w-3xl rounded-3xl border border-[#d6e3f3] bg-[#f8fbff] p-6 shadow-2xl" onMouseDown={(event) => event.stopPropagation()}><div className="mb-5 flex items-center justify-between"><div><h2 className="text-xl font-semibold text-[#102033]">添加飞书组织或账号</h2><p className="mt-1 text-xs text-[#71869d]">应用名称、账号凭据、任务和状态会独立保存。</p></div><button type="button" onClick={() => setAddAccountOpen(false)} className="rounded-lg border border-[#cbd9ea] px-3 py-1.5 text-sm text-[#52657a]">关闭</button></div><AccountConnectPanel onCancel={() => setAddAccountOpen(false)} onConnected={() => { setAddAccountOpen(false); void refreshProfiles(); toast("账号已连接", "success"); }} /></div></div> : null}
      {reauthorizeAccountId ? <div className="fixed inset-0 z-[90] grid place-items-center overflow-y-auto bg-[#102033]/25 p-6 backdrop-blur-[2px]" onMouseDown={() => setReauthorizeAccountId(null)}><div className="w-full max-w-3xl rounded-3xl border border-[#d6e3f3] bg-[#f8fbff] p-6 shadow-2xl" onMouseDown={(event) => event.stopPropagation()}><div className="mb-5 flex items-center justify-between"><div><h2 className="text-xl font-semibold text-[#102033]">重新授权账号</h2><p className="mt-1 text-xs text-[#71869d]">成功后将切换到 Device Flow V2，账号数据保持不变。</p></div><button type="button" onClick={() => setReauthorizeAccountId(null)} className="rounded-lg border border-[#cbd9ea] px-3 py-1.5 text-sm text-[#52657a]">关闭</button></div><AccountConnectPanel mode="reauthorize" accountId={reauthorizeAccountId} onCancel={() => setReauthorizeAccountId(null)} onConnected={() => { setReauthorizeAccountId(null); toast("账号已重新授权并升级为 V2", "success"); }} /></div></div> : null}
    </section>
  );
}

export function SettingsPage() {
  return useRemainingPagesShowcase() ? <SettingsShowcasePage /> : <SettingsLivePage />;
}
