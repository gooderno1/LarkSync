/* ------------------------------------------------------------------ */
/*  新建同步任务弹窗 — 分步向导 (Step 1/2/3) 优化版                      */
/* ------------------------------------------------------------------ */

import { useState } from "react";
import { createPortal } from "react-dom";
import { apiFetch } from "../lib/api";
import { buildCreateTaskPayload, resolveManualCloudSelection } from "../lib/newTaskWizard";
import { useDriveTree } from "../hooks/useDriveTree";
import { useAuth } from "../hooks/useAuth";
import { syncModeSupportsUpload } from "../lib/constants";
import { useToast } from "./ui/toast";
import { cn } from "../lib/utils";
import type { CloudSelection } from "../types";
import { NewTaskCloudStep } from "./tasks/NewTaskCloudStep";
import { NewTaskLocalStep } from "./tasks/NewTaskLocalStep";
import { NewTaskStrategyStep } from "./tasks/NewTaskStrategyStep";
import { NewTaskWizardStepIndicator } from "./tasks/NewTaskWizardStepIndicator";

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
  const [taskMdSyncMode, setTaskMdSyncMode] = useState<"enhanced" | "download_only" | "doc_only">("enhanced");
  const [taskDeletePolicy, setTaskDeletePolicy] = useState<"off" | "safe" | "strict">("safe");
  const [taskDeleteGraceMinutes, setTaskDeleteGraceMinutes] = useState("30");
  const [taskEnabled, setTaskEnabled] = useState(true);
  const [folderPickLoading, setFolderPickLoading] = useState(false);
  const [folderPickError, setFolderPickError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const taskUploadEnabled = syncModeSupportsUpload(taskSyncMode);

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

  const applyManualCloud = () => {
    const { selection, error: nextError } = resolveManualCloudSelection(
      manualCloudInput,
      manualCloudName
    );
    if (!selection) {
      setManualCloudError(nextError);
      return;
    }
    setManualCloudError(null);
    setSelectedCloud(selection);
    setTaskCloudToken(selection.token);
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
        body: JSON.stringify(
          buildCreateTaskPayload({
            taskName,
            taskLocalPath,
            taskCloudToken,
            selectedCloud,
            taskBasePath,
            taskSyncMode,
            taskUpdateMode,
            taskMdSyncMode,
            taskUploadEnabled,
            taskDeletePolicy,
            taskDeleteGraceMinutes,
            taskEnabled,
          })
        ),
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
    setTaskMdSyncMode("enhanced");
    setTaskDeletePolicy("safe");
    setTaskDeleteGraceMinutes("30");
    setTaskEnabled(true);
    setError(null);
    onClose();
  };

  if (!open) return null;

  const inputCls = "w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-200 outline-none focus:border-[#3370FF] placeholder:text-zinc-600";

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

        <NewTaskWizardStepIndicator
          step={step}
          taskLocalPath={taskLocalPath}
          taskCloudToken={taskCloudToken}
          onSelectStep={setStep}
        />

        {/* Content */}
        <div className="px-6 py-5">
          {/* Step 1: Local */}
          {step === 1 ? (
            <NewTaskLocalStep
              inputCls={inputCls}
              taskName={taskName}
              taskLocalPath={taskLocalPath}
              taskBasePath={taskBasePath}
              folderPickLoading={folderPickLoading}
              folderPickError={folderPickError}
              onTaskNameChange={setTaskName}
              onTaskLocalPathChange={setTaskLocalPath}
              onTaskBasePathChange={setTaskBasePath}
              onPickLocalFolder={pickLocalFolder}
            />
          ) : null}

          {/* Step 2: Cloud */}
          {step === 2 ? (
            <NewTaskCloudStep
              inputCls={inputCls}
              tree={tree}
              treeLoading={treeLoading}
              treeError={treeError}
              taskCloudToken={taskCloudToken}
              selectedCloud={selectedCloud}
              manualCloudInput={manualCloudInput}
              manualCloudName={manualCloudName}
              manualCloudError={manualCloudError}
              onRefreshTree={refreshTree}
              onSelectCloudFolder={selectCloudFolder}
              onManualCloudInputChange={(value) => {
                setManualCloudInput(value);
                setManualCloudError(null);
              }}
              onManualCloudNameChange={setManualCloudName}
              onApplyManualCloud={applyManualCloud}
            />
          ) : null}

          {/* Step 3: Strategy + Confirm */}
          {step === 3 ? (
            <NewTaskStrategyStep
              inputCls={inputCls}
              taskName={taskName}
              taskLocalPath={taskLocalPath}
              selectedCloud={selectedCloud}
              taskSyncMode={taskSyncMode}
              taskUpdateMode={taskUpdateMode}
              taskMdSyncMode={taskMdSyncMode}
              taskDeletePolicy={taskDeletePolicy}
              taskDeleteGraceMinutes={taskDeleteGraceMinutes}
              taskEnabled={taskEnabled}
              error={error}
              onTaskSyncModeChange={setTaskSyncMode}
              onTaskUpdateModeChange={setTaskUpdateMode}
              onTaskMdSyncModeChange={setTaskMdSyncMode}
              onTaskDeletePolicyChange={setTaskDeletePolicy}
              onTaskDeleteGraceMinutesChange={setTaskDeleteGraceMinutes}
              onTaskEnabledChange={setTaskEnabled}
            />
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
