import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useConflicts } from "../hooks/useConflicts";
import { useConflictResolutionQueue } from "../hooks/useConflictResolutionQueue";
import {
  CONFLICT_ACTION_LABELS,
  getConflictStatusMeta,
  type ConflictResolutionStatus,
} from "../lib/conflictResolution";
import { formatTimestamp } from "../lib/formatters";
import { shortPath } from "../lib/logCenter";
import { StatusPill } from "../components/StatusPill";
import { useToast } from "../components/ui/toast";
import {
  IconActivity,
  IconConflicts,
  IconCopy,
  IconRefresh,
} from "../components/Icons";
import { cn } from "../lib/utils";
import type { ConflictItem, ConflictResolutionAction } from "../types";

function Panel({
  title,
  hint,
  children,
  action,
  className,
}: {
  title: string;
  hint?: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("min-w-0 rounded-lg border border-[#d7e4f5] bg-white p-4 shadow-[0_10px_28px_rgba(51,112,255,0.05)]", className)}>
      <div className="mb-4 flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-[#102033]">{title}</h2>
          {hint ? <p className="mt-1 text-xs leading-5 text-[#6b7f96]">{hint}</p> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
      {children}
    </section>
  );
}

function previewText(value?: string | null): string {
  const text = value?.trim();
  return text || "暂无预览。";
}

function resolutionIsBusy(status?: ConflictResolutionStatus): boolean {
  return Boolean(status && status.state !== "error" && status.state !== "success");
}

