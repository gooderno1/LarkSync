import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { SettingsOAuthPanel } from "./SettingsOAuthPanel";
import { SettingsSyncStrategyPanel } from "./SettingsSyncStrategyPanel";
import { SettingsMorePanel } from "./SettingsMorePanel";
import { SettingsGeneralPanel } from "./SettingsGeneralPanel";
import { SettingsIgnoredDirectoriesPanel } from "./SettingsIgnoredDirectoriesPanel";
import type { SyncTask } from "../../types";

const task: SyncTask = {
  id: "task-1",
  name: "知识库同步",
  local_path: "D:/Knowledge/Base",
  cloud_folder_token: "fld_123",
  sync_mode: "bidirectional",
  enabled: true,
  created_at: 1,
  updated_at: 2,
};

describe("settings panels", () => {
  it("renders oauth and sync strategy panels", () => {
    const html = renderToStaticMarkup(
      <>
        <SettingsOAuthPanel
          clientId="cli_123"
          setClientId={vi.fn()}
          clientSecret=""
          setClientSecret={vi.fn()}
          redirectUri="http://localhost:8000/auth/callback"
          copyRedirectUri={vi.fn()}
          handleSave={vi.fn()}
          saving={false}
          saveError={null}
          showAdvanced={false}
          toggleAdvanced={vi.fn()}
          authorizeUrl=""
          setAuthorizeUrl={vi.fn()}
          tokenUrl=""
          setTokenUrl={vi.fn()}
          tokenStore="keyring"
          setTokenStore={vi.fn()}
          inputCls="input"
        />
        <SettingsSyncStrategyPanel
          syncMode="bidirectional"
          setSyncMode={vi.fn()}
          uploadEnabled
          downloadEnabled
          uploadValue="60"
          setUploadValue={vi.fn()}
          uploadUnit="seconds"
          setUploadUnit={vi.fn()}
          uploadTime="01:00"
          setUploadTime={vi.fn()}
          downloadValue="1"
          setDownloadValue={vi.fn()}
          downloadUnit="days"
          setDownloadUnit={vi.fn()}
          downloadTime="01:00"
          setDownloadTime={vi.fn()}
          handleSave={vi.fn()}
          saving={false}
        />
      </>,
    );

    expect(html).toContain("OAuth 配置");
    expect(html).toContain("同步策略");
    expect(html).toContain("双向同步");
    expect(html).toContain("grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.25fr)]");
    expect(html).toContain("min-h-[72px]");
    expect(html).toContain("计划设置");
    expect(html).toContain("border-[#d7e4f5]");
    expect(html).not.toContain("bg-zinc-900/60");
    expect(html).not.toContain("border-zinc-800");
  });

  it("renders more settings panels", () => {
    const html = renderToStaticMarkup(
      <SettingsMorePanel
        showMoreSettings
        toggleMoreSettings={vi.fn()}
        handleSaveMoreSettings={vi.fn()}
        saving={false}
      >
        <SettingsGeneralPanel
          inputCls="input"
          deviceDisplayName="开发机"
          setDeviceDisplayName={vi.fn()}
        />
        <SettingsIgnoredDirectoriesPanel
          tasks={[task]}
          showIgnoredDirectorySettings
          toggleIgnoredDirectorySettings={vi.fn()}
          ignoreHiddenCachePaths
          setIgnoreHiddenCachePaths={vi.fn()}
          ignoredSubpathsMap={{ "task-1": ["node_modules"] }}
          ignoredPathDrafts={{}}
          setIgnoredPathDrafts={vi.fn()}
          updatingIgnoredSubpaths={false}
          handleSaveIgnoredSubpaths={vi.fn(async () => undefined)}
          removeIgnoredSubpath={vi.fn()}
          addIgnoredSubpath={vi.fn()}
          pickingIgnoredTaskId={null}
          handlePickIgnoredSubpath={vi.fn(async () => undefined)}
        />
      </SettingsMorePanel>,
    );

    expect(html).toContain("更多设置");
    expect(html).toContain("当前设备");
    expect(html).toContain("本地忽略目录");
    expect(html).toContain("默认忽略隐藏/缓存路径");
    expect(html).not.toContain("自动更新");
    expect(html).not.toContain("维护工具");
    expect(html).not.toContain("bg-zinc-900/60");
    expect(html).not.toContain("border-zinc-800");
  });
});
