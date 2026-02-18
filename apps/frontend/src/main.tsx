/* ------------------------------------------------------------------ */
/*  React 入口 — QueryClientProvider + ToastProvider                    */
/* ------------------------------------------------------------------ */

import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "./components/ui/toast";
import App from "./App";
import "./index.css";

try {
  const saved = window.localStorage.getItem("larksync-theme");
  document.documentElement.dataset.theme = saved === "dark" ? "dark" : "light";
} catch {
  document.documentElement.dataset.theme = "light";
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <App />
      </ToastProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
