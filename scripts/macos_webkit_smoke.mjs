#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { webkit } from "../apps/frontend/node_modules/playwright/index.mjs";

function readArgument(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || !process.argv[index + 1]) {
    throw new Error(`${name} 缺少参数值`);
  }
  return process.argv[index + 1];
}

const url = readArgument("--url");
const resultPath = path.resolve(readArgument("--result"));
const mockApi = process.argv.includes("--mock-api");
const screenshotPath = resultPath.replace(/\.json$/u, ".png");
let browser;
let payload;

async function publish(value) {
  await fs.mkdir(path.dirname(resultPath), { recursive: true });
  const temporaryPath = `${resultPath}.tmp`;
  await fs.writeFile(temporaryPath, JSON.stringify(value), "utf8");
  await fs.rename(temporaryPath, resultPath);
}

await publish({ ok: false, completed: false, stage: "starting", engine: "playwright-webkit" });

try {
  browser = await webkit.launch({ headless: true, timeout: 15000 });
  await publish({
    ok: false,
    completed: false,
    stage: "browser_launched",
    engine: "playwright-webkit",
  });
  const page = await browser.newPage({ viewport: { width: 1080, height: 720 } });
  if (mockApi) {
    await page.route("**/*", (route) => {
      const requestUrl = new URL(route.request().url());
      const requestMethod = route.request().method();
      const json = (body) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(body),
        });
      const registrationSession = {
        session_id: "registration-webkit-smoke",
        status: "pending",
        brand: "feishu",
        user_code: "WEBKIT",
        verification_uri: "https://accounts.feishu.cn/device",
        verification_uri_complete: "https://accounts.feishu.cn/device?user_code=WEBKIT",
        expires_at: Math.floor(Date.now() / 1000) + 600,
        interval: 1,
      };
      const deviceSession = {
        session_id: "device-webkit-smoke",
        status: "pending",
        brand: "feishu",
        user_code: "LOGIN",
        verification_uri: "https://accounts.feishu.cn/device",
        verification_uri_complete: "https://accounts.feishu.cn/device?user_code=LOGIN",
        expires_at: Math.floor(Date.now() / 1000) + 600,
        interval: 60,
      };
      if (requestUrl.pathname === "/accounts/summary") {
        return json([]);
      }
      if (requestUrl.pathname === "/app-profiles" && requestMethod === "GET") {
        return json([]);
      }
      if (
        requestUrl.pathname === "/app-profiles/registration-sessions" &&
        requestMethod === "POST"
      ) {
        return json(registrationSession);
      }
      if (
        requestUrl.pathname ===
        "/app-profiles/registration-sessions/registration-webkit-smoke"
      ) {
        return json({
          status: "registered",
          app_profile: { id: "profile-webkit-smoke" },
          next_session: deviceSession,
        });
      }
      if (
        requestUrl.pathname === "/auth/device-sessions/device-webkit-smoke"
      ) {
        return json(deviceSession);
      }
      if (requestUrl.pathname === "/config") {
        return json({ auth_client_id: "cli_webkit_smoke" });
      }
      if (requestUrl.pathname === "/auth/status") {
        return json({ connected: false, expires_at: null });
      }
      if (requestUrl.pathname === "/auth/authorize-url") {
        return json({
          authorize_url: "https://open.feishu.cn/oauth?state=webkit-smoke",
          state: "webkit-smoke",
          expires_in: 600,
          local_callback: true,
        });
      }
      if (
        requestUrl.pathname === "/auth/cli/status" ||
        requestUrl.pathname === "/system/desktop/status"
      ) {
        return route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ detail: "smoke placeholder" }),
        });
      }
      return route.continue();
    });
  }
  // The runner Keychain can retain credentials between local diagnostic runs.
  // Keep the smoke deterministic by exercising the first-run UI while leaving
  // config and authorize-url requests on the real packaged backend.
  if (!mockApi) {
    await page.route("**/auth/status", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ connected: false, expires_at: null }),
      }),
    );
  }
  await page.goto(url, { waitUntil: "networkidle", timeout: 15000 });
  await publish({
    ok: false,
    completed: false,
    stage: "page_loaded",
    engine: "playwright-webkit",
  });
  if (mockApi) {
    await page.getByTestId("start-two-step-connect").click();
  }
  await page.waitForFunction(
    () => {
      const panel = document.querySelector('[data-testid="device-flow-qr-panel"]');
      const image = document.querySelector('[data-testid="device-flow-qr-image"]');
      const root = document.querySelector('[data-account-connect-root="true"]');
      const rect = image?.getBoundingClientRect();
      return Boolean(
        root?.getAttribute("data-connect-phase") === "authorizing_account" &&
          root?.textContent?.includes("步骤 2 / 2") &&
          panel?.getAttribute("data-qr-state") === "ready" &&
          rect &&
          rect.width > 0 &&
          rect.height > 0 &&
          image?.getAttribute("src")?.startsWith("data:image/png;base64,"),
      );
    },
    undefined,
    { timeout: 15000 },
  );
  payload = await page.evaluate(() => {
    const root = document.querySelector('[data-account-connect-root="true"]');
    const panel = document.querySelector('[data-testid="device-flow-qr-panel"]');
    const image = document.querySelector('[data-testid="device-flow-qr-image"]');
    const rect = image?.getBoundingClientRect();
    return {
      ok: Boolean(root && rect && rect.width > 0 && rect.height > 0),
      engine: "playwright-webkit",
      account_connect_visible: Boolean(root),
      connect_phase: root?.getAttribute("data-connect-phase") ?? null,
      second_step_visible: Boolean(root?.textContent?.includes("步骤 2 / 2")),
      qr_state: panel?.getAttribute("data-qr-state") ?? null,
      qr_visible: Boolean(rect && rect.width > 0 && rect.height > 0),
      qr_is_data_url: Boolean(
        image?.getAttribute("src")?.startsWith("data:image/png;base64,"),
      ),
      viewport: { width: window.innerWidth, height: window.innerHeight },
      completed: true,
      stage: "device_flow_qr_verified",
    };
  });
  await page.screenshot({ path: screenshotPath, fullPage: true });
  payload.screenshot = screenshotPath;
} catch (error) {
  payload = {
    ok: false,
    completed: true,
    stage: "webkit_exception",
    engine: "playwright-webkit",
    error: `${error?.name ?? "Error"}: ${error?.message ?? String(error)}`,
  };
} finally {
  if (browser) {
    await Promise.race([
      browser.close().catch(() => undefined),
      new Promise((resolve) => setTimeout(resolve, 5000)),
    ]);
  }
}

await publish(payload);
process.stdout.write(`${JSON.stringify(payload)}\n`);
process.exit(payload.ok ? 0 : 1);
