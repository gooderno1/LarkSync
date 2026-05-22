import { describe, expect, it } from "vitest";

import {
  buildCreateTaskPayload,
  extractCloudFolderToken,
  resolveManualCloudSelection,
} from "./newTaskWizard";

describe("newTaskWizard", () => {
  it("extracts folder token from link or raw token", () => {
    expect(extractCloudFolderToken("https://host/drive/folder/abc_123?from=share")).toBe("abc_123");
    expect(extractCloudFolderToken("abc_123")).toBe("abc_123");
    expect(extractCloudFolderToken("not a token!")).toBeNull();
  });

  it("resolves manual cloud selection and validation error", () => {
    expect(resolveManualCloudSelection("bad url", "").error).toBe("未识别到有效的共享链接或 Token。");
    expect(resolveManualCloudSelection("folder_token", "共享目录").selection).toEqual({
      token: "folder_token",
      name: "共享目录",
      path: "共享目录",
    });
  });

  it("builds create payload with strict delete override", () => {
    expect(
      buildCreateTaskPayload({
        taskName: " Demo ",
        taskLocalPath: " C:/demo ",
        taskCloudToken: " token ",
        selectedCloud: { token: "token", name: "云端", path: "云端/目录" },
        taskBasePath: " ",
        taskSyncMode: "download_only",
        taskUpdateMode: "auto",
        taskMdSyncMode: "enhanced",
        taskUploadEnabled: false,
        taskDeletePolicy: "strict",
        taskDeleteGraceMinutes: "30",
        taskEnabled: true,
      })
    ).toMatchObject({
      name: "Demo",
      local_path: "C:/demo",
      cloud_folder_token: "token",
      cloud_folder_name: "云端/目录",
      base_path: null,
      md_sync_mode: "download_only",
      delete_policy: "strict",
      delete_grace_minutes: 0,
      enabled: true,
    });
  });
});
