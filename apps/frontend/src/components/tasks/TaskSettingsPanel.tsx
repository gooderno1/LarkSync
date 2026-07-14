import { useEffect, useState } from "react";

import {
  mdSyncModeLabels,
  modeLabels,
  syncModeSupportsUpload,
  updateModeLabels,
} from "../../lib/constants";
import {
  buildTaskSettingsPatch,
  countTaskSettingsDraftChanges,
  createTaskSettingsDraft,
  getTaskSettingsRisk,
  type TaskSettingsDraft,
} from "../../lib/taskSettings";
import { deletePolicyLabel } from "../../lib/taskManagement";
import { cn } from "../../lib/utils";
import type { SyncTask } from "../../types";
import {
  IconArrowDown,
  IconArrowRightLeft,
  IconArrowUp,
  IconTrash,
} from "../Icons";

type TaskSettingsPanelProps = {
  task: SyncTask;
  processed: number;
  total: number;
  onClose: () => void;
  onDelete: () => void | Promise<void>;
  onDirtyChange?: (dirty: boolean) => void;
  onSave: (patch: Record<string, unknown>) => Promise<void>;
};

const syncModes = [
  { value: "download_only", label: "仅下载", desc: "云端到本地，不写入云端", Icon: IconArrowDown },
  { value: "bidirectional", label: "双向同步", desc: "本地与云端互相更新", Icon: IconArrowRightLeft },
  { value: "upload_only", label: "仅上传", desc: "本地到云端，会写入云端", Icon: IconArrowUp },
];

const deletePolicies = [
  { value: "off", label: "关闭联动", desc: "删除不传递" },
  { value: "safe", label: "安全删除", desc: "宽限后执行" },
  { value: "strict", label: "严格删除", desc: "立即执行" },
] as const;

