import { StatusPill } from "../StatusPill";
import { IconConflicts, IconRefresh } from "../Icons";
import { cn } from "../../lib/utils";
import {
  getConflictStatusMeta,
  type ConflictResolutionStatus,
  type ConflictResolutionSummary,
} from "../../lib/conflictResolution";
import type { ConflictItem, ConflictResolutionAction } from "../../types";

type ConflictManagementPanelProps = {
  conflicts: ConflictItem[];
  conflictLoading: boolean;
  conflictError: string | null;
  refreshConflicts: () => void;
  queueSummary: ConflictResolutionSummary;
  conflictResolutionStates: Record<string, ConflictResolutionStatus>;
  onResolveConflict: (id: string, action: ConflictResolutionAction, successMessage: string) => void;
  conflictActionLabels: Record<ConflictResolutionAction, string>;
};

export function ConflictManagementPanel({
  conflicts,
  conflictLoading,
  conflictError,
  refreshConflicts,
  queueSummary,
  conflictResolutionStates,
  onResolveConflict,
  conflictActionLabels,
}: ConflictManagementPanelProps) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
        <div>
          <h3 className="text-lg font-semibold text-zinc-50">冲突管理</h3>
          <p className="mt-1 text-xs text-zinc-400">处理云端与本地同时修改产生的冲突。支持连续为多条冲突选择方案，系统会按顺序提交。</p>
        </div>
        <button className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800" onClick={refreshConflicts} disabled={conflictLoading} type="button">
          <IconRefresh className="h-3.5 w-3.5" /> {conflictLoading ? "加载中..." : "刷新"}
        </button>
      </div>
      {(queueSummary.queued > 0 || queueSummary.running > 0 || queueSummary.waiting > 0 || queueSummary.success > 0 || queueSummary.failed > 0) ? (
        <div className="rounded-2xl border border-[#3370FF]/30 bg-[#3370FF]/10 px-4 py-3 text-sm text-zinc-200">
          当前冲突处理队列：处理中 {queueSummary.running} 条，等待任务空闲 {queueSummary.waiting} 条，排队中 {queueSummary.queued} 条，最近成功 {queueSummary.success} 条，失败 {queueSummary.failed} 条。
        </div>
      ) : null}
      {conflictError ? <p className="text-sm text-rose-400">加载失败：{conflictError}</p> : null}
      {conflicts.length === 0 ? (
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 py-16 text-center">
          <IconConflicts className="mx-auto h-12 w-12 text-zinc-700" />
          <p className="mt-4 text-sm text-zinc-500">暂无冲突记录。</p>
        </div>
      ) : (
        conflicts.map((conflict) => {
          const resolutionState = conflictResolutionStates[conflict.id];
          const meta = getConflictStatusMeta(conflict.resolved, conflict.resolved_action, resolutionState);
          const disabled = conflict.resolved || (resolutionState ? resolutionState.state !== "error" : false);
          const primaryLabel = resolutionState?.state === "running"
            ? "处理中..."
            : resolutionState?.state === "waiting"
              ? "等待重试..."
              : resolutionState?.state === "queued"
                ? "已排队"
                : "使用本地";
          const secondaryLabel = resolutionState?.state === "running"
            ? "处理中..."
            : resolutionState?.state === "waiting"
              ? "等待重试..."
              : resolutionState?.state === "queued"
                ? "已排队"
                : "使用云端";
          return (
            <div key={conflict.id} className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-1">
                  <p className="text-xs uppercase tracking-widest text-zinc-500">本地路径</p>
                  <p className="text-sm text-zinc-200">{conflict.local_path}</p>
                  <p className="text-xs text-zinc-500">云端 token：{conflict.cloud_token}</p>
                  <p className="text-xs text-zinc-600">哈希：{conflict.local_hash.slice(0, 8)} / {conflict.db_hash.slice(0, 8)}</p>
                </div>
                <StatusPill label={meta.label} tone={meta.tone} />
              </div>
              <div className="mt-4 grid gap-4 lg:grid-cols-2">
                <div>
                  <p className="text-xs uppercase tracking-widest text-zinc-500">本地版本</p>
                  <pre className="mt-2 max-h-56 overflow-auto rounded-lg border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs text-zinc-300">
                    {conflict.local_preview || "暂无本地预览。"}
                  </pre>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-widest text-zinc-500">云端版本</p>
                  <pre className="mt-2 max-h-56 overflow-auto rounded-lg border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs text-zinc-300">
                    {conflict.cloud_preview || "暂无云端预览。"}
                  </pre>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  className="rounded-lg bg-emerald-500/20 px-4 py-2 text-xs font-semibold text-emerald-300 transition hover:bg-emerald-500/30 disabled:opacity-50"
                  disabled={disabled}
                  onClick={() => onResolveConflict(conflict.id, "use_local", "已采用本地版本")}
                  type="button"
                >
                  {primaryLabel}
                </button>
                <button
                  className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 transition hover:bg-zinc-800 disabled:opacity-50"
                  disabled={disabled}
                  onClick={() => onResolveConflict(conflict.id, "use_cloud", "已采用云端版本")}
                  type="button"
                >
                  {secondaryLabel}
                </button>
                {conflict.resolved ? (
                  <span className="self-center text-xs text-zinc-500">已处理：{conflict.resolved_action}</span>
                ) : resolutionState ? (
                  <span className={cn(
                    "self-center text-xs",
                    resolutionState.state === "error"
                      ? "text-rose-400"
                      : resolutionState.state === "success"
                        ? "text-emerald-300"
                        : resolutionState.state === "waiting"
                          ? "text-amber-300"
                          : "text-zinc-500",
                  )}>
                    {meta.label}：
                    {conflictActionLabels[resolutionState.action]}
                    {resolutionState.message ? `，${resolutionState.message}` : ""}
                  </span>
                ) : null}
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
