import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const frontendPort = Number(process.env.LARKSYNC_VITE_DEV_PORT ?? "3666");
const backendTarget = process.env.LARKSYNC_BACKEND_TARGET
  ?? `http://localhost:${process.env.LARKSYNC_BACKEND_PORT ?? "8000"}`;
const backendWsTarget = backendTarget.replace(/^http/, "ws");

export default defineConfig({
  plugins: [react()],
  define: {
    "import.meta.env.VITE_LARKSYNC_BACKEND_PORT": JSON.stringify(
      process.env.LARKSYNC_BACKEND_PORT ?? "8000"
    ),
  },
  test: {
    environment: "node",
    globals: true,
  },
  server: {
    port: frontendPort,
    strictPort: true,
    proxy: {
      "/api": {
        target: backendTarget,
        changeOrigin: true,
        ws: true,
        rewrite: (path) => path.replace(/^\/api/, "")
      },
      "/auth": backendTarget,
      "/config": backendTarget,
      "/drive": backendTarget,
      "/conflicts": backendTarget,
      "/sync": backendTarget,
      "/watcher": backendTarget,
      "/system": backendTarget,
      "/health": backendTarget,
      "/ws": {
        target: backendWsTarget,
        ws: true
      }
    }
  }
});
