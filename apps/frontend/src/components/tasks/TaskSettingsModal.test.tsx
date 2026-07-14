import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { TaskSettingsDialog } from "./TaskSettingsModal";
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

describe("TaskSettingsDialog", () => {
  it("renders task settings as an accessible modal instead of an inline row", () => {
    const html = renderToStaticMarkup(
      <TaskSettingsDialog
        task={task}
        processed={0}
        total={0}
        onClose={vi.fn()}
        onDelete={vi.fn()}
        onSave={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    expect(html).toContain('data-task-settings-modal="true"');
    expect(html).toContain('role="dialog"');
    expect(html).toContain('aria-modal="true"');
    expect(html).toContain('aria-labelledby="task-settings-dialog-title"');
    expect(html).toContain("w-[1040px]");
    expect(html).toContain("max-h-[88vh]");
    expect(html).toContain('data-task-settings-panel="true"');
    expect(html).not.toContain("<tr");
  });
});
