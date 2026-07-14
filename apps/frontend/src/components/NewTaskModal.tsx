/* ------------------------------------------------------------------ */
/*  新建同步任务弹窗 — 五步桌面向导                                      */
/* ------------------------------------------------------------------ */

import { useState } from "react";
import { createPortal } from "react-dom";
import { apiFetch } from "../lib/api";
import {
  buildCreateTaskPayload,
  getWizardMaxAccessibleStep,
  resolveManualCloudSelection,
} from "../lib/newTaskWizard";
import { useDriveTree } from "../hooks/useDriveTree";
import { useAuth } from "../hooks/useAuth";
import { syncModeSupportsUpload } from "../lib/constants";
import { useToast } from "./ui/toast";
import type { CloudSelection } from "../types";
import { NewTaskCloudStep } from "./tasks/NewTaskCloudStep";
import { NewTaskLocalStep } from "./tasks/NewTaskLocalStep";
import { NewTaskStrategyStep } from "./tasks/NewTaskStrategyStep";
import { NewTaskWizardStepIndicator } from "./tasks/NewTaskWizardStepIndicator";
import { NewTaskWizardSummary } from "./tasks/NewTaskWizardSummary";

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
  const [taskSyncMode, setTaskSyncMode] = useState("download_only");
  const [taskUpdateMode, setTaskUpdateMode] = useState("auto");
  const [taskMdSyncMode, setTaskMdSyncMode] = useState<"enhanced" | "download_only" | "doc_only">("download_only");
  const [taskDeletePolicy, setTaskDeletePolicy] = useState<"off" | "safe" | "strict">("safe");
  const [taskDeleteGraceMinutes, setTaskDeleteGraceMinutes] = useState("30");
  const [taskEnabled, setTaskEnabled] = useState(true);
  const [folderPickLoading, setFolderPickLoading] = useState(false);
  const [folderPickError, setFolderPickError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const taskUploadEnabled = syncModeSupportsUpload(taskSyncMode);
  const maxAccessibleStep = getWizardMaxAccessibleStep(taskLocalPath, taskCloudToken);

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
    setTaskSyncMode("download_only");
    setTaskUpdateMode("auto");
    setTaskMdSyncMode("download_only");
    setTaskDeletePolicy("safe");
    setTaskDeleteGraceMinutes("30");
    setTaskEnabled(true);
    setError(null);
    onClose();
  };

  if (!open) return null;

  const inputCls = "h-9 w-full rounded-lg border border-[#c9d8ec] bg-white px-3 text-sm text-[#334762] outline-none placeholder:text-[#9fb2c8] focus:border-[#3370ff] focus:ring-2 focus:ring-[#3370ff]/10 disabled:bg-[#edf3fb] disabled:text-[#9fb2c8]";

  const strategyProps = {
    inputCls,
    taskName,
    taskLocalPath,
    selectedCloud,
    taskSyncMode,
    taskUpdateMode,
    taskMdSyncMode,
    taskDeletePolicy,
    taskDeleteGraceMinutes,
    taskEnabled,
    error,
    onTaskSyncModeChange: setTaskSyncMode,
    onTaskUpdateModeChange: setTaskUpdateMode,
    onTaskMdSyncModeChange: setTaskMdSyncMode,
    onTaskDeletePolicyChange: setTaskDeletePolicy,
    onTaskDeleteGraceMinutesChange: setTaskDeleteGraceMinutes,
    onTaskEnabledChange: setTaskEnabled,
  };
  const stepCopy = [
    ["选择本地目录", "确定本地内容保存的位置，并可为任务命名。"],
    ["选择云端目录", "选择需要同步的飞书目录，也可使用共享链接。"],
    ["同步模式", "决定内容流向；首次使用默认选择更安全的仅下载。"],
    ["删除与忽略", "明确删除是否联动，并确认任务创建后的状态。"],
    ["确认创建", "最后核对目录、策略和风险等级。"],
  ][step - 1];

  const modal = (
    <div className="fixed inset-0 z-50 bg-[#102033]/35 backdrop-blur-sm">
      <div className="flex min-h-full items-center justify-center overflow-y-auto px-4 py-6">
        <div className="flex max-h-[90vh] w-[1120px] max-w-[calc(100vw-32px)] flex-col overflow-hidden rounded-xl border border-[#d7e4f5] bg-white shadow-[0_24px_80px_rgba(16,32,51,0.18)]">
          <div className="flex items-center justify-between border-b border-[#edf3fb] px-6 py-4">
            <div>
              <h2 className="text-lg font-semibold text-[#102033]">新建同步任务</h2>
              <p className="mt-0.5 text-xs text-[#52657a]">分五步完成配置，每一步只处理一类决策。</p>
            </div>
            <button aria-label="关闭新建任务" className="rounded-lg border border-[#d7e4f5] p-2 text-[#52657a] transition hover:bg-[#eef5ff] hover:text-[#3370ff]" onClick={resetAndClose} type="button">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-4 w-4"><path d="M18 6L6 18M6 6l12 12" /></svg>
            </button>
          </div>

          <NewTaskWizardStepIndicator
            step={step}
            taskLocalPath={taskLocalPath}
            taskCloudToken={taskCloudToken}
            maxAccessibleStep={maxAccessibleStep}
            onSelectStep={(nextStep) => setStep(Math.min(nextStep, maxAccessibleStep))}
          />

          <div className="min-h-0 flex-1 overflow-y-auto bg-[linear-gradient(180deg,#ffffff_0%,#f8fbff_100%)] px-6 py-5">
            <div className="mb-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#3370ff]">第 {step} 步，共 5 步</p>
              <h3 className="mt-1 text-lg font-semibold text-[#102033]">{stepCopy[0]}</h3>
              <p className="mt-1 text-sm text-[#52657a]">{stepCopy[1]}</p>
            </div>
            <div className="grid grid-cols-[minmax(0,1fr)_280px] items-start gap-5">
              <section className="min-h-[360px] min-w-0 rounded-xl border border-[#d7e4f5] bg-white p-5 shadow-[0_10px_28px_rgba(51,112,255,0.06)]">
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
                    onManualCloudInputChange={(value) => { setManualCloudInput(value); setManualCloudError(null); }}
                    onManualCloudNameChange={setManualCloudName}
                    onApplyManualCloud={applyManualCloud}
                  />
                ) : null}
                {step === 3 ? <NewTaskStrategyStep view="mode" {...strategyProps} /> : null}
                {step === 4 ? <NewTaskStrategyStep view="rules" {...strategyProps} /> : null}
                {step === 5 ? <NewTaskStrategyStep view="confirm" {...strategyProps} /> : null}
              </section>
              <NewTaskWizardSummary
                taskName={taskName}
                taskLocalPath={taskLocalPath}
                cloudPath={selectedCloud?.path || ""}
                taskSyncMode={taskSyncMode}
                taskDeletePolicy={taskDeletePolicy}
                taskEnabled={taskEnabled}
              />
            </div>
          </div>

          <div className="flex items-center justify-between border-t border-[#edf3fb] bg-white px-6 py-4">
            <button className="rounded-lg px-3 py-2 text-sm font-medium text-[#52657a] transition hover:bg-[#f6faff]" onClick={resetAndClose} type="button">取消</button>
            <div className="flex items-center gap-3">
              {step > 1 ? (
                <button className="rounded-lg border border-[#c9d8ec] px-4 py-2 text-sm font-medium text-[#334762] transition hover:bg-[#f6faff]" onClick={() => setStep((current) => current - 1)} type="button">上一步</button>
              ) : null}
              {step < 5 ? (
                <button
                  className="rounded-lg bg-[#3370ff] px-5 py-2 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(51,112,255,0.2)] transition hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:opacity-40"
                  onClick={() => setStep((current) => Math.min(5, current + 1))}
                  disabled={step === 1 ? !taskLocalPath.trim() : step === 2 ? !taskCloudToken.trim() : false}
                  type="button"
                >
                  下一步
                </button>
              ) : (
                <button className="rounded-lg bg-[#3370ff] px-6 py-2 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(51,112,255,0.2)] transition hover:bg-[#1d4ed8] disabled:opacity-40" onClick={handleCreate} disabled={creating || !taskLocalPath.trim() || !taskCloudToken.trim()} type="button">
                  {creating ? "创建中..." : "创建任务"}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return createPortal(modal, document.body);
}
