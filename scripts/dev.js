const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const root = process.cwd();
const logDir = path.join(root, "data", "logs");
fs.mkdirSync(logDir, { recursive: true });

const logPath = path.join(logDir, "dev-console.log");
const logStream = fs.createWriteStream(logPath, { flags: "a" });

const timestamp = () => new Date().toISOString().replace("T", " ").replace("Z", "");

const writeLines = (source, chunk) => {
  const text = chunk.toString();
  const normalized = text.replace(/\r\n/g, "\n");
  const lines = normalized.split("\n");
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    if (line.length === 0 && i === lines.length - 1) {
      continue;
    }
    logStream.write(`[${timestamp()}] [${source}] ${line}\n`);
  }
};

logStream.write(`[${timestamp()}] [system] dev session start\n`);
logStream.write(`[${timestamp()}] [system] log file: ${logPath}\n`);

const children = [];
let shuttingDown = false;

const spawnProcess = (name, command, args, options) => {
  const child = spawn(command, args, {
    ...options,
    shell: true,
    env: process.env,
  });
  children.push(child);

  child.stdout.on("data", (data) => {
    process.stdout.write(data);
    writeLines(name, data);
  });

  child.stderr.on("data", (data) => {
    process.stderr.write(data);
    writeLines(`${name}:err`, data);
  });

  child.on("exit", (code, signal) => {
    writeLines("system", `${name} exited code=${code ?? ""} signal=${signal ?? ""}`);
    if (!shuttingDown) {
      process.exitCode = code ?? 1;
      shutdown("SIGTERM");
    }
  });

  return child;
};

const shutdown = (signal) => {
  if (shuttingDown) {
    return;
  }
  shuttingDown = true;
  writeLines("system", `shutting down signal=${signal ?? ""}`);
  for (const child of children) {
    if (child.killed) {
      continue;
    }
    child.kill(signal);
  }
  setTimeout(() => {
    logStream.end();
    process.exit(process.exitCode ?? 0);
  }, 500);
};

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("exit", () => logStream.end());

spawnProcess("frontend", "npm", ["run", "dev", "--prefix", "apps/frontend"], {
  cwd: root,
});

spawnProcess("backend", "python", ["-m", "uvicorn", "src.main:app", "--reload", "--port", "8000"], {
  cwd: path.join(root, "apps", "backend"),
});
