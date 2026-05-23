import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { SettingsPage } from "./SettingsPage";

vi.mock("../hooks/useConfig", () => ({
  useConfig: () => ({
    config: {
      auth_authorize_url: "https://open.feishu.cn/open-apis/authen/v1/authorize",
      auth_token_url: "https://open.feishu.cn/open-apis/authen/v1/access_token",
      auth_client_id: "cli_123",
      sync_mode: "bidirectional",
      ignore_hidden_cache_paths: true,
      token_store: "keyring",
      upload_interval_value: 60,
      upload_interval_unit: "seconds",
      upload_daily_time: "01:00",
      download_interval_value: 1,
      download_interval_unit: "days",
      download_daily_time: "01:00",
      sync_log_retention_days: 0,
      sync_log_warn_size_mb: 200,
      system_log_retention_days: 1,
      auto_update_enabled: true,
      update_check_interval_hours: 24,
      allow_dev_to_stable: false,
      device_display_name: "开发机",
    },
    configLoading: false,
    saveConfig: vi.fn().mockResolvedValue(undefined),
    saving: false,
    saveError: null,
  }),
}));

vi.mock("../hooks/useUpdate", () => ({
  useUpdate: () => ({
    status: {
      current_version: "v0.7.16",
      latest_version: "v0.7.16",
      published_at: "2026-05-22T00:00:00Z",
      last_check: 1_747_872_000,
    },
    checkUpdate: vi.fn(),
    checking: false,
    downloadUpdate: vi.fn(),
    downloading: false,
    installUpdate: vi.fn(),
    installing: false,
    openUpdateFolder: vi.fn(),
    openingUpdateFolder: false,
  }),
}));

vi.mock("../hooks/useTasks", () => ({
  useTasks: () => ({
    tasks: [],
    resetLinks: vi.fn(),
    resettingLinks: false,
    updateIgnoredSubpaths: vi.fn(),
    updatingIgnoredSubpaths: false,
  }),
}));

vi.mock("../components/ui/toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

vi.mock("../components/ThemeToggle", () => ({
  ThemeToggle: () => <div>Theme Toggle</div>,
}));

describe("SettingsPage smoke", () => {
  it("renders OAuth, sync strategy and advanced settings sections", () => {
    const html = renderToStaticMarkup(<SettingsPage />);

    expect(html).toContain("OAuth 配置");
    expect(html).toContain("同步策略");
    expect(html).toContain("更多设置");
  });
});
