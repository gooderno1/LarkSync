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
  neutral: "border-[#c9d8ec] bg-white text-[#334762]",
  info: "border-[#3370ff]/25 bg-[#eef5ff] text-[#1d4ed8]",
  success: "border-[#10b981]/25 bg-[#ecfdf5] text-[#047857]",
  warning: "border-[#f59e0b]/30 bg-[#fffbeb] text-[#b45309]",
  danger: "border-[#f43f5e]/30 bg-[#fff1f2] text-[#be123c]",
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
              "pointer-events-auto animate-slide-up rounded-lg border px-4 py-3 text-sm shadow-[0_18px_48px_rgba(16,32,51,0.14)] backdrop-blur-sm",
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
