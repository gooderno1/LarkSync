/* ------------------------------------------------------------------ */
/*  新建同步任务弹窗 — 五步桌面向导                                      */
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

  const inputCls = "h-9 w-full rounded-lg border border-[#c9d8ec] bg-white px-3 text-sm text-[#334762] outline-none placeholder:text-[#9fb2c8] focus:border-[#3370ff] focus:ring-2 focus:ring-[#3370ff]/10 disabled:bg-[#edf3fb] disabled:text-[#9fb2c8]";

  const modal = (
    <div className="fixed inset-0 z-50 bg-[#102033]/35 backdrop-blur-sm">
        <div className="flex min-h-full items-center justify-center overflow-y-auto px-4 py-6">
        <div className="max-h-[94vh] w-[1460px] max-w-[calc(100vw-32px)] overflow-auto rounded-lg border border-[#d7e4f5] bg-white shadow-[0_24px_80px_rgba(16,32,51,0.18)]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#edf3fb] px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-[#102033]">新建同步任务</h2>
            <p className="mt-0.5 text-xs text-[#6b7f96]">按步骤配置本地目录、云端目录和同步策略。</p>
          </div>
          <button className="rounded-lg border border-[#d7e4f5] p-2 text-[#6b7f96] transition hover:bg-[#eef5ff] hover:text-[#3370ff]" onClick={resetAndClose} type="button">
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
        <div className="bg-[linear-gradient(180deg,#ffffff_0%,#f8fbff_100%)] px-5 py-4">
          <div className="grid min-w-[1240px] grid-cols-[1.05fr_1.05fr_1fr_1.05fr_.9fr] items-stretch gap-3">
            <section className={cn("min-w-0 rounded-lg border bg-white p-3", step === 1 ? "border-[#3370ff] shadow-[0_10px_28px_rgba(51,112,255,0.12)]" : "border-[#d7e4f5]")}>
              <h3 className="mb-3 text-sm font-semibold text-[#102033]">选择本地目录</h3>
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
            </section>

            <section className={cn("min-w-0 rounded-lg border bg-white p-3", step === 2 ? "border-[#3370ff] shadow-[0_10px_28px_rgba(51,112,255,0.12)]" : "border-[#d7e4f5]")}>
              <h3 className="mb-3 text-sm font-semibold text-[#102033]">选择云端目录</h3>
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
            </section>

            <section className={cn("min-w-0 rounded-lg border bg-white p-3", step === 3 ? "border-[#3370ff] shadow-[0_10px_28px_rgba(51,112,255,0.12)]" : "border-[#d7e4f5]")}>
              <h3 className="mb-3 text-sm font-semibold text-[#102033]">同步模式</h3>
              <NewTaskStrategyStep
              view="mode"
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
            </section>

            <section className={cn("min-w-0 rounded-lg border bg-white p-3", step === 4 ? "border-[#3370ff] shadow-[0_10px_28px_rgba(51,112,255,0.12)]" : "border-[#d7e4f5]")}>
              <h3 className="mb-3 text-sm font-semibold text-[#102033]">删除与忽略</h3>
              <NewTaskStrategyStep
              view="rules"
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
            </section>

            <section className={cn("min-w-0 rounded-lg border bg-white p-3", step === 5 ? "border-[#3370ff] shadow-[0_10px_28px_rgba(51,112,255,0.12)]" : "border-[#d7e4f5]")}>
              <h3 className="mb-3 text-sm font-semibold text-[#102033]">风险摘要</h3>
              <NewTaskStrategyStep
                view="confirm"
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
              <aside className="mt-3 rounded-lg border border-[#10b981]/25 bg-[#ecfdf5] p-3">
                <h4 className="text-sm font-semibold text-[#047857]">{taskDeletePolicy === "strict" ? "中风险" : "低风险"}</h4>
                <div className="mt-3 space-y-3 text-xs leading-5 text-[#786043]">
                  <p>安全删除不会直接删除云端文件。</p>
                  <p>隐藏目录和缓存路径默认不参与同步。</p>
                </div>
              </aside>
            </section>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-[#edf3fb] bg-white px-6 py-4">
          <button className="rounded-lg border border-[#c9d8ec] px-4 py-2 text-sm font-medium text-[#334762] transition hover:bg-[#f6faff]" onClick={resetAndClose} type="button">
            取消
          </button>
          <button
            className="rounded-lg border border-[#c9d8ec] px-4 py-2 text-sm font-medium text-[#334762] transition hover:bg-[#f6faff] disabled:opacity-40"
            onClick={() => setStep((s) => Math.max(1, s - 1))}
            disabled={step === 1}
            type="button"
          >
            上一步
          </button>
          <button
            className="rounded-lg bg-[#3370ff] px-5 py-2 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(51,112,255,0.2)] transition hover:bg-[#1d4ed8] disabled:opacity-40"
            onClick={() => setStep((s) => Math.min(5, s + 1))}
            disabled={step === 5 || (step === 1 ? !taskLocalPath.trim() : step === 2 ? !taskCloudToken.trim() : false)}
            type="button"
          >
            下一步
          </button>
          <button
            className="rounded-lg bg-[#3370ff] px-6 py-2 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(51,112,255,0.2)] transition hover:bg-[#1d4ed8] disabled:opacity-40"
            onClick={handleCreate}
            disabled={creating || step !== 5 || !taskLocalPath.trim() || !taskCloudToken.trim()}
            type="button"
          >
            {creating ? "创建中..." : "创建任务"}
          </button>
        </div>
        </div>
      </div>
    </div>
  );

  return createPortal(modal, document.body);
}