function ConflictQueueItem({
  conflict,
  selected,
  status,
  onSelect,
}: {
  conflict: ConflictItem;
  selected: boolean;
  status?: ConflictResolutionStatus;
  onSelect: () => void;
}) {
  const meta = getConflictStatusMeta(conflict.resolved, conflict.resolved_action, status);
  return (
    <button
      className={cn(
        "w-full rounded-xl border px-3 py-3 text-left transition",
        selected
          ? "border-[#3370ff]/45 bg-[#eef5ff]"
          : "border-[#d7e4f5] bg-white hover:border-[#b8c9df] hover:bg-[#f6faff]"
      )}
      onClick={onSelect}
      type="button"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-[#102033]">{shortPath(conflict.local_path, 42)}</p>
          <p className="mt-1 text-xs text-[#6b7f96]">{formatTimestamp(conflict.created_at)}</p>
        </div>
        <StatusPill label={meta.label} tone={meta.tone} />
      </div>
      <p className="mt-2 truncate font-mono text-xs text-[#6b7f96]">cloud: {shortPath(conflict.cloud_token, 28)}</p>
      {meta.detail ? <p className="mt-2 text-xs text-[#52657a]">{meta.detail}</p> : null}
    </button>
  );
}

function VersionPreview({
  title,
  subtitle,
  hash,
  preview,
}: {
  title: string;
  subtitle: string;
  hash: string;
  preview?: string | null;
}) {
  return (
    <article className="min-w-0 rounded-xl border border-[#d7e4f5] bg-white">
      <div className="border-b border-[#edf3fb] px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-[#102033]">{title}</h3>
            <p className="mt-1 truncate text-xs text-[#6b7f96]" title={subtitle}>{subtitle}</p>
          </div>
          <span className="rounded-md bg-[#eef5ff] px-2 py-1 font-mono text-xs text-[#52657a]">{hash.slice(0, 8)}</span>
        </div>
      </div>
      <pre className="max-h-[420px] min-h-[260px] overflow-auto whitespace-pre-wrap break-words p-4 font-mono text-xs leading-5 text-[#334762]">
        {previewText(preview)}
      </pre>
    </article>
  );
}

export function ConflictResolutionPage() {
  const { conflicts, conflictLoading, conflictError, refreshConflicts, resolveConflictAsync } = useConflicts(true);
  const { toast } = useToast();
  const {
    conflictResolutionStates,
    queueSummary,
    handleResolveConflict,
  } = useConflictResolutionQueue({
    resolveConflictAsync,
    toast,
  });
  const [selectedConflictId, setSelectedConflictId] = useState<string | null>(null);

  const unresolved = conflicts.filter((conflict) => !conflict.resolved);
  const selectedConflict = useMemo(() => {
    if (selectedConflictId) {
      const found = conflicts.find((conflict) => conflict.id === selectedConflictId);
      if (found) return found;
    }
    return unresolved[0] ?? conflicts[0] ?? null;
  }, [conflicts, selectedConflictId, unresolved]);
  const selectedState = selectedConflict ? conflictResolutionStates[selectedConflict.id] : undefined;
  const selectedMeta = selectedConflict
    ? getConflictStatusMeta(selectedConflict.resolved, selectedConflict.resolved_action, selectedState)
    : null;
  const resolveSelected = (action: ConflictResolutionAction) => {
    if (!selectedConflict) return;
    const successMessage = action === "use_local" ? "已采用本地版本" : "已采用云端版本";
    handleResolveConflict(selectedConflict.id, action, successMessage);
  };

  const copyConflict = async () => {
    if (!selectedConflict) return;
    const text = [
      selectedConflict.local_path,
      selectedConflict.cloud_token,
      `local_hash=${selectedConflict.local_hash}`,
      `db_hash=${selectedConflict.db_hash}`,
      selectedConflict.local_preview,
      selectedConflict.cloud_preview,
    ].filter(Boolean).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      toast("冲突信息已复制", "success");
    } catch {
      toast("复制冲突信息失败", "danger");
    }
  };

  const disableResolution = !selectedConflict || selectedConflict.resolved || resolutionIsBusy(selectedState);

  return (
    <section className="animate-fade-up min-w-0 space-y-4">
      <div className="flex min-w-0 flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-[#102033]">冲突处理</h1>
          <p className="mt-1 text-sm text-[#52657A]">检测到 {unresolved.length} 个未解决冲突，按需选择版本后继续同步。</p>
        </div>
        <button
          className="inline-flex h-9 items-center gap-2 rounded-lg border border-[#c9d8ec] bg-white px-4 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff] disabled:opacity-50"
          disabled={conflictLoading}
          onClick={refreshConflicts}
          type="button"
        >
          <IconRefresh className="h-3.5 w-3.5" />
          刷新
        </button>
      </div>

      <div className="grid grid-cols-[280px_minmax(0,1fr)_320px] gap-4">
        <Panel
          title="冲突队列"
          hint="选择一条冲突查看本地和云端版本。"
          action={
            <button
              className="inline-flex items-center gap-2 rounded-lg border border-[#c9d8ec] px-3 py-1.5 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff] disabled:opacity-50"
              disabled={conflictLoading}
              onClick={refreshConflicts}
              type="button"
            >
              <IconRefresh className="h-3.5 w-3.5" />
              刷新
            </button>
          }
        >
          {conflictError ? <p className="mb-3 rounded-lg border border-[#f43f5e]/30 bg-[#fff1f2] px-3 py-2 text-xs text-[#be123c]">{conflictError}</p> : null}
          <div className="max-h-[680px] space-y-2 overflow-y-auto pr-1 log-scroll-area">
            {conflictLoading && conflicts.length === 0 ? (
              [1, 2, 3].map((item) => <div key={item} className="h-20 animate-pulse rounded-xl bg-[#eef5ff]" />)
            ) : conflicts.length === 0 ? (
              <div className="rounded-xl border border-dashed border-[#c9d8ec] px-5 py-10 text-center">
                <IconConflicts className="mx-auto h-10 w-10 text-[#9fb2c8]" />
                <p className="mt-3 text-sm text-[#6b7f96]">暂无冲突。</p>
              </div>
            ) : (
              conflicts.map((conflict) => (
                <ConflictQueueItem
                  key={conflict.id}
                  conflict={conflict}
                  selected={selectedConflict?.id === conflict.id}
                  status={conflictResolutionStates[conflict.id]}
                  onSelect={() => setSelectedConflictId(conflict.id)}
                />
              ))
            )}
          </div>
        </Panel>

        <main className="min-w-0 space-y-4">
          <Panel
            title="版本对比"
            hint={selectedConflict ? "数据方向明确后再提交处理，避免覆盖错误版本。" : "请选择一条冲突。"}
          >
            {!selectedConflict ? (
              <div className="rounded-xl border border-dashed border-[#c9d8ec] px-5 py-16 text-center">
                <IconConflicts className="mx-auto h-12 w-12 text-[#9fb2c8]" />
                <p className="mt-3 text-sm text-[#6b7f96]">请选择一条冲突查看预览。</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                <VersionPreview
                  title="本地版本"
                  subtitle={selectedConflict.local_path}
                  hash={selectedConflict.local_hash}
                  preview={selectedConflict.local_preview}
                />
                <VersionPreview
                  title="云端版本"
                  subtitle={`cloud token: ${selectedConflict.cloud_token}`}
                  hash={selectedConflict.db_hash || selectedConflict.cloud_token}
                  preview={selectedConflict.cloud_preview}
                />
              </div>
            )}
          </Panel>

          {selectedConflict ? (
            <Panel title="元数据" hint="用于判断版本来源和变更范围。">
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-xl border border-[#edf3fb] bg-[#f6faff] p-3">
                  <dt className="text-xs text-[#6b7f96]">本地路径</dt>
                  <dd className="mt-1 break-words font-mono text-xs text-[#102033]">{selectedConflict.local_path}</dd>
                </div>
                <div className="rounded-xl border border-[#edf3fb] bg-[#f6faff] p-3">
                  <dt className="text-xs text-[#6b7f96]">云端 token</dt>
                  <dd className="mt-1 break-words font-mono text-xs text-[#102033]">{selectedConflict.cloud_token}</dd>
                </div>
                <div className="rounded-xl border border-[#edf3fb] bg-[#f6faff] p-3">
                  <dt className="text-xs text-[#6b7f96]">版本号</dt>
                  <dd className="mt-1 text-xs text-[#102033]">云端 {selectedConflict.cloud_version} / 基线 {selectedConflict.db_version}</dd>
                </div>
                <div className="rounded-xl border border-[#edf3fb] bg-[#f6faff] p-3">
                  <dt className="text-xs text-[#6b7f96]">创建时间</dt>
                  <dd className="mt-1 text-xs text-[#102033]">{formatTimestamp(selectedConflict.created_at)}</dd>
                </div>
              </dl>
            </Panel>
          ) : null}
        </main>

        <aside className="min-w-0 space-y-4">
          <Panel title="处理状态" hint="冲突处理会串行提交，任务忙时自动等待重试。">
            {!selectedConflict || !selectedMeta ? (
              <div className="rounded-xl border border-dashed border-[#c9d8ec] px-4 py-10 text-center">
                <IconActivity className="mx-auto h-10 w-10 text-[#9fb2c8]" />
                <p className="mt-3 text-sm text-[#6b7f96]">请选择冲突。</p>
              </div>
            ) : (
              <div className="space-y-4">
                <StatusPill label={selectedMeta.label} tone={selectedMeta.tone} />
                <div className="rounded-xl border border-[#d7e4f5] bg-[#f6faff] p-3">
                  <p className="text-xs font-semibold text-[#52657a]">当前动作</p>
                  <p className="mt-2 text-sm text-[#102033]">
                    {selectedState ? CONFLICT_ACTION_LABELS[selectedState.action] : selectedConflict.resolved_action || "等待选择"}
                  </p>
                  {selectedMeta.detail ? <p className="mt-2 text-xs leading-5 text-[#52657a]">{selectedMeta.detail}</p> : null}
                </div>
                <dl className="space-y-2 text-xs">
                  <div className="flex justify-between gap-3"><dt className="text-[#6b7f96]">排队中</dt><dd className="font-semibold text-[#102033]">{queueSummary.queued}</dd></div>
                  <div className="flex justify-between gap-3"><dt className="text-[#6b7f96]">处理中</dt><dd className="font-semibold text-[#102033]">{queueSummary.running}</dd></div>
                  <div className="flex justify-between gap-3"><dt className="text-[#6b7f96]">等待重试</dt><dd className="font-semibold text-[#102033]">{queueSummary.waiting}</dd></div>
                  <div className="flex justify-between gap-3"><dt className="text-[#6b7f96]">成功</dt><dd className="font-semibold text-[#047857]">{queueSummary.success}</dd></div>
                  <div className="flex justify-between gap-3"><dt className="text-[#6b7f96]">失败</dt><dd className="font-semibold text-[#be123c]">{queueSummary.failed}</dd></div>
                </dl>
              </div>
            )}
          </Panel>

          <Panel title="版本选择">
            <div className="space-y-2">
              <button
                className="w-full rounded-lg bg-[#3370ff] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#1d4ed8] disabled:opacity-50"
                disabled={disableResolution}
                onClick={() => resolveSelected("use_cloud")}
                type="button"
              >
                使用云端
              </button>
              <button
                className="w-full rounded-lg border border-[#c9d8ec] px-4 py-2.5 text-sm font-semibold text-[#3370ff] hover:bg-[#eef5ff] disabled:opacity-50"
                disabled={disableResolution}
                onClick={() => resolveSelected("use_local")}
                type="button"
              >
                使用本地
              </button>
              <button
                className="w-full cursor-not-allowed rounded-lg border border-[#f59e0b]/35 bg-[#fffbeb] px-4 py-2.5 text-sm font-semibold text-[#b45309] opacity-70"
                disabled
                title="后端尚未提供 keep_both 冲突解决策略"
                type="button"
              >
                保留双方
              </button>
              <p className="text-xs leading-5 text-[#6b7f96]">“保留双方”需要后端新增副本命名、云端/本地映射和同步基线更新策略，当前不可提交。</p>
            </div>
          </Panel>

          <Panel title="辅助操作">
            <div className="grid gap-2">
              <button
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-[#c9d8ec] px-3 py-2 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff] disabled:opacity-50"
                disabled={!selectedConflict}
                onClick={copyConflict}
                type="button"
              >
                <IconCopy className="h-3.5 w-3.5" />
                复制冲突信息
              </button>
              <button
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-[#c9d8ec] px-3 py-2 text-xs font-semibold text-[#334762] hover:bg-[#f6faff] disabled:opacity-50"
                disabled={conflictLoading}
                onClick={refreshConflicts}
                type="button"
              >
                <IconRefresh className="h-3.5 w-3.5" />
                刷新队列
              </button>
            </div>
          </Panel>
        </aside>
      </div>
    </section>
  );
}
