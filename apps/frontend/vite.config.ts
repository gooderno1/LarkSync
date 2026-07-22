import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const frontendPort = Number(process.env.LARKSYNC_VITE_DEV_PORT ?? "3666");
const backendTarget = process.env.LARKSYNC_BACKEND_TARGET
  ?? `http://localhost:${process.env.LARKSYNC_BACKEND_PORT ?? "18765"}`;
const backendWsTarget = backendTarget.replace(/^http/, "ws");

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          const normalized = id.replaceAll("\\", "/");
          if (normalized.includes("/src/pages/")) return "desktop-pages";
          if (normalized.includes("/node_modules/react/") || normalized.includes("/node_modules/react-dom/")) {
            return "react-vendor";
          }
          if (normalized.includes("/node_modules/@tanstack/")) return "query-vendor";
          if (normalized.includes("/node_modules/")) return "vendor";
          return undefined;
        },
      },
    },
  },
  define: {
    "import.meta.env.VITE_LARKSYNC_BACKEND_PORT": JSON.stringify(
      process.env.LARKSYNC_BACKEND_PORT ?? "18765"
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
