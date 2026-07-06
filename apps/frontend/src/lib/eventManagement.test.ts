import { describe, expect, it } from "vitest";

import {
  buildEventIssueGroups,
  buildEventRunGroups,
  buildTaskEventGroups,
  classifyEventProblem,
} from "./eventManagement";
import type { SyncLogEntry } from "../types";

function event(overrides: Partial<SyncLogEntry>): SyncLogEntry {
  return {
    taskId: "task-1",
    taskName: "王远雄 - 工作记录",
    timestamp: 100,
    status: "failed",
    path: "D:/Docs/demo.md",
    message: null,
    runId: "run-1",
    ...overrides,
  };
}

describe("event management helpers", () => {
  it("explains enhanced markdown mirror folder permission failures", () => {
    const problem = classifyEventProblem(event({
      message: "创建云端文件夹失败: forbidden. (name=_LarkSync_MD_Mirror)",
    }));

    expect(problem.key).toBe("mirror_folder_forbidden");
    expect(problem.title).toBe("权限禁止：云端镜像目录创建失败");
    expect(problem.recommendedAction).toContain("doc_only");
    expect(problem.needsAction).toBe(true);
  });

  it("explains docx block write forbidden failures", () => {
    const problem = classifyEventProblem(event({
      message: "创建块失败，已中止替换。飞书返回 code=1770032 msg=forBidden",
    }));

    expect(problem.key).toBe("docx_block_write_forbidden");
    expect(problem.title).toBe("权限禁止：云文档内容写入失败");
    expect(problem.cause).toContain("块级写入权限");
  });

  it("treats delete not found as stale delete state instead of a user file task", () => {
    const problem = classifyEventProblem(event({
      status: "delete_failed",
      message: "删除文件失败: not found. token=LwzVfMbZXlVeHHdk8W7ccFPdnEd type=folder",
    }));

    expect(problem.key).toBe("delete_target_missing");
    expect(problem.title).toBe("删除状态已失效：云端目标不存在");
    expect(problem.recommendedAction).toContain("状态库");
  });

  it("groups issue queues by concrete problem and sorts action items first", () => {
    const groups = buildEventIssueGroups([
      event({
        timestamp: 100,
        message: "创建云端文件夹失败: forbidden. (name=_LarkSync_MD_Mirror)",
      }),
      event({
        timestamp: 120,
        message: "创建块失败，已中止替换。飞书返回 code=1770032 msg=forBidden",
      }),
      event({
        timestamp: 130,
        status: "uploaded",
        message: "上传完成",
      }),
    ], { includeInformational: false, unresolvedConflictCount: 0 });

    expect(groups.map((group) => group.problem.key)).toEqual([
      "docx_block_write_forbidden",
      "mirror_folder_forbidden",
    ]);
    expect(groups[0].entries).toHaveLength(1);
  });

  it("groups task queues with per-problem summaries", () => {
    const groups = buildTaskEventGroups([
      event({
        taskId: "task-1",
        taskName: "王远雄 - 工作记录",
        message: "创建云端文件夹失败: forbidden. (name=_LarkSync_MD_Mirror)",
      }),
      event({
        taskId: "task-2",
        taskName: "芯华 - 工作记录",
        status: "delete_failed",
        message: "删除文件失败: not found. token=abc type=folder",
      }),
    ], { includeInformational: false });

    expect(groups).toHaveLength(2);
    expect(groups[0].taskName).toBe("王远雄 - 工作记录");
    expect(groups[1].problemSummaries[0].count).toBe(1);
    expect(groups[1].problemSummaries[0].problem.title).toBe("删除状态已失效：云端目标不存在");
  });

  it("groups selected task events by sync run/process", () => {
    const groups = buildEventRunGroups([
      event({
        runId: "run-20260706-abcdef-123456",
        timestamp: 200,
        message: "创建块失败，已中止替换。飞书返回 code=1770032 msg=forBidden",
      }),
      event({
        runId: "run-20260706-abcdef-123456",
        timestamp: 180,
        message: "创建云端文件夹失败: forbidden. (name=_LarkSync_MD_Mirror)",
      }),
      event({
        runId: "run-old",
        timestamp: 100,
        status: "delete_pending",
        message: "检测到本地已删除，待处理删除同步",
      }),
    ], { includeInformational: false });

    expect(groups).toHaveLength(2);
    expect(groups[0].label).toContain("run-2026");
    expect(groups[0].problemSummaries.map((item) => item.problem.key)).toEqual([
      "docx_block_write_forbidden",
      "mirror_folder_forbidden",
    ]);
    expect(groups[1].problemSummaries[0].problem.key).toBe("delete_pending");
  });
});
