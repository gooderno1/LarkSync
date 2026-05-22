import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { SettingsOAuthPanel } from "./SettingsOAuthPanel";
import { SettingsSyncStrategyPanel } from "./SettingsSyncStrategyPanel";
import { SettingsMorePanel } from "./SettingsMorePanel";
import { SettingsGeneralPanel } from "./SettingsGeneralPanel";
import { SettingsUpdatePanel } from "./SettingsUpdatePanel";
import { SettingsIgnoredDirectoriesPanel } from "./SettingsIgnoredDirectoriesPanel";
import { SettingsMaintenancePanel } from "./SettingsMaintenancePanel";
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
          themeSlot={<div>Theme Toggle</div>}
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
          syncLogRetentionDays="0"
          setSyncLogRetentionDays={vi.fn()}
          syncLogWarnSizeMb="200"
          setSyncLogWarnSizeMb={vi.fn()}
          systemLogRetentionDays="1"
          setSystemLogRetentionDays={vi.fn()}
        />
        <SettingsUpdatePanel
          status={{
            current_version: "v0.7.17",
            latest_version: "v0.7.18",
            update_available: true,
            download_path: "D:/Temp/LarkSync.exe",
            asset: { name: "LarkSync.exe", url: "https://example.com" },
          }}
          inputCls="input"
          autoUpdateEnabled
          setAutoUpdateEnabled={vi.fn()}
          updateCheckIntervalHours="24"
          setUpdateCheckIntervalHours={vi.fn()}
          allowDevToStable={false}
          setAllowDevToStable={vi.fn()}
          handleCheckUpdate={vi.fn()}
          checking={false}
          handleDownloadUpdate={vi.fn()}
          downloading={false}
          installing={false}
          handleOpenDownloadedUpdateFolder={vi.fn()}
          openingUpdateFolder={false}
          handleInstallDownloadedUpdate={vi.fn()}
          lastCheckLabel="今天"
          publishedLabel="今天"
        />
        <SettingsIgnoredDirectoriesPanel
          tasks={[task]}
          showIgnoredDirectorySettings
          toggleIgnoredDirectorySettings={vi.fn()}
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
        <SettingsMaintenancePanel
          tasks={[task]}
          resettingLinks={false}
          onResetTask={vi.fn(async () => undefined)}
        />
      </SettingsMorePanel>,
    );

    expect(html).toContain("更多设置");
    expect(html).toContain("自动更新");
    expect(html).toContain("本地忽略目录");
    expect(html).toContain("维护工具");
  });
});
