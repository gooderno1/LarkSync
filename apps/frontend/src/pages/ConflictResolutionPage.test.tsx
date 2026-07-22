import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { ConflictResolutionPage } from "./ConflictResolutionPage";

const problem = {
  id: "problem-1",
  fingerprint: "fingerprint",
  category: "upload",
  severity: "high" as const,
  state: "open" as const,
  title: "上传失败 · a.md",
  summary: "文件没有成功写入云端。",
  task_id: "task-1",
  object_kind: "sync_event",
  object_key: "a.md",
  object_path: "a.md",
  first_seen_at: 1,
  last_seen_at: 3,
  occurrence_count: 2,
  latest_run_id: "run-1",
  latest_event_id: "event-1",
  classifier_version: "problem-classifier-v1",
  resolution_verification: null,
  resolved_at: null,
  ignored_reason: null,
  available_actions: [
    { key: "retry_task" as const, label: "重试任务", tone: "primary", requires_confirmation: false },
    { key: "open_local_folder" as const, label: "打开本地目录", tone: "neutral", requires_confirmation: false },
  ],
};

vi.mock("../hooks/useTasks", () => ({
  useTasks: () => ({ tasks: [{ id: "task-1", name: "项目文档同步" }] }),
}));

vi.mock("../hooks/useProblems", () => ({
  useProblems: () => ({
    problems: [problem],
    total: 1,
    summary: { unresolved: 1, by_state: { open: 1 }, by_category: { upload: 1 }, by_severity: { high: 1 } },
    detail: {
      problem,
      history: {
        occurrences: [{ id: "occ-1", problem_id: "problem-1", source_kind: "sync_event", source_id: "event-1", occurred_at: 3, evidence: { status: "failed", message: "HTTP 503" } }],
        actions: [],
      },
    },
    loading: false,
    fetching: false,
    error: null,
    actionPending: false,
    verifyPending: false,
    executeAction: vi.fn(),
    verifyProblem: vi.fn(),
    refresh: vi.fn(),
  }),
}));

vi.mock("../components/ui/toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

describe("ConflictResolutionPage smoke", () => {
  it("renders the standard two-column problem center with backend actions", () => {
    const html = renderToStaticMarkup(<ConflictResolutionPage layoutMode="standard" />);

    expect(html).toContain("问题中心");
    expect(html).toContain("上传失败 · a.md");
    expect(html).toContain("诊断");
    expect(html).toContain("证据");
    expect(html).toContain("处理记录");
    expect(html).toContain("重试任务");
    expect(html).toContain("打开本地目录");
    expect(html).toContain("上一页");
    expect(html).toContain("下一页");
    expect(html).toContain('data-problem-center="true"');
    expect(html).toContain('data-window-layout="standard"');
    expect(html).toContain("grid-cols-[288px_minmax(680px,1fr)]");
    expect(html).not.toContain("保留双方");
    expect(html).not.toContain("批量处理");
  });

  it("renders compact as a queue-only master state", () => {
    const html = renderToStaticMarkup(<ConflictResolutionPage layoutMode="compact" />);

    expect(html).toContain('data-window-layout="compact"');
    expect(html).toContain('data-problem-queue="true"');
    expect(html).not.toContain('data-problem-workbench="true"');
    expect(html).not.toContain('data-problem-actions="true"');
  });

  it("renders wide with queue, diagnosis and action columns", () => {
    const html = renderToStaticMarkup(<ConflictResolutionPage layoutMode="wide" />);

    expect(html).toContain('data-window-layout="wide"');
    expect(html).toContain("grid-cols-[288px_minmax(520px,1fr)_320px]");
    expect(html).toContain('data-problem-workbench="true"');
    expect(html).toContain('data-problem-actions="true"');
  });
});
