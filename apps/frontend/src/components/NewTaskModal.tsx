/* ------------------------------------------------------------------ */
/*  新建同步任务弹窗 — 分步向导 (Step 1/2/3)                             */
/* ------------------------------------------------------------------ */

import { useState } from "react";
import { apiFetch } from "../lib/api";
import { useDriveTree } from "../hooks/useDriveTree";
import { useAuth } from "../hooks/useAuth";
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
    setTaskSyncMode("bidirectional");
    setTaskUpdateMode("auto");
    setTaskEnabled(true);
    setError(null);
    onClose();
  };

  if (!open) return null;

  const stepInfo = [
    { num: 1, label: "本地目录" },
    { num: 2, label: "云端目录" },
    { num: 3, label: "同步策略" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4 py-6">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-auto rounded-2xl border border-zinc-800 bg-zinc-900 p-6 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-zinc-50">新建同步任务</h2>
            <p className="mt-1 text-xs text-zinc-400">按步骤完成配置</p>
          </div>
          <button className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800" onClick={resetAndClose} type="button">
            关闭
          </button>
        </div>

        {/* Step Indicator */}
        <div className="mt-6 flex items-center gap-2">
          {stepInfo.map((s) => (
            <button
              key={s.num}
              className={cn(
                "flex-1 rounded-lg border p-3 text-center transition",
                step === s.num
                  ? "border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]"
                  : step > s.num
                    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                    : "border-zinc-800 bg-zinc-900/50 text-zinc-500"
              )}
              onClick={() => setStep(s.num)}
              type="button"
            >
              <p className="text-xs font-bold">步骤 {s.num}</p>
              <p className="mt-1 text-sm font-medium">{s.label}</p>
            </button>
          ))}
        </div>

        {/* Step 1: Local */}
        {step === 1 ? (
          <div className="mt-6 space-y-4">
            <input
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
              placeholder="任务名称（可选）"
              value={taskName}
              onChange={(e) => setTaskName(e.target.value)}
            />
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400">本地目录</label>
              <div className="flex gap-2">
                <input
                  className="flex-1 rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
                  placeholder="请选择本地目录"
                  value={taskLocalPath}
                  onChange={(e) => setTaskLocalPath(e.target.value)}
                />
                <button
                  className="rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-700"
                  onClick={pickLocalFolder}
                  type="button"
                >
                  {folderPickLoading ? "选择中..." : "浏览"}
                </button>
              </div>
              {folderPickError ? <p className="mt-1 text-xs text-rose-400">{folderPickError}</p> : null}
            </div>
            <input
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
              placeholder="base_path（可选，默认同本地目录）"
              value={taskBasePath}
              onChange={(e) => setTaskBasePath(e.target.value)}
            />
            <div className="flex justify-end">
              <button
                className="rounded-lg bg-[#3370FF] px-5 py-2 text-sm font-semibold text-white transition hover:bg-[#3370FF]/80 disabled:opacity-50"
                onClick={() => setStep(2)}
                disabled={!taskLocalPath.trim()}
                type="button"
              >
                下一步
              </button>
            </div>
          </div>
        ) : null}

        {/* Step 2: Cloud */}
        {step === 2 ? (
          <div className="mt-6 space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-zinc-400">选择飞书云端目录</label>
              <button
                className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
                onClick={refreshTree}
                type="button"
              >
                <IconRefresh className="h-3.5 w-3.5" />
                刷新
              </button>
            </div>
            <div className="max-h-[360px] overflow-auto rounded-lg border border-zinc-800 bg-zinc-950 p-4">
              {treeLoading ? (
                <p className="text-sm text-zinc-500">目录加载中...</p>
              ) : treeError ? (
                <p className="text-sm text-rose-400">{treeError}</p>
              ) : tree ? (
                <ul className="space-y-3">
                  <TreeNode node={tree} selectable selectedToken={taskCloudToken} onSelect={selectCloudFolder} />
                </ul>
              ) : (
                <p className="text-sm text-zinc-500">暂无目录数据，请先刷新。</p>
              )}
            </div>
            {selectedCloud ? (
              <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300">
                已选择：{selectedCloud.path} ({selectedCloud.token})
              </div>
            ) : null}
            <div className="flex justify-between">
              <button className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-800" onClick={() => setStep(1)} type="button">
                上一步
              </button>
              <button
                className="rounded-lg bg-[#3370FF] px-5 py-2 text-sm font-semibold text-white transition hover:bg-[#3370FF]/80 disabled:opacity-50"
                onClick={() => setStep(3)}
                disabled={!taskCloudToken.trim()}
                type="button"
              >
                下一步
              </button>
            </div>
          </div>
        ) : null}

        {/* Step 3: Strategy */}
        {step === 3 ? (
          <div className="mt-6 space-y-5">
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
                      "flex flex-col items-center gap-2 rounded-lg border p-4 transition",
                      taskSyncMode === value
                        ? "border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]"
                        : "border-zinc-800 text-zinc-400 hover:bg-zinc-800/50"
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
            <div>
              <label className="mb-2 block text-xs font-medium text-zinc-400">更新模式</label>
              <select
                className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
                value={taskUpdateMode}
                onChange={(e) => setTaskUpdateMode(e.target.value)}
              >
                <option value="auto">自动</option>
                <option value="partial">局部更新</option>
                <option value="full">全量覆盖</option>
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm text-zinc-200">
              <input type="checkbox" checked={taskEnabled} onChange={(e) => setTaskEnabled(e.target.checked)} className="accent-[#3370FF]" />
              创建后立即启用
            </label>

            {/* Summary */}
            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4 text-xs text-zinc-400">
              <p className="font-semibold text-zinc-200">任务摘要</p>
              <ul className="mt-2 space-y-1">
                <li>本地：{taskLocalPath || "—"}</li>
                <li>云端：{selectedCloud?.path || taskCloudToken || "—"}</li>
                <li>模式：{taskSyncMode} / {taskUpdateMode}</li>
              </ul>
            </div>

            {error ? <p className="text-sm text-rose-400">错误：{error}</p> : null}

            <div className="flex justify-between">
              <button className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-800" onClick={() => setStep(2)} type="button">
                上一步
              </button>
              <button
                className="rounded-lg bg-[#3370FF] px-5 py-2 text-sm font-semibold text-white transition hover:bg-[#3370FF]/80 disabled:opacity-50"
                onClick={handleCreate}
                disabled={creating}
                type="button"
              >
                {creating ? "创建中..." : "创建任务"}
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
