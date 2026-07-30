import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import {
  MaintenancePage,
  getInstallTimelineSteps,
  getUpdateActionVisibility,
  shouldAutoExpandInstallDetails,
} from "./MaintenancePage";

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
      phase: "downloading",
      progress: {
        percent: 42,
        bytes_per_second: 4 * 1024 * 1024,
        transferred: 24 * 1024 * 1024,
        total: 57 * 1024 * 1024,
      },
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
    tasks: [{ id: "task-hidden", name: "默认不展示的危险任务", local_path: "D:/Hidden" }],
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
  it("renders one natural-height responsive dual-panel workspace with module-owned actions", () => {
    const html = renderToStaticMarkup(<MaintenancePage />);

    expect(html).toContain("版本与安装");
    expect(html).toContain("版本与更新");
    expect(html).toContain("本机维护");
    expect(html).toContain("日志管理");
    expect(html).toContain("危险操作");
    expect(html).toContain("正在下载安装包");
    expect(html).toContain("42%");
    expect(html).toContain("24.0 MB / 57.0 MB");
    expect(html).toContain("4.0 MB/s");
    expect(html).toContain('role="progressbar"');
    expect(html).toContain("重置同步映射");
    expect(html).toContain("安装详情");
    expect(html).toContain("选择任务");
    expect(html).toContain("保存更新设置");
    expect(html).toContain("保存日志设置");
    expect(html).not.toContain("保存维护设置");
    expect(html).toContain('data-maintenance-workspace="true"');
    expect(html).toContain('data-maintenance-page="true"');
    expect(html).toContain('data-maintenance-panel="version-install"');
    expect(html).toContain('data-maintenance-panel="local-maintenance"');
    expect(html).toContain('data-maintenance-section="install-details"');
    expect(html).toContain('data-maintenance-section="log-management"');
    expect(html).toContain('data-maintenance-section="danger"');
    expect(html).toContain('data-maintenance-action="check-update"');
    expect(html).not.toContain("data-maintenance-scroll-region");
    expect(html).not.toContain('data-page-primary-action="check-update"');
    expect(html).not.toContain("max-w-[1240px]");
    expect(html).toContain(
      'data-maintenance-page="true" class="mx-auto min-w-0 w-full max-w-[1440px] animate-fade-up"',
    );
    expect(html).toContain(
      'data-maintenance-workspace="true" class="mt-5 grid min-w-0 grid-cols-1 items-start gap-4 min-[900px]:grid-cols-[minmax(0,3fr)_minmax(360px,2fr)] min-[1200px]:gap-5"',
    );
    expect(html).not.toContain("grid-rows-[auto_minmax(0,1fr)]");
    expect(html).not.toContain('class="mt-auto border-t');
    expect(html.match(/检查更新/g)).toHaveLength(1);
    expect(html).not.toContain("默认不展示的危险任务");
    expect(html).toContain("安装器已启动");
    expect(html).toContain("req-123");
    expect(html).toContain("pid=1234");
    expect(html).toContain("min-[900px]:grid-cols-[minmax(0,3fr)_minmax(360px,2fr)]");
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

  it("only exposes update actions that are meaningful for the current state", () => {
    expect(
      getUpdateActionVisibility(
        { phase: "up_to_date", update_available: false, download_path: null },
        { downloadActive: false, installing: false },
      ),
    ).toEqual({
      showDownload: false,
      showOpenFolder: false,
      showInstall: false,
      disableDownload: false,
      disableInstall: false,
    });

    expect(
      getUpdateActionVisibility(
        { phase: "available", update_available: true, download_path: null },
        { downloadActive: false, installing: false },
      ),
    ).toMatchObject({
      showDownload: true,
      showOpenFolder: false,
      showInstall: false,
    });

    expect(
      getUpdateActionVisibility(
        {
          phase: "downloaded",
          update_available: true,
          download_path: "D:/downloads/LarkSync-Setup.exe",
        },
        { downloadActive: false, installing: false },
      ),
    ).toMatchObject({
      showDownload: false,
      showOpenFolder: true,
      showInstall: true,
    });
  });

  it("auto-expands install details only for active, failed, or unconfirmed handoff", () => {
    expect(
      shouldAutoExpandInstallDetails({
        install_request: {
          request_id: "req-active",
          installer_path: "D:/downloads/LarkSync-Setup.exe",
          created_at: 1800000000,
          silent: true,
        },
      }),
    ).toBe(true);
    expect(
      shouldAutoExpandInstallDetails({
        install_handoff: {
          request_id: "req-failed",
          stage: "restart_failed",
        },
      }),
    ).toBe(true);
    expect(
      shouldAutoExpandInstallDetails({
        install_handoff: {
          request_id: "req-done",
          stage: "restart_succeeded",
        },
      }),
    ).toBe(false);
    expect(shouldAutoExpandInstallDetails({})).toBe(false);
  });
});
