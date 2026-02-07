/* ------------------------------------------------------------------ */
/*  轻量 Toast 通知系统                                                 */
/* ------------------------------------------------------------------ */

import { createContext, useCallback, useContext, useState } from "react";
import type { ReactNode } from "react";
import { cn } from "../../lib/utils";
import type { Tone } from "../../types";

type ToastItem = {
  id: number;
  message: string;
  tone: Tone;
};

type ToastContextValue = {
  toast: (message: string, tone?: Tone) => void;
};

const ToastContext = createContext<ToastContextValue>({
  toast: () => {},
});

export function useToast() {
  return useContext(ToastContext);
}

let nextId = 0;

const toneStyles: Record<Tone, string> = {
  neutral: "border-zinc-700 bg-zinc-900 text-zinc-100",
  info: "border-blue-500/40 bg-blue-950 text-blue-100",
  success: "border-emerald-500/40 bg-emerald-950 text-emerald-100",
  warning: "border-amber-500/40 bg-amber-950 text-amber-100",
  danger: "border-rose-500/40 bg-rose-950 text-rose-100",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const toast = useCallback((message: string, tone: Tone = "neutral") => {
    const id = ++nextId;
    setItems((prev) => [...prev, { id, message, tone }]);
    setTimeout(() => {
      setItems((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {/* Toast 容器 - 右下角 */}
      <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2 pointer-events-none">
        {items.map((item) => (
          <div
            key={item.id}
            className={cn(
              "pointer-events-auto animate-slide-up rounded-xl border px-4 py-3 text-sm shadow-lg backdrop-blur-sm",
              toneStyles[item.tone]
            )}
          >
            {item.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
