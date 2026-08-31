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

vi.mock("../hooks/useTasks", () => ({
  useTasks: () => ({
    tasks: [],
    updateIgnoredSubpaths: vi.fn(),
    updatingIgnoredSubpaths: false,
  }),
}));

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    connected: true,
    accountName: "张三",
    deviceId: "4d6c2e1f-8b12-4eac-9b56",
    logout: vi.fn(),
  }),
}));

vi.mock("../hooks/useAutostart", () => ({
  useAutostart: () => ({
    autostart: {
      supported: true,
      enabled: true,
      platform: "windows",
    },
    autostartLoading: false,
    updatingAutostart: false,
    setAutostart: vi.fn().mockResolvedValue(undefined),
  }),
}));

vi.mock("../components/ui/toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

describe("SettingsPage smoke", () => {
  it("renders the natural-height responsive settings workspace", () => {
    const html = renderToStaticMarkup(<SettingsPage />);
    const contextTitleIndex = html.indexOf("飞书账号与当前设备");
    const currentDeviceIndex = html.indexOf(">当前设备<", contextTitleIndex);

    expect(html).toContain("管理飞书账号、当前设备、默认同步行为和本地规则。");
    expect(html).toContain("飞书账号与当前设备");
    expect(html).toContain("飞书账号");
    expect(html).toContain("飞书已连接");
    expect(html).toContain("当前设备");
    expect(html).toContain("开机自启动");
    expect(html).toContain("登录当前系统账号后自动启动 LarkSync");
    expect(html).toContain('role="switch"');
    expect(html).toContain('aria-checked="true"');
    expect(html).toContain("默认同步策略");
    expect(html).toContain("忽略规则");
    expect(html).toContain("高级 OAuth");
    expect(html).toContain("仅在更换应用凭证或授权端点时修改。");
    expect(html).toContain("同步策略");
    expect(html).toContain("本地忽略目录");
    expect(html).toContain('data-settings-context="true"');
    expect(html).toContain('data-settings-context-title="true"');
    expect(html).toContain('data-settings-workspace="true"');
    expect(html).toContain('data-settings-primary-column="true"');
    expect(html).toContain('data-settings-auxiliary-column="true"');
    expect(html).toContain('data-settings-page="true"');
    expect(html).toContain("grid-cols-1");
    expect(html).toContain("items-start");
    expect(html).toContain("min-[900px]:grid-cols-[minmax(0,1fr)_minmax(380px,420px)]");
    expect(html).toContain("min-[1200px]:gap-5");
    expect(html).toContain("grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]");
    expect(html).toContain('data-settings-account-panel="true"');
    expect(html).toContain('data-settings-device-panel="true"');
    expect(html).toContain('data-settings-strategy-header="true"');
    expect(html).not.toContain("data-settings-scroll-region");
    expect(html).not.toContain("overflow-y-auto");
    expect(html).not.toContain("max-w-[1240px]");
    expect(html.match(/保存设置/g)).toHaveLength(1);
    expect(html).not.toContain("保存策略");
    expect(html).not.toContain("保存配置");
    expect(html).not.toContain("App Secret");
    expect(html).not.toContain("Redirect URI");
    expect(html).toContain('aria-expanded="false"');
    expect(contextTitleIndex).toBeLessThan(currentDeviceIndex);
    expect(currentDeviceIndex).toBeLessThan(html.indexOf("默认同步策略"));
    expect(html.indexOf("默认同步策略")).toBeLessThan(html.indexOf("高级 OAuth"));
    expect(html.indexOf("高级 OAuth")).toBeLessThan(html.indexOf("忽略规则"));
    expect(html.indexOf("忽略规则")).toBeLessThan(html.indexOf("数据保护"));
    expect(html).not.toContain("自动更新");
    expect(html).not.toContain("重置同步映射");
    expect(html).not.toContain("bg-zinc-900/60");
    expect(html).not.toContain("border-zinc-800");
  });
});
