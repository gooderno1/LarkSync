import { useEffect, useMemo, useState } from "react";
import { useConfig } from "../hooks/useConfig";
import { useTasks } from "../hooks/useTasks";
import { useUpdate } from "../hooks/useUpdate";
import type { UpdateInstallHandoff, UpdateStatus } from "../hooks/useUpdate";
import { confirm } from "../components/ui/confirm-dialog";
import { useToast } from "../components/ui/toast";
import { IconFolder, IconMaintenance, IconRefresh } from "../components/Icons";

function formatAssetSize(size?: number): string {
  if (!size || size <= 0) return "—";
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`;
  if (size >= 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${size} B`;
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

export function MaintenancePage() {
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

  const handleSaveMaintenanceConfig = async () => {
    try {
      await saveConfig({
        sync_log_retention_days: Number.parseInt(syncLogRetentionDays, 10),
        system_log_retention_days: Number.parseInt(systemLogRetentionDays, 10),
        sync_log_warn_size_mb: Number.parseInt(syncLogWarnSizeMb, 10),
        auto_update_enabled: autoUpdateEnabled,
        update_check_interval_hours: Number.parseInt(updateCheckIntervalHours, 10),
      });
      toast("维护设置已保存", "success");
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
    <section className="animate-fade-up min-w-0 space-y-4">
      <div className="flex min-w-0 flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-[#102033]">更新与维护</h1>
          <p className="mt-1 text-sm text-[#52657A]">管理应用更新、安装交接、日志保留和系统维护工具。</p>
        </div>
        <button
          className="inline-flex h-9 items-center gap-2 rounded-lg bg-[#3370FF] px-4 text-xs font-semibold text-white shadow-[0_10px_24px_rgba(51,112,255,0.22)] hover:bg-[#2563eb]"
          onClick={handleCheckUpdate}
          disabled={checking}
          type="button"
        >
          <IconRefresh className={`h-3.5 w-3.5 ${checking ? "animate-spin" : ""}`} />
          {checking ? "检查中" : "检查更新"}
        </button>
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)_360px] gap-5">
        <div className="rounded-lg border border-[#d7e6ff] bg-white p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-[#102033]">更新流程</h2>
              <p className="mt-1 text-xs text-[#52657A]">检查、下载并安装 LarkSync Windows 更新包。</p>
            </div>
            <button
              className="inline-flex h-9 items-center gap-2 rounded-lg border border-[#bfd8ff] px-4 text-sm font-medium text-[#3370FF] hover:bg-[#eef5ff]"
              onClick={handleCheckUpdate}
              disabled={checking}
              type="button"
            >
              <IconRefresh className={`h-4 w-4 ${checking ? "animate-spin" : ""}`} />
              {checking ? "检查中" : "检查更新"}
            </button>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-4">
            <div className="rounded-xl border border-[#d7e6ff] bg-[#f8fbff] p-4">
              <p className="text-xs text-[#7a8da3]">当前版本</p>
              <p className="mt-1 text-xl font-semibold text-[#102033]">{status.current_version || "未知"}</p>
              <p className="mt-3 text-xs text-[#52657A]">上次检查：{lastCheckLabel}</p>
            </div>
            <div className="rounded-xl border border-[#d7e6ff] bg-[#f8fbff] p-4">
              <p className="text-xs text-[#7a8da3]">可用版本</p>
              <p className="mt-1 text-xl font-semibold text-[#102033]">{status.latest_version || "—"}</p>
              <p className="mt-3 text-xs text-[#52657A]">安装包：{status.asset?.name || "暂无"}</p>
            </div>
          </div>

          <div className="mt-5 rounded-xl border border-[#d7e6ff] bg-white p-4">
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div>
                <p className="text-xs text-[#7a8da3]">包大小</p>
                <p className="mt-1 font-medium text-[#102033]">{formatAssetSize(status.asset?.size)}</p>
              </div>
              <div>
                <p className="text-xs text-[#7a8da3]">下载路径</p>
                <p className="mt-1 truncate font-mono text-xs text-[#52657A]" title={status.download_path || undefined}>
                  {status.download_path || "尚未下载"}
                </p>
              </div>
              <div>
                <p className="text-xs text-[#7a8da3]">状态</p>
                <p className={`mt-1 font-medium ${status.update_available ? "text-[#F59E0B]" : "text-[#10B981]"}`}>
                  {status.update_available ? "发现新版本" : "已是最新"}
                </p>
              </div>
            </div>
            {status.last_error ? <p className="mt-3 text-xs text-[#F43F5E]">检查失败：{status.last_error}</p> : null}
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                className="h-9 rounded-lg bg-[#3370FF] px-4 text-sm font-semibold text-white hover:bg-[#2563eb] disabled:opacity-50"
                onClick={handleDownloadUpdate}
                disabled={!status.update_available || downloading || installing}
                type="button"
              >
                {downloading ? "下载中" : "下载更新"}
              </button>
              <button
                className="inline-flex h-9 items-center gap-2 rounded-lg border border-[#bfd8ff] px-4 text-sm font-medium text-[#3370FF] hover:bg-[#eef5ff] disabled:opacity-50"
                onClick={handleOpenFolder}
                disabled={openingUpdateFolder || !status.download_path}
                type="button"
              >
                <IconFolder className="h-4 w-4" />
                打开安装包目录
              </button>
              <button
                className="h-9 rounded-lg border border-[#10B981]/40 bg-[#ECFDF5] px-4 text-sm font-semibold text-[#047857] hover:bg-[#D1FAE5] disabled:opacity-50"
                onClick={handleInstallUpdate}
                disabled={installing || !status.download_path}
                type="button"
              >
                {installing ? "启动中" : "静默安装"}
              </button>
            </div>
          </div>

          <div className="mt-5 rounded-xl border border-[#d7e6ff] bg-[#f8fbff] p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-[#102033]">安装与交接</h3>
                <p className="mt-1 text-xs leading-5 text-[#52657A]">
                  读取本地安装请求和托盘 helper 回执，只展示已经确认的阶段。
                </p>
              </div>
              <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${installStepClassName(installStageTone)}`}>
                {getHandoffStageLabel(status.install_handoff)}
              </span>
            </div>
            <div className="mt-4 grid grid-cols-5 gap-3">
              {installTimeline.map((step, index) => (
                <div key={step.label} className={`rounded-lg border px-3 py-2 text-center text-xs ${installStepClassName(step.tone)}`}>
                  <span className="mx-auto mb-1 flex h-6 w-6 items-center justify-center rounded-full bg-white/70">
                    {index + 1}
                  </span>
                  <span className="block font-semibold">{step.label}</span>
                  <span className="mt-1 block text-[11px] opacity-80">{step.state}</span>
                </div>
              ))}
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-lg border border-[#d7e6ff] bg-white px-3 py-2">
                <p className="font-semibold text-[#102033]">安装请求</p>
                <p className="mt-1 truncate font-mono text-[#52657A]" title={status.install_request?.request_id || undefined}>
                  {status.install_request?.request_id || "暂无"}
                </p>
                <p className="mt-1 truncate font-mono text-[#52657A]" title={status.install_request?.installer_path || undefined}>
                  {status.install_request?.installer_path || "未排队安装包"}
                </p>
              </div>
              <div className="rounded-lg border border-[#d7e6ff] bg-white px-3 py-2">
                <p className="font-semibold text-[#102033]">helper 回执</p>
                <p className="mt-1 text-[#52657A]">时间：{formatInstallTimestamp(status.install_handoff?.timestamp)}</p>
                <p className="mt-1 break-words font-mono text-[#52657A]">
                  {status.install_handoff?.message || "暂无回执消息"}
                </p>
              </div>
            </div>
          </div>
        </div>

        <aside className="space-y-5">
          <div className="rounded-lg border border-[#d7e6ff] bg-white p-5">
            <h2 className="text-lg font-semibold text-[#102033]">日志保留</h2>
            <div className="mt-4 grid gap-3">
              <label className="text-xs font-medium text-[#52657A]">
                同步日志保留天数
                <input className="mt-1 w-full rounded-lg border border-[#bfd8ff] px-3 py-2 text-sm text-[#102033]" value={syncLogRetentionDays} onChange={(e) => setSyncLogRetentionDays(e.target.value)} type="number" min="0" />
              </label>
              <label className="text-xs font-medium text-[#52657A]">
                系统日志保留天数
                <input className="mt-1 w-full rounded-lg border border-[#bfd8ff] px-3 py-2 text-sm text-[#102033]" value={systemLogRetentionDays} onChange={(e) => setSystemLogRetentionDays(e.target.value)} type="number" min="1" />
              </label>
              <label className="text-xs font-medium text-[#52657A]">
                同步日志提醒阈值（MB）
                <input className="mt-1 w-full rounded-lg border border-[#bfd8ff] px-3 py-2 text-sm text-[#102033]" value={syncLogWarnSizeMb} onChange={(e) => setSyncLogWarnSizeMb(e.target.value)} type="number" min="0" />
              </label>
              <label className="flex items-center justify-between rounded-lg border border-[#d7e6ff] bg-[#f8fbff] px-3 py-2 text-sm text-[#52657A]">
                自动更新
                <input checked={autoUpdateEnabled} onChange={(e) => setAutoUpdateEnabled(e.target.checked)} type="checkbox" />
              </label>
              <label className="text-xs font-medium text-[#52657A]">
                更新检查间隔（小时）
                <input className="mt-1 w-full rounded-lg border border-[#bfd8ff] px-3 py-2 text-sm text-[#102033]" value={updateCheckIntervalHours} onChange={(e) => setUpdateCheckIntervalHours(e.target.value)} type="number" min="1" />
              </label>
              <button className="h-9 rounded-lg bg-[#3370FF] text-sm font-semibold text-white hover:bg-[#2563eb]" onClick={handleSaveMaintenanceConfig} disabled={saving} type="button">
                {saving ? "保存中" : "保存维护设置"}
              </button>
            </div>
          </div>

          <div className="rounded-lg border border-[#fecdd3] bg-[#fff8f9] p-5">
            <div className="flex items-center gap-2">
              <IconMaintenance className="h-5 w-5 text-[#F43F5E]" />
              <h2 className="text-lg font-semibold text-[#102033]">重置同步映射</h2>
            </div>
            <p className="mt-2 text-xs leading-5 text-[#52657A]">只清除映射关系，不删除本地或飞书文件。下次运行会重新扫描并建立映射。</p>
            <div className="mt-4 max-h-[260px] space-y-2 overflow-auto pr-1">
              {tasks.length === 0 ? (
                <p className="rounded-lg border border-[#d7e6ff] bg-white px-3 py-3 text-sm text-[#52657A]">暂无同步任务。</p>
              ) : (
                tasks.map((task) => (
                  <div key={task.id} className="rounded-lg border border-[#fecdd3] bg-white px-3 py-3">
                    <p className="truncate text-sm font-medium text-[#102033]">{task.name || "未命名任务"}</p>
                    <p className="mt-1 truncate font-mono text-[11px] text-[#52657A]">{task.local_path}</p>
                    <button
                      className="mt-2 h-8 rounded-lg border border-[#F43F5E]/40 px-3 text-xs font-semibold text-[#E11D48] hover:bg-[#fff1f2] disabled:opacity-50"
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
          </div>
        </aside>
      </div>
    </section>
  );
}
