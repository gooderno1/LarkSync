import { useEffect, useMemo, useState } from "react";
import { useConfig } from "../hooks/useConfig";
import { useTasks } from "../hooks/useTasks";
import { useUpdate } from "../hooks/useUpdate";
import type { UpdateInstallHandoff, UpdateStatus } from "../hooks/useUpdate";
import { confirm } from "../components/ui/confirm-dialog";
import { useToast } from "../components/ui/toast";
import { IconFolder, IconMaintenance, IconRefresh } from "../components/Icons";
import { MaintenanceShowcasePage } from "../components/showcase/RemainingPagesShowcase";
import { useRemainingPagesShowcase } from "../lib/remainingPagesShowcase";

function formatAssetSize(size?: number): string {
  if (!size || size <= 0) return "—";
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`;
  if (size >= 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${size} B`;
}

function updatePhaseLabel(phase?: string): string {
  if (phase === "checking") return "正在检查更新";
  if (phase === "downloading") return "正在下载安装包";
  if (phase === "verifying") return "下载完成，正在校验安全性";
  if (phase === "downloaded") return "安装包已下载并校验通过";
  if (phase === "error") return "更新未完成";
  if (phase === "available") return "发现新版本";
  if (phase === "up_to_date") return "已是最新版本";
  return "等待检查";
}

type InstallStepTone = "neutral" | "info" | "success" | "warning" | "danger";

type InstallTimelineStep = {
  label: string;
  state: string;
  tone: InstallStepTone;
};

const handoffStageLabels: Record<string, string> = {
  bootstrap_started: "托盘已拉起安装 worker",
  helper_started: "安装 helper 已接管",
  installer_started: "安装器已启动",
  launch_failed: "安装器启动失败",
  install_failed: "安装失败",
  install_succeeded: "安装完成",
  restart_succeeded: "自动重启已确认",
  restart_failed: "安装完成但重启未确认",
};

function formatInstallTimestamp(timestamp?: number | null): string {
  if (!timestamp) return "暂无";
  return new Date(timestamp * 1000).toLocaleString();
}

function getHandoffStageLabel(handoff?: UpdateInstallHandoff | null): string {
  const stage = handoff?.stage?.trim();
  if (!stage) return "暂无 handoff";
  return handoffStageLabels[stage] || stage;
}

function getHandoffStageTone(handoff?: UpdateInstallHandoff | null): InstallStepTone {
  const stage = handoff?.stage?.trim();
  if (!stage) return "neutral";
  if (stage === "launch_failed" || stage === "install_failed" || stage === "restart_failed") return "danger";
  if (stage === "bootstrap_started" || stage === "helper_started" || stage === "installer_started") return "info";
  if (stage === "install_succeeded") return "warning";
  if (stage === "restart_succeeded") return "success";
  return "neutral";
}

export function getInstallTimelineSteps(status: UpdateStatus): InstallTimelineStep[] {
  const request = status.install_request;
  const handoff = status.install_handoff;
  const stage = handoff?.stage?.trim() || "";
  const hasDownload = Boolean(status.download_path);
  const hasRequest = Boolean(request);
  const helperStages = new Set(["bootstrap_started", "helper_started", "installer_started", "install_succeeded", "restart_succeeded", "restart_failed"]);
  const installerStarted = ["installer_started", "install_succeeded", "restart_succeeded", "restart_failed"].includes(stage);
  const installDone = ["install_succeeded", "restart_succeeded", "restart_failed"].includes(stage);
  const restartDone = stage === "restart_succeeded";
  const failed = stage === "launch_failed" || stage === "install_failed" || stage === "restart_failed";

  return [
    {
      label: "校验通过",
      state: hasDownload ? "就绪" : "等待下载",
      tone: hasDownload ? "success" : "neutral",
    },
    {
      label: "托盘接管",
      state: hasRequest ? "已排队" : "等待确认",
      tone: hasRequest ? "info" : "neutral",
    },
    {
      label: "helper 启动",
      state: helperStages.has(stage) ? "已接管" : failed ? "未接管" : "等待",
      tone: helperStages.has(stage) ? "info" : failed ? "danger" : "neutral",
    },
    {
      label: "静默安装",
      state: installDone ? "已完成" : installerStarted ? "安装中" : stage === "install_failed" ? "失败" : "等待",
      tone: stage === "install_failed" ? "danger" : installDone ? "success" : installerStarted ? "info" : "neutral",
    },
    {
      label: "自动重启",
      state: restartDone ? "已确认" : stage === "restart_failed" ? "未确认" : "等待",
      tone: restartDone ? "success" : stage === "restart_failed" ? "danger" : "neutral",
    },
  ];
}