export function TaskSettingsPanel({
  task,
  processed,
  total,
  onClose,
  onDelete,
  onDirtyChange,
  onSave,
}: TaskSettingsPanelProps) {
  const [draft, setDraft] = useState<TaskSettingsDraft>(() => createTaskSettingsDraft(task));
  const [baseline, setBaseline] = useState<TaskSettingsDraft>(() => createTaskSettingsDraft(task));
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    const next = createTaskSettingsDraft(task);
    setDraft(next);
    setBaseline(next);
    setSaveError(null);
  }, [task]);

  const uploadEnabled = syncModeSupportsUpload(draft.syncMode);
  const changeCount = countTaskSettingsDraftChanges(baseline, draft);
  const risk = getTaskSettingsRisk(draft.syncMode, draft.deletePolicy);

  useEffect(() => {
    onDirtyChange?.(changeCount > 0);
  }, [changeCount, onDirtyChange]);

  const updateDraft = <K extends keyof TaskSettingsDraft>(key: K, value: TaskSettingsDraft[K]) => {
    setDraft((current) => ({ ...current, [key]: value }));
    setSaveError(null);
  };

  const handleSave = async () => {
    if (changeCount === 0 || saving) return;
    setSaving(true);
    setSaveError(null);
    try {
      await onSave(buildTaskSettingsPatch(task, draft));
      setBaseline(draft);
    } catch {
      setSaveError("保存失败，请检查连接后重试。");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div data-task-settings-panel="true" className="overflow-hidden rounded-xl border border-[#bfd8ff] bg-white shadow-[0_14px_36px_rgba(51,112,255,0.08)]">
      <div className="flex items-center justify-between gap-4 border-b border-[#d7e4f5] px-5 py-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 id="task-settings-dialog-title" className="text-sm font-semibold text-[#102033]">任务设置</h3>
            <span className="text-[#c9d8ec]">·</span>
            <span className="truncate text-sm font-medium text-[#334762]">{task.name || "未命名任务"}</span>
          </div>
          <p className="mt-1 text-xs text-[#52657a]">调整内容流向、写入方式和删除联动，完成后统一保存。</p>
        </div>
        <button data-task-settings-close="true" aria-label="关闭任务设置" className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-[#c9d8ec] text-[#52657a] hover:bg-[#eef5ff] hover:text-[#3370ff] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3370ff]/40" onClick={onClose} type="button">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4"><path d="M18 6 6 18M6 6l12 12" /></svg>
        </button>
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)_272px] items-stretch">
        <div className="min-w-0 divide-y divide-[#edf3fb] px-5">
          <section className="py-3">
            <div className="mb-3"><h4 className="text-sm font-semibold text-[#102033]">内容流向</h4><p className="mt-1 text-xs text-[#52657a]">决定内容从哪里读取、是否允许写入云端。</p></div>
            <div className="grid grid-cols-3 gap-3" role="group" aria-label="内容流向">
              {syncModes.map(({ value, label, desc, Icon }) => (
                <button
                  key={value}
                  aria-pressed={draft.syncMode === value}
                  className={cn(
                    "flex min-h-[72px] items-start gap-3 rounded-xl border p-3 text-left transition",
                    draft.syncMode === value
                      ? "border-[#3370ff] bg-[#eef5ff] text-[#3370ff]"
                      : "border-[#d7e4f5] bg-white text-[#334762] hover:border-[#bfd8ff] hover:bg-[#f8fbff]",
                  )}
                  onClick={() => {
                    updateDraft("syncMode", value);
                    if (value === "download_only") updateDraft("mdSyncMode", "download_only");
                    else if (draft.mdSyncMode === "download_only") updateDraft("mdSyncMode", "enhanced");
                  }}
                  type="button"
                >
                  <Icon className="mt-0.5 h-4 w-4 shrink-0" />
                  <span><span className="block text-xs font-semibold">{label}</span><span className="mt-1 block text-[11px] leading-4 text-[#52657a]">{desc}</span></span>
                </button>
              ))}
            </div>
          </section>

          <section className="py-3">
            <div className="mb-3"><h4 className="text-sm font-semibold text-[#102033]">写入方式</h4><p className="mt-1 text-xs text-[#52657a]">控制文档更新粒度和 Markdown 上行行为。</p></div>
            <div className="grid grid-cols-2 gap-4">
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-[#52657a]">更新模式</span>
                <select className="h-9 w-full rounded-lg border border-[#c9d8ec] bg-white px-3 text-xs text-[#334762] outline-none focus:border-[#3370ff]" value={draft.updateMode} onChange={(event) => updateDraft("updateMode", event.target.value)}>
                  <option value="auto">自动：智能选择更新方式</option>
                  <option value="partial">局部：仅更新变更块</option>
                  <option value="full">全量：完整替换文档</option>
                </select>
              </label>
              {uploadEnabled ? (
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-[#52657a]">MD 上传模式</span>
                  <select className="h-9 w-full rounded-lg border border-[#c9d8ec] bg-white px-3 text-xs text-[#334762] outline-none focus:border-[#3370ff]" value={draft.mdSyncMode} onChange={(event) => updateDraft("mdSyncMode", event.target.value as TaskSettingsDraft["mdSyncMode"])}>
                    <option value="enhanced">增强 MD 上传</option>
                    <option value="download_only">MD 仅下载</option>
                    <option value="doc_only">仅云文档上传</option>
                  </select>
                </label>
              ) : (
                <div className="rounded-lg border border-dashed border-[#c9d8ec] bg-[#f8fbff] px-3 py-2.5">
                  <p className="text-xs font-medium text-[#334762]">MD 上传模式不适用</p>
                  <p className="mt-1 text-[11px] leading-4 text-[#52657a]">当前任务为仅下载，不会写入云端。</p>
                </div>
              )}
            </div>
          </section>

          <section className="py-3">
            <div className="mb-3"><h4 className="text-sm font-semibold text-[#102033]">删除联动</h4><p className="mt-1 text-xs text-[#52657a]">控制一端删除后是否影响另一端。</p></div>
            <div className="grid grid-cols-3 gap-3">
              {deletePolicies.map(({ value, label, desc }) => (
                <button
                  key={value}
                  aria-pressed={draft.deletePolicy === value}
                  className={cn(
                    "rounded-xl border p-3 text-left transition",
                    draft.deletePolicy === value
                      ? value === "strict"
                        ? "border-[#f43f5e]/55 bg-[#fff1f2] text-[#be123c]"
                        : "border-[#3370ff] bg-[#eef5ff] text-[#3370ff]"
                      : "border-[#d7e4f5] bg-white text-[#334762] hover:border-[#bfd8ff] hover:bg-[#f8fbff]",
                  )}
                  onClick={() => updateDraft("deletePolicy", value)}
                  type="button"
                >
                  <span className="block text-xs font-semibold">{label}</span><span className="mt-1 block text-[11px] text-[#52657a]">{desc}</span>
                </button>
              ))}
            </div>
            {draft.deletePolicy === "safe" ? (
              <label className="mt-3 flex max-w-[300px] items-center gap-3 text-xs text-[#52657a]">
                <span className="shrink-0 font-medium">删除宽限</span>
                <input className="h-9 w-24 rounded-lg border border-[#c9d8ec] bg-white px-3 text-xs text-[#334762] outline-none focus:border-[#3370ff]" type="number" min="0" step="1" value={draft.deleteGraceMinutes} onChange={(event) => updateDraft("deleteGraceMinutes", event.target.value)} />
                <span>分钟</span>
              </label>
            ) : null}
          </section>
        </div>

        <aside className="border-l border-[#d7e4f5] bg-[#f8fbff] p-4">
          <div className="flex items-center justify-between gap-3"><h4 className="text-sm font-semibold text-[#102033]">变更摘要</h4><span className={cn("rounded-full px-2.5 py-1 text-[11px] font-semibold", changeCount > 0 ? "bg-[#fff7ed] text-[#b45309]" : "bg-[#ecfdf5] text-[#047857]")}>{changeCount > 0 ? `${changeCount} 项待保存` : "尚未修改"}</span></div>
          <dl className="mt-4 space-y-3 text-xs">
            {[
              ["内容流向", modeLabels[draft.syncMode] || draft.syncMode],
              ["更新模式", updateModeLabels[draft.updateMode] || draft.updateMode],
              ["MD 模式", uploadEnabled ? mdSyncModeLabels[draft.mdSyncMode] : "不适用"],
              ["删除策略", deletePolicyLabel(draft.deletePolicy)],
            ].map(([label, value]) => <div key={label} className="flex justify-between gap-3"><dt className="text-[#52657a]">{label}</dt><dd className="text-right font-medium text-[#102033]">{value}</dd></div>)}
          </dl>
          <div className={cn("mt-4 rounded-lg border p-3", risk.tone === "safe" && "border-[#10b981]/25 bg-[#ecfdf5]", risk.tone === "warning" && "border-[#f59e0b]/35 bg-[#fffbeb]", risk.tone === "danger" && "border-[#f43f5e]/35 bg-[#fff1f2]")}>
            <p className={cn("text-xs font-semibold", risk.tone === "safe" ? "text-[#047857]" : risk.tone === "warning" ? "text-[#b45309]" : "text-[#be123c]")}>{risk.label}</p>
            <p className="mt-1 text-[11px] leading-5 text-[#52657a]">{risk.description}</p>
          </div>
          {saveError ? <p className="mt-3 text-xs text-[#be123c]">{saveError}</p> : null}
          <div className="mt-4 grid grid-cols-2 gap-2">
            <button className="rounded-lg border border-[#c9d8ec] px-3 py-2 text-xs font-semibold text-[#334762] hover:bg-white disabled:cursor-not-allowed disabled:opacity-40" disabled={changeCount === 0 || saving} onClick={() => { setDraft(baseline); setSaveError(null); }} type="button">放弃更改</button>
            <button className="rounded-lg bg-[#3370ff] px-3 py-2 text-xs font-semibold text-white hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:opacity-40" disabled={changeCount === 0 || saving} onClick={() => void handleSave()} type="button">{saving ? "保存中..." : "保存更改"}</button>
          </div>
          <details className="mt-4 border-t border-[#d7e4f5] pt-3">
            <summary className="cursor-pointer text-xs font-semibold text-[#52657a]">维护操作</summary>
            <button className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-[#f43f5e]/40 px-3 py-2 text-xs font-semibold text-[#be123c] hover:bg-[#fff1f2]" onClick={() => void onDelete()} type="button"><IconTrash className="h-3.5 w-3.5" />删除任务</button>
          </details>
        </aside>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#d7e4f5] bg-white px-5 py-3 text-[11px] text-[#52657a]">
        <span>基准路径：<span className="font-mono text-[#334762]">{task.base_path || "默认同本地目录"}</span></span>
        <span>最近处理：{processed}/{total}</span>
      </div>
    </div>
  );
}
