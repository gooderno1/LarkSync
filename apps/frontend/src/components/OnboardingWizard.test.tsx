import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { OnboardingWizard } from "./OnboardingWizard";

const mockState = vi.hoisted(() => ({
  config: {} as Record<string, unknown>,
  auth: {
    loading: false,
    driveOk: false,
    accountName: null as string | null,
    deviceId: "dev-test",
  },
  authorize: {
    data: {
      authorize_url: "https://open.feishu.cn/oauth?state=state-1",
      state: "state-1",
      expires_in: 600,
      local_callback: true,
    },
    isLoading: false,
    isFetching: false,
    error: null as Error | null,
  },
  larkCli: {
    data: {
      installed: false,
      executable: null as string | null,
      brand: null as string | null,
      identity: null as string | null,
      verified: false,
      user: null as null | Record<string, unknown>,
      can_assist_oauth: false,
      message: "未检测到 lark-cli。可继续使用 LarkSync 原生 OAuth。",
      last_error: null as string | null,
      status_command: "lark-cli auth status --json --verify",
      login_command: "lark-cli auth login --domain docs --domain drive --no-wait --json",
      qrcode_command: 'lark-cli auth qrcode "<verification_url>" --output larksync-cli-auth.png',
    },
    isLoading: false,
    isFetching: false,
    error: null as Error | null,
    refetch: vi.fn(),
  },
  desktopStatus: {
    runtime: {
      backend_running: true,
      frontend_static_available: false,
      data_dir: "D:/Users/Alex/AppData/Roaming/LarkSync/data",
      database_url: "sqlite+aiosqlite:///D:/Users/Alex/AppData/Roaming/LarkSync/data/larksync.db",
      packaged: false,
    },
    auth: {
      connected: false,
      oauth_configured: false,
      open_id: null,
      account_name: null,
      device_id: "dev-test",
      expires_at: null,
    },
    tasks: {
      total: 0,
      enabled: 0,
      paused: 0,
      running: 0,
      failed: 0,
      last_error: null,
      last_sync_time: null,
    },
    conflicts: {
      unresolved: 0,
    },
    update: {
      current_version: "v0.8.0-dev.1",
      latest_version: null,
      update_available: false,
      last_check: null,
      last_error: null,
      download_path: null,
    },
  },
}));

vi.mock("@tanstack/react-query", () => ({
  useQuery: (options: { queryKey?: readonly unknown[] }) => (
    options.queryKey?.[0] === "auth-cli-status" ? mockState.larkCli : mockState.authorize
  ),
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}));

vi.mock("../hooks/useConfig", () => ({
  useConfig: () => ({
    config: mockState.config,
    saveConfig: vi.fn(),
    saving: false,
  }),
}));

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => mockState.auth,
}));

vi.mock("../hooks/useDesktopStatus", () => ({
  useDesktopStatus: () => ({
    status: mockState.desktopStatus,
    error: null,
    isFetching: false,
    refetch: vi.fn(),
  }),
}));

vi.mock("./ui/toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

vi.mock("qrcode", () => ({
  toDataURL: vi.fn(),
}));

describe("OnboardingWizard smoke", () => {
  beforeEach(() => {
    mockState.config = {};
    mockState.auth = {
      loading: false,
      driveOk: false,
      accountName: null,
      deviceId: "dev-test",
    };
    mockState.authorize = {
      data: {
        authorize_url: "https://open.feishu.cn/oauth?state=state-1",
        state: "state-1",
        expires_in: 600,
        local_callback: true,
      },
      isLoading: false,
      isFetching: false,
      error: null,
    };
    mockState.larkCli = {
      data: {
        installed: false,
        executable: null,
        brand: null,
        identity: null,
        verified: false,
        user: null as null | Record<string, unknown>,
        can_assist_oauth: false,
        message: "未检测到 lark-cli。可继续使用 LarkSync 原生 OAuth。",
        last_error: null,
        status_command: "lark-cli auth status --json --verify",
        login_command: "lark-cli auth login --domain docs --domain drive --no-wait --json",
        qrcode_command: 'lark-cli auth qrcode "<verification_url>" --output larksync-cli-auth.png',
      },
      isLoading: false,
      isFetching: false,
      error: null,
      refetch: vi.fn(),
    };
  });

  it("renders the light OAuth configuration workspace before app credentials exist", () => {
    const html = renderToStaticMarkup(<OnboardingWizard oauthConfigured={false} connected={false} />);

    expect(html).toContain("连接飞书工作区");
    expect(html).toContain("窗口宿主");
    expect(html).toContain("后端服务");
    expect(html).toContain("开发服务");
    expect(html).toContain("数据目录");
    expect(html).toContain("扫码授权");
    expect(html).toContain("高级 OAuth 配置");
    expect(html).toContain("App ID");
    expect(html).toContain("App Secret");
    expect(html).toContain("Redirect URI");
    expect(html).toContain("CLI 辅助授权");
    expect(html).toContain("未检测到 lark-cli");
    expect(html).toContain("grid-cols-[310px_minmax(0,1fr)_360px]");
    expect(html).not.toContain("min-[1440px]");
    expect(html).not.toContain("bg-zinc-900/70");
  });

  it("renders browser fallback and local callback warning after OAuth is configured", () => {
    mockState.config = { auth_client_id: "cli_test" };
    mockState.larkCli.data = {
      installed: true,
      executable: "lark-cli.cmd",
      brand: "feishu",
      identity: "user",
      verified: true,
      user: {
        available: true,
        verified: true,
        status: "ready",
        token_status: "valid",
        user_name: "测试用户",
        open_id_present: true,
        scope_count: 3,
        docs_scope_detected: true,
        drive_scope_detected: true,
        expires_at: null,
        refresh_expires_at: null,
      },
      can_assist_oauth: true,
      message: "lark-cli 用户身份可用，可作为后续设备码授权方案的辅助状态。",
      last_error: null,
      status_command: "lark-cli auth status --json --verify",
      login_command: "lark-cli auth login --domain docs --domain drive --no-wait --json",
      qrcode_command: 'lark-cli auth qrcode "<verification_url>" --output larksync-cli-auth.png',
    };
    const html = renderToStaticMarkup(<OnboardingWizard oauthConfigured connected={false} />);

    expect(html).toContain("在浏览器打开");
    expect(html).toContain("复制授权链接");
    expect(html).toContain("当前回调地址是本机地址");
    expect(html).toContain("待授权");
    expect(html).toContain("CLI 可用");
    expect(html).toContain("测试用户");
    expect(html).toContain("docs 权限");
    expect(html).toContain("drive 权限");
    expect(html).toContain("当前主流程仍使用 LarkSync 原生 OAuth");
  });
});