function installStepClassName(tone: InstallStepTone): string {
  if (tone === "success") return "border-[#10b981]/25 bg-[#ecfdf5] text-[#047857]";
  if (tone === "info") return "border-[#3370ff]/25 bg-[#eef5ff] text-[#1d4ed8]";
  if (tone === "warning") return "border-[#f59e0b]/35 bg-[#fffbeb] text-[#b45309]";
  if (tone === "danger") return "border-[#f43f5e]/30 bg-[#fff1f2] text-[#be123c]";
  return "border-[#d7e6ff] bg-white text-[#52657A]";
}

type UpdateActionVisibility = {
  showDownload: boolean;
  showOpenFolder: boolean;
  showInstall: boolean;
  disableDownload: boolean;
  disableInstall: boolean;
};

export function getUpdateActionVisibility(
  status: UpdateStatus,
  flags: { downloadActive: boolean; installing: boolean },
): UpdateActionVisibility {
  const hasDownload = Boolean(status.download_path?.trim());
  const packageReady = hasDownload && status.phase === "downloaded";

  return {
    showDownload: Boolean(status.update_available) && !packageReady,
    showOpenFolder: hasDownload,
    showInstall: packageReady,
    disableDownload: flags.downloadActive || flags.installing,
    disableInstall: flags.downloadActive || flags.installing,
  };
}

export function shouldAutoExpandInstallDetails(status: UpdateStatus, installing = false): boolean {
  if (installing) return true;
  const stage = status.install_handoff?.stage?.trim() || "";
  if (stage === "restart_succeeded") return false;
  if (
    [
      "bootstrap_started",
      "helper_started",
      "installer_started",
      "launch_failed",
      "install_failed",
      "install_succeeded",
      "restart_failed",
    ].includes(stage)
  ) {
    return true;
  }
  return Boolean(status.install_request);
}

function updateStatusClassName(status: UpdateStatus): string {
  if (status.last_error || status.phase === "error") {
    return "border-[#fecdd3] bg-[#fff7f8] text-[#be123c]";
  }
  if (status.update_available || status.phase === "available") {
    return "border-[#fde68a] bg-[#fffbeb] text-[#b45309]";
  }
  if (["checking", "downloading", "verifying"].includes(status.phase || "")) {
    return "border-[#bfd8ff] bg-[#f4f8ff] text-[#1d4ed8]";
  }
  if (status.phase === "downloaded") {
    return "border-[#a7f3d0] bg-[#ecfdf5] text-[#047857]";
  }
  if (status.phase === "up_to_date" || (status.last_check && !status.update_available)) {
    return "border-[#a7f3d0] bg-[#f2fbf7] text-[#047857]";
  }
  return "border-[#d7e6ff] bg-[#f8fbff] text-[#52657A]";
}

