import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { ConflictResolutionPage } from "./ConflictResolutionPage";

const conflict = {
  id: "conflict-1",
  local_path: "D:/Knowledge/FeishuMirror/ProjectDocs/a.md",
  cloud_token: "doccn_cloud",
  local_hash: "localhash123456",
  db_hash: "dbhash123456",
  cloud_version: 3,
  db_version: 2,
  local_preview: "# Local",
  cloud_preview: "# Cloud",
  created_at: 3,
  resolved: false,
  resolved_action: null,
};

vi.mock("../hooks/useConflicts", () => ({
  useConflicts: () => ({
    conflicts: [conflict],
    conflictLoading: false,
    conflictError: null,
    refreshConflicts: vi.fn(),
    resolveConflictAsync: vi.fn(),
  }),
}));

vi.mock("../hooks/useConflictResolutionQueue", () => ({
  useConflictResolutionQueue: () => ({
    conflictResolutionStates: {},
    queueSummary: {
      queued: 0,
      running: 0,
      waiting: 0,
      success: 0,
      failed: 0,
    },
    handleResolveConflict: vi.fn(),
  }),
}));

vi.mock("../components/ui/toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

describe("ConflictResolutionPage smoke", () => {
  it("renders the dedicated conflict workspace and supported actions", () => {
    const html = renderToStaticMarkup(<ConflictResolutionPage />);

    expect(html).toContain("冲突队列");
    expect(html).toContain("版本对比");
    expect(html).toContain("本地版本");
    expect(html).toContain("云端版本");
    expect(html).toContain("处理状态");
    expect(html).toContain("使用云端");
    expect(html).toContain("使用本地");
    expect(html).toContain("保留双方");
    expect(html).toContain("后端尚未提供 keep_both");
    expect(html).toContain("grid-cols-[280px_minmax(0,1fr)_320px]");
    expect(html).toContain("grid-cols-2");
    expect(html).not.toContain("grid grid-cols-4 gap-4");
    expect(html).not.toContain("min-[1760px]");
    expect(html).not.toContain("min-[1440px]");
    expect(html).not.toContain("min-[1280px]:grid-cols-[300px_minmax(0,1fr)_320px]");
  });
});
