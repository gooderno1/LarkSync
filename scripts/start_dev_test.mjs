import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import net from "node:net";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const defaultDataDir = resolve(repoRoot, "data", "dev-test");

const dataDir = process.env.LARKSYNC_DATA_DIR ?? defaultDataDir;
mkdirSync(dataDir, { recursive: true });
const backendClientHost = process.env.LARKSYNC_BACKEND_CLIENT_HOST ?? "127.0.0.1";
const backendPort = process.env.LARKSYNC_BACKEND_PORT ?? await selectBackendPort({
  host: backendClientHost,
  preferredPort: 18000,
  expectedDataDir: dataDir,
});

const env = {
  ...process.env,
  LARKSYNC_BACKEND_BIND_HOST: process.env.LARKSYNC_BACKEND_BIND_HOST ?? "127.0.0.1",
  LARKSYNC_BACKEND_CLIENT_HOST: backendClientHost,
  LARKSYNC_BACKEND_PORT: backendPort,
  LARKSYNC_VITE_DEV_PORT: process.env.LARKSYNC_VITE_DEV_PORT ?? "13666",
  LARKSYNC_LOCK_PORT: process.env.LARKSYNC_LOCK_PORT ?? "48911",
  LARKSYNC_DATA_DIR: dataDir,
  LARKSYNC_TOKEN_STORE: process.env.LARKSYNC_TOKEN_STORE ?? "file",
  LARKSYNC_TOKEN_FILE: process.env.LARKSYNC_TOKEN_FILE ?? join(dataDir, "token_store.json"),
};

console.log("LarkSync isolated dev test");
console.log(`  frontend: http://localhost:${env.LARKSYNC_VITE_DEV_PORT}`);
console.log(`  backend:  http://${env.LARKSYNC_BACKEND_CLIENT_HOST}:${env.LARKSYNC_BACKEND_PORT}`);
console.log(`  data:     ${env.LARKSYNC_DATA_DIR}`);

const python = process.platform === "win32" ? "python" : "python3";
const child = spawn(python, ["apps/tray/tray_app.py", "--dev"], {
  env,
  stdio: "inherit",
  shell: false,
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 0);
});

async function selectBackendPort({ host, preferredPort, expectedDataDir }) {
  for (let port = preferredPort; port < preferredPort + 20; port += 1) {
    if (!(await isPortOpen(host, port))) {
      return String(port);
    }

    const status = await readDesktopStatus(host, port);
    if (status && samePath(status.runtime?.data_dir, expectedDataDir)) {
      return String(port);
    }

    console.warn(`  后端端口 ${port} 已被占用或数据目录不匹配，尝试 ${port + 1}`);
  }
  throw new Error(`No free backend port found from ${preferredPort} to ${preferredPort + 19}`);
}

function isPortOpen(host, port) {
  return new Promise((resolvePort) => {
    const socket = net.createConnection({ host, port });
    socket.setTimeout(500);
    socket.once("connect", () => {
      socket.destroy();
      resolvePort(true);
    });
    socket.once("timeout", () => {
      socket.destroy();
      resolvePort(false);
    });
    socket.once("error", () => resolvePort(false));
  });
}

async function readDesktopStatus(host, port) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 800);
  try {
    const response = await fetch(`http://${host}:${port}/system/desktop/status`, {
      signal: controller.signal,
    });
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

function samePath(left, right) {
  if (typeof left !== "string" || typeof right !== "string") {
    return false;
  }
  return normalizePath(left) === normalizePath(right);
}

function normalizePath(value) {
  const normalized = resolve(value).replaceAll("\\", "/");
  return process.platform === "win32" ? normalized.toLowerCase() : normalized;
}
