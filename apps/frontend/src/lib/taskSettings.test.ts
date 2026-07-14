import { describe, expect, it } from "vitest";

import {
  buildTaskSettingsPatch,
  countTaskSettingsChanges,
  createTaskSettingsDraft,
  getTaskSettingsRisk,
} from "./taskSettings";
import type { SyncTask } from "../types";

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

describe("taskSettings", () => {
  it("creates an editable draft from persisted task settings", () => {
    expect(createTaskSettingsDraft(task)).toEqual({
      syncMode: "download_only",
      updateMode: "auto",
      mdSyncMode: "download_only",
      deletePolicy: "safe",
      deleteGraceMinutes: "30",
    });
  });

  it("counts changed setting groups and builds one combined patch", () => {
    const draft = {
      ...createTaskSettingsDraft(task),
      syncMode: "bidirectional",
      mdSyncMode: "enhanced" as const,
      deletePolicy: "strict" as const,
      deleteGraceMinutes: "99",
    };

    expect(countTaskSettingsChanges(task, draft)).toBe(3);
    expect(buildTaskSettingsPatch(task, draft)).toEqual({
      sync_mode: "bidirectional",
      md_sync_mode: "enhanced",
      delete_policy: "strict",
      delete_grace_minutes: 0,
    });
  });

  it("derives risk from cloud write ability and delete policy", () => {
    expect(getTaskSettingsRisk("download_only", "safe").label).toBe("低风险");
    expect(getTaskSettingsRisk("bidirectional", "safe").label).toBe("中风险");
    expect(getTaskSettingsRisk("download_only", "strict").label).toBe("高风险");
  });
});
