/* ------------------------------------------------------------------ */
/*  新建同步任务弹窗 — 分步向导 (Step 1/2/3) 优化版                      */
/* ------------------------------------------------------------------ */

import { useState } from "react";
import { createPortal } from "react-dom";
import { apiFetch } from "../lib/api";
import { useDriveTree } from "../hooks/useDriveTree";
import { useAuth } from "../hooks/useAuth";
import { modeLabels, updateModeLabels } from "../lib/constants";
import { TreeNode } from "./TreeNode";
import { IconRefresh, IconFolder, IconCloud, IconArrowRightLeft, IconArrowDown, IconArrowUp } from "./Icons";
import { useToast } from "./ui/toast";
import { cn } from "../lib/utils";
import type { CloudSelection } from "../types";

type Props = {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
};

export function NewTaskModal({ open, onClose, onCreated }: Props) {
  const { connected } = useAuth();
  const { tree, treeLoading, treeError, refreshTree } = useDriveTree(open && connected);
  const { toast } = useToast();

  const [step, setStep] = useState(1);
  const [taskName, setTaskName] = useState("");
  const [taskLocalPath, setTaskLocalPath] = useState("");
  const [taskBasePath, setTaskBasePath] = useState("");
  const [taskCloudToken, setTaskCloudToken] = useState("");
  const [selectedCloud, setSelectedCloud] = useState<CloudSelection | null>(null);
  const [manualCloudInput, setManualCloudInput] = useState("");
  const [manualCloudName, setManualCloudName] = useState("");
  const [manualCloudError, setManualCloudError] = useState<string | null>(null);
  const [taskSyncMode, setTaskSyncMode] = useState("bidirectional");
  const [taskUpdateMode, setTaskUpdateMode] = useState("auto");
  const [taskEnabled, setTaskEnabled] = useState(true);
  const [folderPickLoading, setFolderPickLoading] = useState(false);
  const [folderPickError, setFolderPickError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const pickLocalFolder = () => {
    setFolderPickLoading(true);
    setFolderPickError(null);
    apiFetch<{ path: string }>("/system/select-folder", { method: "POST" })
      .then((data) => {
        if (data?.path) {
          setTaskLocalPath(data.path);
          if (!taskBasePath.trim()) setTaskBasePath(data.path);
        }
      })
      .catch((err: Error) => setFolderPickError(err.message))
      .finally(() => setFolderPickLoading(false));
  };

  const selectCloudFolder = (sel: CloudSelection) => {
    setSelectedCloud(sel);
    setTaskCloudToken(sel.token);
  };

  const extractFolderToken = (value: string): string | null => {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const urlMatch = trimmed.match(/folder\/([A-Za-z0-9_-]+)(?:[/?#]|$)/);
    if (urlMatch) return urlMatch[1];
    if (/^[A-Za-z0-9_-]+$/.test(trimmed)) return trimmed;
    return null;
  };

  const applyManualCloud = () => {
    const token = extractFolderToken(manualCloudInput);
    if (!token) {
      setManualCloudError("未识别到有效的共享链接或 Token。");
      return;
    }
    setManualCloudError(null);
    const label = manualCloudName.trim() || token;
    setSelectedCloud({ token, name: label, path: label });
    setTaskCloudToken(token);
  };

  const handleCreate = async () => {
    if (!taskLocalPath.trim() || !taskCloudToken.trim()) {
      setError("请完成本地路径与云端目录的选择。");
      return;
    }
    setError(null);
    setCreating(true);
    try {
      await apiFetch("/sync/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: taskName.trim() || null,
          local_path: taskLocalPath.trim(),
          cloud_folder_token: taskCloudToken.trim(),
          cloud_folder_name: selectedCloud?.path || null,
          base_path: taskBasePath.trim() || null,
          sync_mode: taskSyncMode,
          update_mode: taskUpdateMode,
          enabled: taskEnabled,
        }),
      });
      toast("任务创建成功", "success");
      resetAndClose();
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
    } finally {
      setCreating(false);
    }
  };

  const resetAndClose = () => {
    setStep(1);
    setTaskName("");
    setTaskLocalPath("");
    setTaskBasePath("");
    setTaskCloudToken("");
    setSelectedCloud(null);
    setManualCloudInput("");
    setManualCloudName("");
    setManualCloudError(null);
    setTaskSyncMode("bidirectional");
    setTaskUpdateMode("auto");
    setTaskEnabled(true);
    setError(null);
    onClose();
  };

  if (!open) return null;

  const inputCls = "w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-200 outline-none focus:border-[#3370FF] placeholder:text-zinc-600";

  const stepMeta = [
    { num: 1, label: "选择本地目录", icon: IconFolder, done: !!taskLocalPath.trim() },
    { num: 2, label: "选择云端目录", icon: IconCloud, done: !!taskCloudToken.trim() },
    { num: 3, label: "配置与确认", icon: IconArrowRightLeft, done: false },
  ];

  const modal = (
    <div className="fixed inset-0 z-50 bg-black/50">
        <div className="flex min-h-full items-center justify-center overflow-y-auto px-4 py-6">
        <div className="max-h-[90vh] w-full max-w-2xl overflow-auto rounded-2xl border border-zinc-800 bg-zinc-900 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-800 px-6 py-5">
          <div>
            <h2 className="text-lg font-semibold text-zinc-50">新建同步任务</h2>
            <p className="mt-0.5 text-xs text-zinc-500">按步骤配置本地目录、云端目录和同步策略</p>
          </div>
          <button className="rounded-lg p-2 text-zinc-500 transition hover:bg-zinc-800 hover:text-zinc-300" onClick={resetAndClose} type="button">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-4 w-4"><path d="M18 6L6 18M6 6l12 12" /></svg>
          </button>
        </div>

        {/* Step Indicator */}
        <div className="flex border-b border-zinc-800">
          {stepMeta.map((s) => {
            const Icon = s.icon;
            const isActive = step === s.num;
            const isPast = step > s.num;
            return (
              <button
                key={s.num}
                className={cn(
                  "flex flex-1 items-center justify-center gap-2.5 px-4 py-3.5 text-xs font-medium transition",
                  isActive
                    ? "border-b-2 border-[#3370FF] text-[#3370FF] bg-[#3370FF]/5"
                    : isPast
                      ? "text-emerald-400"
                      : "text-zinc-500"
                )}
                onClick={() => setStep(s.num)}
                type="button"
              >
                <span className={cn(
                  "flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-bold",
                  isActive ? "bg-[#3370FF] text-white" : isPast ? "bg-emerald-500/20 text-emerald-400" : "bg-zinc-800 text-zinc-500"
                )}>
                  {isPast ? "✓" : s.num}
                </span>
                {s.label}
              </button>
            );
          })}
        </div>

        {/* Content */}
        <div className="px-6 py-5">
          {/* Step 1: Local */}
          {step === 1 ? (
            <div className="space-y-5">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-zinc-400">任务名称 <span className="text-zinc-600">（可选）</span></label>
                <input className={inputCls} placeholder="例如：笔记同步" value={taskName} onChange={(e) => setTaskName(e.target.value)} />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-zinc-400">本地同步目录</label>
                <div className="flex gap-2">
                  <input className={`flex-1 ${inputCls}`} placeholder="点击右侧按钮选择目录" value={taskLocalPath} onChange={(e) => setTaskLocalPath(e.target.value)} />
                  <button
                    className="inline-flex items-center gap-1.5 rounded-lg bg-zinc-800 px-4 py-2.5 text-xs font-medium text-zinc-200 transition hover:bg-zinc-700"
                    onClick={pickLocalFolder}
                    type="button"
                  >
                    <IconFolder className="h-3.5 w-3.5" />
                    {folderPickLoading ? "选择中..." : "浏览"}
                  </button>
                </div>
                {folderPickError ? <p className="mt-1.5 text-xs text-rose-400">{folderPickError}</p> : null}
                {taskLocalPath ? (
                  <div className="mt-2 flex items-center gap-2 rounded-lg bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300">
                    <IconFolder className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">{taskLocalPath}</span>
                  </div>
                ) : null}
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-zinc-400">Base Path <span className="text-zinc-600">（可选，默认同本地目录）</span></label>
                <input className={inputCls} placeholder="用于计算相对路径" value={taskBasePath} onChange={(e) => setTaskBasePath(e.target.value)} />
              </div>
            </div>
          ) : null}

          {/* Step 2: Cloud */}
          {step === 2 ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-zinc-400">选择飞书云端目录</label>
                <button className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200" onClick={refreshTree} type="button">
                  <IconRefresh className="h-3 w-3" /> 刷新
                </button>
              </div>
              <div className="max-h-[320px] overflow-auto rounded-xl border border-zinc-800 bg-zinc-950 p-4">
                {treeLoading ? (
                  <div className="space-y-2">{[1, 2, 3].map((i) => <div key={i} className="h-6 animate-pulse rounded bg-zinc-800/50" />)}</div>
                ) : treeError ? (
                  <p className="text-sm text-rose-400">{treeError}</p>
                ) : tree ? (
                  <ul className="space-y-3">
                    <TreeNode node={tree} selectable selectedToken={taskCloudToken} onSelect={selectCloudFolder} />
                  </ul>
                ) : (
                  <div className="py-6 text-center">
                    <IconCloud className="mx-auto h-8 w-8 text-zinc-700" />
                    <p className="mt-2 text-sm text-zinc-500">暂无目录数据，请先刷新。</p>
                  </div>
                )}
              </div>
              <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4 space-y-3">
                <div>
                  <p className="text-xs font-medium text-zinc-400">共享链接 / Token</p>
                  <p className="mt-1 text-[11px] text-zinc-600">非所有者的共享文件夹可能不会出现在目录树中，请使用分享链接或 Token 创建同步。</p>
                </div>
                <input
                  className={inputCls}
                  placeholder="例如：https://.../drive/folder/xxxxxxxx 或 Token"
                  value={manualCloudInput}
                  onChange={(e) => {
                    setManualCloudInput(e.target.value);
                    setManualCloudError(null);
                  }}
                />
                <input
                  className={inputCls}
                  placeholder="云端目录显示名称（可选）"
                  value={manualCloudName}
                  onChange={(e) => setManualCloudName(e.target.value)}
                />
                <div className="flex items-center gap-3">
                  <button
                    className="rounded-lg bg-zinc-800 px-4 py-2 text-xs font-medium text-zinc-200 hover:bg-zinc-700"
                    onClick={applyManualCloud}
                    type="button"
                  >
                    使用链接
                  </button>
                  {manualCloudError ? <span className="text-xs text-rose-400">{manualCloudError}</span> : null}
                </div>
              </div>
              {selectedCloud ? (
                <div className="flex items-center gap-2 rounded-lg bg-emerald-500/10 px-3 py-2.5 text-xs text-emerald-300">
                  <IconCloud className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{selectedCloud.path}</span>
                </div>
              ) : null}
            </div>
          ) : null}

          {/* Step 3: Strategy + Confirm */}
          {step === 3 ? (
            <div className="space-y-5">
              {/* Sync mode cards */}
              <div>
                <label className="mb-2 block text-xs font-medium text-zinc-400">同步模式</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { value: "bidirectional", label: "双向同步", Icon: IconArrowRightLeft },
                    { value: "download_only", label: "仅下载", Icon: IconArrowDown },
                    { value: "upload_only", label: "仅上传", Icon: IconArrowUp },
                  ].map(({ value, label, Icon }) => (
                    <button
                      key={value}
                      className={cn(
                        "flex flex-col items-center gap-1.5 rounded-xl border p-3.5 transition",
                        taskSyncMode === value
                          ? "border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]"
                          : "border-zinc-800 text-zinc-500 hover:border-zinc-700 hover:bg-zinc-800/30"
                      )}
                      onClick={() => setTaskSyncMode(value)}
                      type="button"
                    >
                      <Icon className="h-5 w-5" />
                      <span className="text-xs font-medium">{label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Update mode */}
              <div>
                <label className="mb-1.5 block text-xs font-medium text-zinc-400">更新模式</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { value: "auto", label: "自动", desc: "智能选择" },
                    { value: "partial", label: "局部更新", desc: "仅更新变更块" },
                    { value: "full", label: "全量覆盖", desc: "完整替换" },
                  ].map(({ value, label, desc }) => (
                    <button
                      key={value}
                      className={cn(
                        "rounded-xl border p-3 text-center transition",
                        taskUpdateMode === value
                          ? "border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]"
                          : "border-zinc-800 text-zinc-500 hover:border-zinc-700 hover:bg-zinc-800/30"
                      )}
                      onClick={() => setTaskUpdateMode(value)}
                      type="button"
                    >
                      <p className="text-xs font-medium">{label}</p>
                      <p className="mt-0.5 text-[10px] text-zinc-600">{desc}</p>
                    </button>
                  ))}
                </div>
              </div>

              <label className="flex items-center gap-2.5 text-sm text-zinc-200">
                <input type="checkbox" checked={taskEnabled} onChange={(e) => setTaskEnabled(e.target.checked)} className="accent-[#3370FF] h-4 w-4" />
                创建后立即启用
              </label>

              {/* Summary */}
              <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
                <p className="text-xs font-semibold text-zinc-300">任务摘要</p>
                <div className="mt-3 grid grid-cols-2 gap-y-2 text-xs">
                  <span className="text-zinc-500">任务名称</span>
                  <span className="text-zinc-200 truncate">{taskName || "未命名"}</span>
                  <span className="text-zinc-500">本地目录</span>
                  <span className="text-zinc-200 truncate">{taskLocalPath || "—"}</span>
                  <span className="text-zinc-500">云端目录</span>
                  <span className="text-zinc-200 truncate">{selectedCloud?.path || "—"}</span>
                  <span className="text-zinc-500">同步模式</span>
                  <span className="text-zinc-200">{modeLabels[taskSyncMode]}</span>
                  <span className="text-zinc-500">更新模式</span>
                  <span className="text-zinc-200">{updateModeLabels[taskUpdateMode]}</span>
                </div>
              </div>

              {error ? <p className="text-sm text-rose-400">错误：{error}</p> : null}
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-zinc-800 px-6 py-4">
          <button
            className={cn("rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-200", step === 1 && "invisible")}
            onClick={() => setStep((s) => Math.max(1, s - 1))}
            type="button"
          >
            上一步
          </button>
          {step < 3 ? (
            <button
              className="rounded-lg bg-[#3370FF] px-5 py-2 text-sm font-semibold text-white transition hover:bg-[#3370FF]/80 disabled:opacity-50"
              onClick={() => setStep((s) => s + 1)}
              disabled={step === 1 ? !taskLocalPath.trim() : !taskCloudToken.trim()}
              type="button"
            >
              下一步
            </button>
          ) : (
            <button
              className="rounded-lg bg-[#3370FF] px-6 py-2 text-sm font-semibold text-white transition hover:bg-[#3370FF]/80 disabled:opacity-50"
              onClick={handleCreate}
              disabled={creating}
              type="button"
            >
              {creating ? "创建中..." : "创建任务"}
            </button>
          )}
        </div>
        </div>
      </div>
    </div>
  );

  return createPortal(modal, document.body);
}
