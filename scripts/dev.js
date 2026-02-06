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
const isWindows = process.platform === "win32";
const npmCommand = isWindows ? "npm.cmd" : "npm";
const pythonCommand = isWindows ? "python" : "python3";

const quoteArg = (value) => {
  const text = String(value);
  if (/[\s"]/u.test(text)) {
    return `"${text.replace(/"/g, '\\"')}"`;
  }
  return text;
};

const buildCommand = (command, args) => {
  if (!args || args.length === 0) {
    return command;
  }
  return [command, ...args.map(quoteArg)].join(" ");
};

const spawnProcess = (name, command, args, options) => {
  const spawnOptions = {
    ...options,
    windowsHide: true,
    env: process.env,
  };
  const child = isWindows
    ? spawn(buildCommand(command, args), {
        ...spawnOptions,
        shell: true,
      })
    : spawn(command, args, {
        ...spawnOptions,
        shell: false,
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
    if (isWindows) {
      if (child.pid) {
        spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], {
          shell: true,
          windowsHide: true,
          stdio: "ignore",
        });
      }
    } else {
      child.kill(signal);
    }
  }
  setTimeout(() => {
    logStream.end();
    process.exit(process.exitCode ?? 0);
  }, 500);
};

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("exit", () => logStream.end());
process.on("uncaughtException", (error) => {
  writeLines("system:err", error?.stack ?? String(error));
  shutdown("SIGTERM");
});
process.on("unhandledRejection", (reason) => {
  writeLines("system:err", reason?.stack ?? String(reason));
  shutdown("SIGTERM");
});

spawnProcess("frontend", npmCommand, ["run", "dev", "--prefix", "apps/frontend"], {
  cwd: root,
});

spawnProcess("backend", pythonCommand, ["-m", "uvicorn", "src.main:app", "--reload", "--port", "8000"], {
  cwd: path.join(root, "apps", "backend"),
});
