import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { TaskCard } from "./TaskCard";
import { TasksEmptyState } from "./TasksEmptyState";
import { TasksPageHeader } from "./TasksPageHeader";
import type { SyncTask } from "../../types";

vi.mock("../ThemeToggle", () => ({
  ThemeToggle: () => <div>Theme Toggle</div>,
}));

const task: SyncTask = {
  id: "task-1",
  name: "示例任务",
  local_path: "C:/workspace/docs",
  cloud_folder_token: "folder-token",
  cloud_folder_name: "飞书/文档",
  base_path: "C:/workspace",
  sync_mode: "bidirectional",
  update_mode: "auto",
  md_sync_mode: "enhanced",
  delete_policy: "safe",
  delete_grace_minutes: 30,
  enabled: true,
  created_at: 0,
  updated_at: 0,
};

describe("task panels smoke", () => {
  it("renders task page header and empty state", () => {
    const html = renderToStaticMarkup(
      <>
        <TasksPageHeader
          showTestToggle
          hideTestTasks
          onToggleTestTasks={vi.fn()}
          onRefresh={vi.fn()}
          onCreate={vi.fn()}
        />
        <TasksEmptyState hasAnyTasks={false} hideTestTasks testTaskCount={0} />
      </>
    );

    expect(html).toContain("同步任务");
    expect(html).toContain("搜索任务");
    expect(html).toContain("全部状态");
    expect(html).toContain("全部模式");
    expect(html).toContain("全部健康");
    expect(html).toContain("暂无同步任务");
    expect(html).toContain("border-[#c9d8ec]");
    expect(html).not.toContain("bg-zinc-900/60");
    expect(html).not.toContain("border-zinc-800");
  });

  it("renders task card shell", () => {
    const html = renderToStaticMarkup(
      <TaskCard
        task={task}
        status={{
          task_id: task.id,
          state: "idle",
          total_files: 10,
          completed_files: 5,
          failed_files: 0,
          skipped_files: 1,
          uploaded_files: 2,
          downloaded_files: 3,
          deleted_files: 0,
          conflict_files: 0,
          delete_pending_files: 0,
          delete_failed_files: 0,
          last_files: [],
        }}
        conflictCount={0}
        expanded
        onToggleExpanded={vi.fn()}
        localPathExpanded={false}
        cloudPathExpanded={false}
        onTogglePath={vi.fn()}
        syncModeValue="bidirectional"
        updateModeValue="auto"
        mdSyncModeValue="enhanced"
        deletePolicyValue="safe"
        deleteGraceValue="30"
        onSyncModeChange={vi.fn()}
        onUpdateModeChange={vi.fn()}
        onMdSyncModeChange={vi.fn()}
        onDeletePolicyChange={vi.fn()}
        onDeleteGraceChange={vi.fn()}
        onApplySyncMode={vi.fn()}
        onApplyUpdateMode={vi.fn()}
        onApplyMdSyncMode={vi.fn()}
        onApplyDeletePolicy={vi.fn()}
        onRun={vi.fn()}
        onToggleEnabled={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    expect(html).toContain("示例任务");
    expect(html).toContain("收起管理");
    expect(html).toContain("同步模式");
    expect(html).toContain("bg-[#f8fbff]");
    expect(html).not.toContain("bg-zinc-900/60");
    expect(html).not.toContain("bg-zinc-950/50");
  });
});
