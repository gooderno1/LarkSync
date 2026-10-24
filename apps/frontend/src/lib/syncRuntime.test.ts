import { describe, expect, it } from "vitest";
import type { SyncTaskStatus, SyncRuntimeSnapshot } from "../types";
import { describeSyncRuntime } from "./syncRuntime";

const runtime: SyncRuntimeSnapshot = {
  schema_version: 1, execution_id: "execution-a", active: true,
  phase: "scanning_cloud", direction: "download", pass_kind: "regular", segment_id: 1,
  processed: 0, total: null, discovered: 372, processed_total: 0,
  current_item: null, operation: null, started_at: 100, sampled_at: 165,
  elapsed_seconds: 65, activity_at: 164, progress_at: 164, wait: null,
};
const status = { state: "running", runtime } as SyncTaskStatus;

describe("shared runtime presentation", () => {
  it("shows discovered count rather than a false zero percent", () => {
    const view = describeSyncRuntime(status, 165000, 165000);
    expect(view.phaseLabel).toBe("扫描云端");
    expect(view.countLabel).toBe("已发现 372 项");
    expect(view.progress).toBeNull();
    expect(view.elapsedLabel).toBe("1 分 5 秒");
  });

  it("labels counts as stage work, including handled failures, not success", () => {
    const view = describeSyncRuntime({ ...status, runtime: { ...runtime, phase: "uploading", processed: 2, total: 3 } }, 165000);
    expect(view.countLabel).toBe("本阶段已处理 2/3 项");
    expect(view.progress).toBe(67);
  });

  it("keeps elapsed frozen and stops retry countdown when snapshot is stale", () => {
    const waiting = { ...status, runtime: { ...runtime, wait: { reason: "rate_limit" as const, since: 165, resume_at: 173, attempt: 2 } } };
    const fresh = describeSyncRuntime(waiting, 168000, 165000);
    expect(fresh.waitLabel).toBe("请求受限 · 5 秒后重试");
    const stale = describeSyncRuntime(waiting, 200000, 165000);
    expect(stale.stale).toBe(true);
    expect(stale.waitLabel).toBe("状态暂未更新");
    expect(stale.elapsedLabel).toBe("1 分 5 秒");
  });

  it("does not fabricate stage progress for old backends and freezes terminal elapsed", () => {
    const legacy = describeSyncRuntime({ state: "running", total_files: 10, completed_files: 10, started_at: 100 } as SyncTaskStatus, 165000);
    expect(legacy.progress).toBeNull();
    expect(legacy.countLabel).toBe("阶段数量未提供");
    const done = describeSyncRuntime({ ...status, state: "success", runtime: { ...runtime, active: false, phase: "finished", processed_total: 4 } }, 999000);
    expect(done.elapsedLabel).toBe("1 分 5 秒");
    expect(done.countLabel).toBe("本次已处理 4 项");
    expect(done.stale).toBe(false);
  });
});
