import type { SyncRuntimeSnapshot, SyncTaskStatus } from "../types";

export const RUNTIME_STALE_MS = 15_000;

const phaseLabels: Record<SyncRuntimeSnapshot["phase"], string> = {
  preparing: "准备同步", scanning_cloud: "扫描云端", scanning_local: "扫描本地",
  checking: "检查变更", downloading: "下行处理", uploading: "上行处理",
  deleting: "处理删除", processing: "处理文件", finalizing: "保存同步状态", finished: "处理结束",
};
const operationLabels: Record<string, string> = {
  reading_document: "读取文档", converting_document: "转换文档", updating_document: "更新文档",
  transferring_file: "传输文件", writing_file: "写入文件",
};
const waitLabels: Record<NonNullable<SyncRuntimeSnapshot["wait"]>["reason"], string> = {
  local_rate_limit: "等待请求额度", rate_limit: "请求受限", retry: "自动重试",
  remote_export: "等待飞书完成导出", remote_import: "等待飞书完成导入",
};

export function isTaskExecuting(status?: SyncTaskStatus | null): boolean {
  return status?.runtime?.active ?? status?.state === "running";
}

export function isRecordedRunExecuting(status: SyncTaskStatus | null | undefined, runId: string): boolean {
  // Preflight retains the previous run ID until actual work creates a new run.
  return isTaskExecuting(status) && status?.current_run_id === runId
    && (status.state === "running" || status.runtime?.phase === "finalizing");
}

export function formatElapsed(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds)) return "—";
  const whole = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor(whole / 60) % 60;
  const rest = whole % 60;
  return hours > 0 ? `${hours} 小时 ${minutes} 分` : minutes > 0 ? `${minutes} 分 ${rest} 秒` : `${rest} 秒`;
}

export type RuntimeView = {
  running: boolean;
  stale: boolean;
  phaseLabel: string;
  countLabel: string;
  elapsedLabel: string;
  waitLabel: string | null;
  currentItem: string | null;
  operationLabel: string | null;
  progress: number | null;
};

export function describeSyncRuntime(
  status?: SyncTaskStatus | null,
  nowMs = Date.now(),
  receivedAtMs?: number,
): RuntimeView {
  const runtime = status?.runtime?.schema_version === 1 ? status.runtime : null;
  const running = isTaskExecuting(status);
  // Receipt time avoids depending on the server and browser clocks being aligned.
  const received = receivedAtMs || (runtime ? runtime.sampled_at * 1000 : nowMs);
  const ageMs = Math.max(0, nowMs - received);
  const stale = running && ageMs >= RUNTIME_STALE_MS;
  const delta = running && !stale ? ageMs / 1000 : 0;
  const elapsed = runtime ? runtime.elapsed_seconds + delta : status?.started_at != null
    ? Math.max(0, (status.finished_at ?? ((stale ? received : nowMs) / 1000)) - status.started_at) : null;
  let countLabel = "阶段数量未提供";
  let progress: number | null = null;
  if (runtime) {
    if (!runtime.active || runtime.phase === "finalizing") {
      countLabel = `本次已处理 ${runtime.processed_total} 项`;
    } else if (runtime.phase === "scanning_cloud" || runtime.phase === "scanning_local") {
      countLabel = `已发现 ${runtime.discovered} 项`;
    } else if (runtime.total !== null) {
      countLabel = runtime.total === 0 ? "本阶段无待处理项" : `本阶段已处理 ${runtime.processed}/${runtime.total} 项`;
      if (runtime.total > 0 && runtime.processed <= runtime.total) {
        progress = Math.round((runtime.processed / runtime.total) * 100);
      }
    } else {
      countLabel = `本阶段已处理 ${runtime.processed} 项 · 总数待确定`;
    }
  }
  let waitLabel: string | null = null;
  if (running && runtime?.wait) {
    const wait = runtime.wait;
    waitLabel = waitLabels[wait.reason] || "等待处理";
    if (wait.resume_at !== null && (wait.reason === "rate_limit" || wait.reason === "retry")) {
      const seconds = Math.max(0, Math.ceil(wait.resume_at - runtime.sampled_at - delta));
      waitLabel += seconds > 0 ? ` · ${seconds} 秒后重试` : " · 准备重试";
    }
  }
  const label = runtime ? phaseLabels[runtime.phase] || "处理中" : running ? "同步中" : "暂无阶段信息";
  return {
    running, stale,
    phaseLabel: runtime?.active && runtime.pass_kind === "reconcile" ? `补齐 · ${label}` : label,
    countLabel, elapsedLabel: formatElapsed(elapsed),
    waitLabel: stale ? "状态暂未更新" : waitLabel,
    currentItem: runtime?.active ? runtime.current_item : null,
    operationLabel: runtime?.operation ? operationLabels[runtime.operation] || null : null,
    progress,
  };
}
