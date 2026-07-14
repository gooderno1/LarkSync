import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { TaskSettingsPanel } from "./TaskSettingsPanel";
import type { SyncTask } from "../../types";

const task: SyncTask = {
  id: "task-1",
  name: "资料同步",
  local_path: "D:/Docs",
  cloud_folder_token: "folder_token",
  cloud_folder_name: "资料库",
  base_path: null,
  sync_mode: "download_only",
  update_mode: "auto",
  md_sync_mode: "download_only",
  delete_policy: "safe",
  delete_grace_minutes: 30,
  enabled: true,
  created_at: 1,
  updated_at: 2,
  last_run_at: null,
};

describe("TaskSettingsPanel", () => {
  it("renders one coherent settings workflow with a single save action", () => {
    const html = renderToStaticMarkup(
      <TaskSettingsPanel
        task={task}
        processed={0}
        total={0}
        onClose={vi.fn()}
        onDelete={vi.fn()}
        onSave={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    expect(html).toContain('data-task-settings-panel="true"');
    expect(html).toContain("任务设置");
    expect(html).toContain("内容流向");
    expect(html).toContain("写入方式");
    expect(html).toContain("删除联动");
    expect(html).toContain("变更摘要");
    expect(html).toContain("维护操作");
    expect(html).toContain("保存更改");
    expect(html).toContain("尚未修改");
    expect(html).toContain("grid-cols-[minmax(0,1fr)_272px]");
    expect(html).toContain('aria-label="关闭任务设置"');
    expect(html).toContain('aria-pressed="true"');
    expect(html).toContain("当前任务为仅下载，不会写入云端");
    expect((html.match(/disabled=""/g) || []).length).toBeGreaterThanOrEqual(1);
    expect((html.match(/保存更改/g) || [])).toHaveLength(1);
    expect(html).not.toContain(">应用<");
  });
});