function MaintenanceLivePage() {
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
  const { config, saveConfig, saving } = useConfig();
  const { tasks, resetLinks, resettingLinks } = useTasks();
  const { toast } = useToast();
  const [syncLogRetentionDays, setSyncLogRetentionDays] = useState("0");
  const [systemLogRetentionDays, setSystemLogRetentionDays] = useState("1");
  const [syncLogWarnSizeMb, setSyncLogWarnSizeMb] = useState("200");
  const [autoUpdateEnabled, setAutoUpdateEnabled] = useState(false);
  const [updateCheckIntervalHours, setUpdateCheckIntervalHours] = useState("24");
  const [showResetMappings, setShowResetMappings] = useState(false);
  const [installDetailsExpanded, setInstallDetailsExpanded] = useState(false);
  const [installDetailsDismissed, setInstallDetailsDismissed] = useState(false);

  useEffect(() => {
    if (!config) return;
    if (config.sync_log_retention_days != null) setSyncLogRetentionDays(String(config.sync_log_retention_days));
    if (config.system_log_retention_days != null) setSystemLogRetentionDays(String(config.system_log_retention_days));
    if (config.sync_log_warn_size_mb != null) setSyncLogWarnSizeMb(String(config.sync_log_warn_size_mb));
    if (config.auto_update_enabled != null) setAutoUpdateEnabled(Boolean(config.auto_update_enabled));
    if (config.update_check_interval_hours != null) setUpdateCheckIntervalHours(String(config.update_check_interval_hours));
  }, [config]);

  const lastCheckLabel = useMemo(() => {
    if (!status.last_check) return "未检查";
    return new Date(status.last_check * 1000).toLocaleString();
  }, [status.last_check]);
  const installTimeline = useMemo(() => getInstallTimelineSteps(status), [status]);
  const installStageTone = getHandoffStageTone(status.install_handoff);
  const downloadActive = downloading || status.phase === "downloading" || status.phase === "verifying";
  const progress = status.progress;
  const checkActive = checking || status.phase === "checking";
  const updateActions = getUpdateActionVisibility(status, { downloadActive, installing });
  const autoExpandInstallDetails = shouldAutoExpandInstallDetails(status, installing);
  const installDetailsOpen = autoExpandInstallDetails
    ? !installDetailsDismissed
    : installDetailsExpanded;
  const installActivityKey = [
    status.install_request?.request_id || "",
    status.install_handoff?.request_id || "",
    status.install_handoff?.stage || "",
  ].join(":");

  useEffect(() => {
    setInstallDetailsDismissed(false);
  }, [installActivityKey]);

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
      toast(result.download_path ? `更新包已下载：${result.download_path}` : "更新包已下载", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "下载更新失败", "danger");
    }
  };

  const handleInstallUpdate = async () => {
    if (!status.download_path) {
      toast("尚未下载更新包", "danger");
      return;
    }
    const ok = await confirm({
      title: "静默安装更新",
      description: `即将安装：\n${status.download_path}\n\n继续后 LarkSync 会退出并由托盘 helper 接管安装，完成后自动重启。Windows 仍可能弹出权限确认。`,
      confirmLabel: "确认安装",
      tone: "warning",
    });
    if (!ok) return;
    try {
      await installUpdate(status.download_path);
      toast("静默安装已交给托盘接管", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "启动安装失败", "danger");
    }
  };

  const handleOpenFolder = async () => {
    try {
      const result = await openUpdateFolder(status.download_path || null);
      toast(`已打开目录：${result.path}`, "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "打开目录失败", "danger");
    }
  };

  const handleSaveUpdateConfig = async () => {
    try {
      await saveConfig({
        auto_update_enabled: autoUpdateEnabled,
        update_check_interval_hours: Number.parseInt(updateCheckIntervalHours, 10),
      });
      toast("更新设置已保存", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "保存失败", "danger");
    }
  };

  const handleSaveLogConfig = async () => {
    try {
      await saveConfig({
        sync_log_retention_days: Number.parseInt(syncLogRetentionDays, 10),
        system_log_retention_days: Number.parseInt(systemLogRetentionDays, 10),
        sync_log_warn_size_mb: Number.parseInt(syncLogWarnSizeMb, 10),
      });
      toast("日志设置已保存", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "保存失败", "danger");
    }
  };

  const handleResetTask = async (taskId: string, taskName: string) => {
    const ok = await confirm({
      title: "重置同步映射",
      description: `任务：${taskName}\n\n此操作会清除该任务的本地与云端映射关系。不会删除本地文件，也不会删除飞书文件。`,
      confirmLabel: "重置映射",
      tone: "warning",
    });
    if (!ok) return;
    try {
      const result = await resetLinks(taskId);
      toast(`已清除 ${result.deleted_links} 条同步映射`, "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "重置失败", "danger");
    }
  };

  return (
    <section data-maintenance-page="true" className="mx-auto min-w-0 w-full max-w-[1440px] animate-fade-up">
      <header className="min-w-0">
        <h1 className="text-xl font-semibold text-[#102033]">更新与维护</h1>
        <p className="mt-1 text-sm text-[#52657A]">管理应用更新、日志保留和本机维护工具。</p>
      </header>

      <div
        data-maintenance-workspace="true"
        className="mt-5 grid min-w-0 grid-cols-1 items-start gap-4 min-[900px]:grid-cols-[minmax(0,3fr)_minmax(360px,2fr)] min-[1200px]:gap-5"
      >
        <article
          data-maintenance-panel="version-install"
          className="flex min-w-0 flex-col rounded-xl border border-[#d7e4f5] bg-white p-5 shadow-[0_14px_34px_rgba(51,112,255,0.06)]"
        >
          <h2 className="text-lg font-semibold text-[#102033]">版本与安装</h2>

          <section className="mt-5 min-w-0">
            <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-base font-semibold text-[#102033]">版本与更新</h3>
                <p className="mt-1 text-xs text-[#52657A]">上次检查：{lastCheckLabel}</p>
              </div>
              <button
                data-maintenance-action="check-update"
                className="inline-flex h-9 shrink-0 items-center gap-2 rounded-lg border border-[#bfd8ff] bg-white px-4 text-sm font-semibold text-[#3370FF] transition hover:bg-[#eef5ff] disabled:cursor-not-allowed disabled:opacity-60"
                onClick={handleCheckUpdate}
                disabled={checkActive}
                type="button"
              >
                <IconRefresh className={`h-4 w-4 ${checkActive ? "animate-spin" : ""}`} />
                {checkActive ? "检查中" : "检查更新"}
              </button>
            </div>

            <div className="mt-5 grid grid-cols-3 divide-x divide-[#dce7f4] border-y border-[#dce7f4] py-4">
              <div className="min-w-0 px-4 first:pl-0">
                <p className="text-xs text-[#7a8da3]">当前版本</p>
                <p className="mt-2 truncate text-lg font-semibold text-[#102033]">{status.current_version || "未知"}</p>
              </div>
              <div className="min-w-0 px-4">
                <p className="text-xs text-[#7a8da3]">最新版本</p>
                <p className="mt-2 truncate text-lg font-semibold text-[#102033]">{status.latest_version || "—"}</p>
              </div>
              <div className="min-w-0 px-4 last:pr-0">
                <p className="text-xs text-[#7a8da3]">状态</p>
                <p
                  className={`mt-2 truncate text-sm font-semibold ${
                    status.update_available
                      ? "text-[#b45309]"
                      : status.last_check
                        ? "text-[#047857]"
                        : "text-[#52657A]"
                  }`}
                >
                  {status.update_available ? "发现新版本" : status.last_check ? "已是最新" : "等待检查"}
                </p>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-end gap-3 rounded-xl border border-[#d7e6ff] bg-[#f8fbff] p-4">
              <label className="flex min-w-[180px] flex-1 items-center justify-between gap-3 text-sm font-medium text-[#52657A]">
                <span>
                  自动更新
                  <span className={`ml-2 font-semibold ${autoUpdateEnabled ? "text-[#047857]" : "text-[#7a8da3]"}`}>
                    {autoUpdateEnabled ? "已开启" : "已关闭"}
                  </span>
                </span>
                <input
                  aria-label="自动更新"
                  checked={autoUpdateEnabled}
                  onChange={(event) => setAutoUpdateEnabled(event.target.checked)}
                  type="checkbox"
                />
              </label>
              <label className="min-w-[170px] flex-1 text-xs font-medium text-[#52657A]">
                检查间隔（小时）
                <input
                  className="mt-1 w-full rounded-lg border border-[#bfd8ff] bg-white px-3 py-2 text-sm text-[#102033]"
                  value={updateCheckIntervalHours}
                  onChange={(event) => setUpdateCheckIntervalHours(event.target.value)}
                  type="number"
                  min="1"
                />
              </label>
              <button
                className="h-9 shrink-0 rounded-lg border border-[#bfd8ff] bg-white px-4 text-sm font-semibold text-[#3370FF] hover:bg-[#eef5ff] disabled:opacity-60"
                onClick={handleSaveUpdateConfig}
                disabled={saving}
                type="button"
              >
                {saving ? "保存中" : "保存更新设置"}
              </button>
            </div>

            <div
              className={`mt-4 rounded-xl border p-4 ${updateStatusClassName(status)}`}
              aria-live="polite"
            >
              <p className="text-sm font-semibold">{updatePhaseLabel(status.phase)}</p>
              <p className="mt-1 text-xs leading-5 opacity-80">
                {status.last_error
                  ? `失败原因：${status.last_error}`
                  : status.update_available
                    ? `${status.asset?.name || "新版本安装包"}${status.asset?.size ? ` · ${formatAssetSize(status.asset.size)}` : ""}`
                    : status.last_check
                      ? "您的 LarkSync 已保持最新，无需更新。"
                      : "点击“检查更新”获取最新版本状态。"}
              </p>
              {status.download_path ? (
                <p className="mt-2 truncate font-mono text-[11px] opacity-75" title={status.download_path}>
                  {status.download_path}
                </p>
              ) : null}

              {progress && ["downloading", "verifying", "downloaded"].includes(status.phase || "") ? (
                <div className="mt-4 rounded-lg border border-current/15 bg-white/70 p-3">
                  <div className="flex items-start justify-between gap-4">
                    <p className="text-xs">
                      {formatAssetSize(progress.transferred)} / {formatAssetSize(progress.total)}
                      {status.phase === "downloading" ? ` · ${formatAssetSize(progress.bytes_per_second)}/s` : ""}
                    </p>
                    <strong className="text-base">{Math.round(progress.percent)}%</strong>
                  </div>
                  <div
                    className="mt-3 h-2 overflow-hidden rounded-full bg-[#dceaff]"
                    role="progressbar"
                    aria-label={updatePhaseLabel(status.phase)}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={Math.round(progress.percent)}
                  >
                    <span
                      className="block h-full rounded-full bg-[#3370ff] transition-[width] duration-300"
                      style={{ width: `${Math.max(0, Math.min(100, progress.percent))}%` }}
                    />
                  </div>
                </div>
              ) : null}
            </div>

            {updateActions.showDownload || updateActions.showOpenFolder || updateActions.showInstall ? (
              <div className="mt-4 flex flex-wrap gap-2">
                {updateActions.showDownload ? (
                  <button
                    className="h-9 rounded-lg bg-[#3370FF] px-4 text-sm font-semibold text-white hover:bg-[#2563eb] disabled:cursor-not-allowed disabled:opacity-60"
                    onClick={handleDownloadUpdate}
                    disabled={updateActions.disableDownload}
                    type="button"
                  >
                    {downloadActive
                      ? `下载中${progress ? ` ${Math.round(progress.percent)}%` : ""}`
                      : status.phase === "error"
                        ? "重新下载"
                        : "下载更新"}
                  </button>
                ) : null}
                {updateActions.showOpenFolder ? (
                  <button
                    className="inline-flex h-9 items-center gap-2 rounded-lg border border-[#bfd8ff] px-4 text-sm font-medium text-[#3370FF] hover:bg-[#eef5ff] disabled:opacity-60"
                    onClick={handleOpenFolder}
                    disabled={openingUpdateFolder}
                    type="button"
                  >
                    <IconFolder className="h-4 w-4" />
                    打开目录
                  </button>
                ) : null}
                {updateActions.showInstall ? (
                  <button
                    className="h-9 rounded-lg border border-[#10B981]/40 bg-[#ECFDF5] px-4 text-sm font-semibold text-[#047857] hover:bg-[#D1FAE5] disabled:opacity-60"
                    onClick={handleInstallUpdate}
                    disabled={updateActions.disableInstall}
                    type="button"
                  >
                    {installing ? "启动中" : "静默安装"}
                  </button>
                ) : null}
              </div>
            ) : null}
          </section>

          <section data-maintenance-section="install-details" className="mt-5 border-t border-[#dce7f4] pt-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-3">
                  <h3 className="text-base font-semibold text-[#102033]">安装详情</h3>
                  <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${installStepClassName(installStageTone)}`}>
                    {getHandoffStageLabel(status.install_handoff)}
                  </span>
                </div>
                <p className="mt-1 text-xs text-[#52657A]">
                  最近状态：{formatInstallTimestamp(status.install_handoff?.timestamp)}
                </p>
              </div>
              <button
                aria-expanded={installDetailsOpen}
                className="h-9 rounded-lg border border-[#bfd8ff] bg-white px-4 text-sm font-medium text-[#335f91] hover:bg-[#f4f8ff]"
                onClick={() => {
                  if (autoExpandInstallDetails) {
                    setInstallDetailsDismissed((value) => !value);
                  } else {
                    setInstallDetailsExpanded((value) => !value);
                  }
                }}
                type="button"
              >
                {installDetailsOpen ? "收起安装详情" : "查看安装详情"}
              </button>
            </div>

            {installDetailsOpen ? (
              <div className="mt-4" data-install-details-open="true">
                <p className="text-xs leading-5 text-[#52657A]">
                  读取本地安装请求和托盘 helper 回执，只展示已经确认的阶段。
                </p>
                <div className="mt-3 grid grid-cols-5 gap-2">
                  {installTimeline.map((step, index) => (
                    <div
                      key={step.label}
                      className={`rounded-lg border px-2 py-2 text-center text-xs ${installStepClassName(step.tone)}`}
                    >
                      <span className="mx-auto mb-1 flex h-6 w-6 items-center justify-center rounded-full bg-white/70">
                        {index + 1}
                      </span>
                      <span className="block font-semibold">{step.label}</span>
                      <span className="mt-1 block text-[11px] opacity-80">{step.state}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
                  <div className="rounded-lg bg-[#f8fbff] px-3 py-3">
                    <p className="font-semibold text-[#102033]">安装请求</p>
                    <p className="mt-1 truncate font-mono text-[#52657A]" title={status.install_request?.request_id || undefined}>
                      {status.install_request?.request_id || "暂无"}
                    </p>
                    <p className="mt-1 truncate font-mono text-[#52657A]" title={status.install_request?.installer_path || undefined}>
                      {status.install_request?.installer_path || "未排队安装包"}
                    </p>
                  </div>
                  <div className="rounded-lg bg-[#f8fbff] px-3 py-3">
                    <p className="font-semibold text-[#102033]">helper 回执</p>
                    <p className="mt-1 text-[#52657A]">时间：{formatInstallTimestamp(status.install_handoff?.timestamp)}</p>
                    <p className="mt-1 break-words font-mono text-[#52657A]">
                      {status.install_handoff?.message || "暂无回执消息"}
                    </p>
                  </div>
                </div>
              </div>
            ) : null}
          </section>
        </article>

        <aside
          data-maintenance-panel="local-maintenance"
          className="flex min-w-0 flex-col rounded-xl border border-[#d7e4f5] bg-white p-5 shadow-[0_14px_34px_rgba(51,112,255,0.06)]"
        >
          <h2 className="text-lg font-semibold text-[#102033]">本机维护</h2>

          <section data-maintenance-section="log-management" className="mt-5">
            <h3 className="text-base font-semibold text-[#102033]">日志管理</h3>
            <div className="mt-4 grid gap-3">
              <label className="text-xs font-medium text-[#52657A]">
                同步日志保留天数
                <input
                  className="mt-1 w-full rounded-lg border border-[#bfd8ff] px-3 py-2.5 text-sm text-[#102033]"
                  value={syncLogRetentionDays}
                  onChange={(event) => setSyncLogRetentionDays(event.target.value)}
                  type="number"
                  min="0"
                />
              </label>
              <label className="text-xs font-medium text-[#52657A]">
                系统日志保留天数
                <input
                  className="mt-1 w-full rounded-lg border border-[#bfd8ff] px-3 py-2.5 text-sm text-[#102033]"
                  value={systemLogRetentionDays}
                  onChange={(event) => setSystemLogRetentionDays(event.target.value)}
                  type="number"
                  min="1"
                />
              </label>
              <label className="text-xs font-medium text-[#52657A]">
                日志提醒阈值（MB）
                <input
                  className="mt-1 w-full rounded-lg border border-[#bfd8ff] px-3 py-2.5 text-sm text-[#102033]"
                  value={syncLogWarnSizeMb}
                  onChange={(event) => setSyncLogWarnSizeMb(event.target.value)}
                  type="number"
                  min="0"
                />
              </label>
              <button
                className="mt-1 h-10 rounded-lg bg-[#3370FF] text-sm font-semibold text-white hover:bg-[#2563eb] disabled:opacity-60"
                onClick={handleSaveLogConfig}
                disabled={saving}
                type="button"
              >
                {saving ? "保存中" : "保存日志设置"}
              </button>
            </div>
          </section>

          <section
            data-maintenance-danger="true"
            data-maintenance-section="danger"
            className="mt-5 border-t border-[#f3d4da] pt-5"
          >
            <div className="flex items-center gap-2 text-[#e11d48]">
              <IconMaintenance className="h-5 w-5" />
              <h3 className="text-base font-semibold">危险操作</h3>
            </div>
            <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-[220px] flex-1">
                <h4 className="text-sm font-semibold text-[#102033]">重置同步映射</h4>
                <p className="mt-2 text-xs leading-5 text-[#52657A]">
                  此操作将清除本地映射关系并解除同步绑定，不会删除本地或飞书文件。下次同步会重新扫描。
                </p>
              </div>
              <button
                aria-expanded={showResetMappings}
                className="h-9 shrink-0 rounded-lg border border-[#f43f5e]/45 bg-white px-4 text-sm font-semibold text-[#e11d48] hover:bg-[#fff1f2]"
                onClick={() => setShowResetMappings((value) => !value)}
                type="button"
              >
                {showResetMappings ? "收起任务" : "选择任务"}
              </button>
            </div>
            {showResetMappings ? (
              <div className="mt-4 space-y-2">
                {tasks.length === 0 ? (
                  <p className="rounded-lg bg-[#f8fbff] px-3 py-3 text-sm text-[#52657A]">暂无同步任务。</p>
                ) : (
                  tasks.map((task) => (
                    <div key={task.id} className="rounded-lg border border-[#fecdd3] bg-[#fffafb] px-3 py-3">
                      <p className="truncate text-sm font-medium text-[#102033]">{task.name || "未命名任务"}</p>
                      <p className="mt-1 truncate font-mono text-[11px] text-[#52657A]">{task.local_path}</p>
                      <button
                        className="mt-2 h-8 rounded-lg border border-[#F43F5E]/40 bg-white px-3 text-xs font-semibold text-[#E11D48] hover:bg-[#fff1f2] disabled:opacity-50"
                        disabled={resettingLinks}
                        onClick={() => void handleResetTask(task.id, task.name || task.id)}
                        type="button"
                      >
                        重置映射
                      </button>
                    </div>
                  ))
                )}
              </div>
            ) : null}
          </section>
        </aside>
      </div>
    </section>
  );
}

export function MaintenancePage() {
  return useRemainingPagesShowcase() ? <MaintenanceShowcasePage /> : <MaintenanceLivePage />;
}
