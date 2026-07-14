/* ------------------------------------------------------------------ */
/*  WebSocket 实时日志流 Hook                                           */
/*  后端 ws://host/ws/events 路由通过同源或 Vite proxy 暴露                 */
/* ------------------------------------------------------------------ */

import { useCallback, useEffect, useRef, useState } from "react";
import type { SyncLogEntry } from "../types";

const MAX_ENTRIES = 500;

export function useWebSocketLog(enabled = true) {
  const [entries, setEntries] = useState<SyncLogEntry[]>([]);
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected">(
    "disconnected"
  );
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!enabled) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const base = `${protocol}//${window.location.host}`;
    const url = `${base}/ws/events`;

    setStatus("connecting");

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => setStatus("connected");

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as SyncLogEntry;
          setEntries((prev) => [data, ...prev].slice(0, MAX_ENTRIES));
        } catch {
          // ignore malformed messages
        }
      };

      ws.onerror = () => {
        // will trigger onclose
      };

      ws.onclose = () => {
        setStatus("disconnected");
        wsRef.current = null;
        // exponential backoff reconnect
        reconnectTimer.current = setTimeout(connect, 5000);
      };
    } catch {
      setStatus("disconnected");
      reconnectTimer.current = setTimeout(connect, 5000);
    }
  }, [enabled]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const clearEntries = useCallback(() => setEntries([]), []);

  return { entries, status, clearEntries };
}
