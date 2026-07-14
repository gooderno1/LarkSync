import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { MaintenancePage, getInstallTimelineSteps } from "./MaintenancePage";

vi.mock("../hooks/useUpdate", () => ({
  useUpdate: () => ({
    status: {
      current_version: "v0.8.0-dev.1",
      latest_version: "v0.8.0-dev.1",
      update_available: false,
      asset: null,
      last_check: 3,
      last_error: null,
      download_path: null,
      install_request: {
        request_id: "req-123",
        installer_path: "D:/downloads/LarkSync-Setup-v0.8.0.exe",
        created_at: 1800000000,
        silent: true,
        restart_path: null,
      },
      install_handoff: {
        request_id: "req-123",
        stage: "installer_started",
        message: "pid=1234",
        exit_code: 0,
        timestamp: 1800000001,
      },
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

vi.mock("../hooks/useConfig", () => ({
  useConfig: () => ({
    config: {
      sync_log_retention_days: 0,
      system_log_retention_days: 1,
      sync_log_warn_size_mb: 200,
      auto_update_enabled: false,
      update_check_interval_hours: 24,
    },
    saveConfig: vi.fn(),
    saving: false,
  }),
}));

vi.mock("../hooks/useTasks", () => ({
  useTasks: () => ({
    tasks: [],
    resetLinks: vi.fn(),
    resettingLinks: false,
  }),
}));

vi.mock("../components/ui/toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

vi.mock("../components/ui/confirm-dialog", () => ({
  confirm: vi.fn(),
}));

describe("MaintenancePage smoke", () => {
  it("renders the light maintenance workspace with shell-safe wide breakpoint", () => {
    const html = renderToStaticMarkup(<MaintenancePage />);

    expect(html).toContain("更新流程");
    expect(html).toContain("日志保留");
    expect(html).toContain("重置同步映射");
    expect(html).toContain("安装与交接");
    expect(html).toContain("安装器已启动");
    expect(html).toContain("req-123");
    expect(html).toContain("pid=1234");
    expect(html).toContain("grid-cols-[minmax(0,1fr)_360px]");
    expect(html).toContain("更新流程");
    expect(html).toContain("安装与交接");
    expect(html).not.toContain("min-[1760px]");
    expect(html).not.toContain("min-[1440px]:grid-cols-[minmax(0,1.05fr)_minmax(320px,0.95fr)]");
    expect(html).not.toContain("xl:grid-cols-[minmax(0,1.05fr)_minmax(320px,0.95fr)]");
  });

  it("derives conservative install handoff timeline states", () => {
    const steps = getInstallTimelineSteps({
      download_path: "D:/downloads/LarkSync-Setup-v0.8.0.exe",
      install_request: {
        request_id: "req-1",
        installer_path: "D:/downloads/LarkSync-Setup-v0.8.0.exe",
        created_at: 1800000000,
        silent: true,
      },
      install_handoff: {
        request_id: "req-1",
        stage: "restart_failed",
        message: "installed but restart did not stay alive",
      },
    });

    expect(steps.map((step) => `${step.label}:${step.state}:${step.tone}`)).toEqual([
      "校验通过:就绪:success",
      "托盘接管:已排队:info",
      "helper 启动:已接管:info",
      "静默安装:已完成:success",
      "自动重启:未确认:danger",
    ]);
  });
});
