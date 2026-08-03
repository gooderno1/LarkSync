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
const screenshotPath = resultPath.replace(/\.json$/u, ".png");
let browser;
let payload;

try {
  browser = await webkit.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1080, height: 720 } });
  // The runner Keychain can retain credentials between local diagnostic runs.
  // Keep the smoke deterministic by exercising the first-run UI while leaving
  // config and authorize-url requests on the real packaged backend.
  await page.route("**/auth/status", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ connected: false, expires_at: null }),
    }),
  );
  await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
  await page.waitForFunction(
    () => {
      const panel = document.querySelector('[data-testid="oauth-qr-panel"]');
      const image = document.querySelector('[data-testid="oauth-qr-image"]');
      const rect = image?.getBoundingClientRect();
      return Boolean(
        document.querySelector('[data-onboarding-root="true"]') &&
          panel?.getAttribute("data-qr-state") === "ready" &&
          rect &&
          rect.width > 0 &&
          rect.height > 0 &&
          image?.getAttribute("src")?.startsWith("data:image/png;base64,"),
      );
    },
    undefined,
    { timeout: 30000 },
  );
  payload = await page.evaluate(() => {
    const root = document.querySelector('[data-onboarding-root="true"]');
    const panel = document.querySelector('[data-testid="oauth-qr-panel"]');
    const image = document.querySelector('[data-testid="oauth-qr-image"]');
    const rect = image?.getBoundingClientRect();
    return {
      ok: Boolean(root && rect && rect.width > 0 && rect.height > 0),
      engine: "playwright-webkit",
      onboarding_visible: Boolean(root),
      qr_state: panel?.getAttribute("data-qr-state") ?? null,
      qr_visible: Boolean(rect && rect.width > 0 && rect.height > 0),
      qr_is_data_url: Boolean(
        image?.getAttribute("src")?.startsWith("data:image/png;base64,"),
      ),
      viewport: { width: window.innerWidth, height: window.innerHeight },
    };
  });
  await page.screenshot({ path: screenshotPath, fullPage: true });
  payload.screenshot = screenshotPath;
} catch (error) {
  payload = {
    ok: false,
    engine: "playwright-webkit",
    error: `${error?.name ?? "Error"}: ${error?.message ?? String(error)}`,
  };
} finally {
  await browser?.close();
}

await fs.mkdir(path.dirname(resultPath), { recursive: true });
const temporaryPath = `${resultPath}.tmp`;
await fs.writeFile(temporaryPath, JSON.stringify(payload), "utf8");
await fs.rename(temporaryPath, resultPath);
process.stdout.write(`${JSON.stringify(payload)}\n`);
process.exitCode = payload.ok ? 0 : 1;
