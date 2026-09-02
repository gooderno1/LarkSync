/* ------------------------------------------------------------------ */
/*  确认对话框组件 (AlertDialog 替代)                                    */
/* ------------------------------------------------------------------ */

import { useCallback, useEffect, useRef, useState } from "react";

type ConfirmOptions = {
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "danger" | "warning" | "neutral";
};

type ConfirmDialogState = ConfirmOptions & {
  resolve: (value: boolean) => void;
};

let globalSetDialog: ((state: ConfirmDialogState | null) => void) | null = null;

export function confirm(options: ConfirmOptions): Promise<boolean> {
  return new Promise<boolean>((resolve) => {
    globalSetDialog?.({ ...options, resolve });
  });
}

const toneButton: Record<string, string> = {
  danger: "bg-[#e11d48] text-white hover:bg-[#be123c]",
  warning: "bg-[#f59e0b] text-white hover:bg-[#d97706]",
  neutral: "bg-[#3370ff] text-white hover:bg-[#2456d6]",
};

export function ConfirmDialogProvider() {
  const [dialog, setDialog] = useState<ConfirmDialogState | null>(null);
  const cancelButtonRef = useRef<HTMLButtonElement>(null);
  globalSetDialog = setDialog;

  const handleResolve = useCallback(
    (value: boolean) => {
      dialog?.resolve(value);
      setDialog(null);
    },
    [dialog]
  );

  useEffect(() => {
    if (!dialog) return;
    cancelButtonRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") handleResolve(false);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [dialog, handleResolve]);

  if (!dialog) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#102033]/30 px-4 backdrop-blur-sm" onMouseDown={() => handleResolve(false)}>
      <div data-confirm-dialog="true" aria-labelledby="confirm-dialog-title" aria-modal="true" className="w-full max-w-md rounded-2xl border border-[#d7e4f5] bg-white p-6 shadow-[0_28px_90px_rgba(16,32,51,0.22)]" role="alertdialog" onMouseDown={(event) => event.stopPropagation()}>
        <div className="flex items-start gap-3">
          <span aria-hidden="true" className={`mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-full ${dialog.tone === "danger" ? "bg-[#fff1f2] text-[#e11d48]" : "bg-[#eef5ff] text-[#3370ff]"}`}>
            <svg viewBox="0 0 20 20" className="h-5 w-5"><path d="M10 3.2 17 16H3L10 3.2Z" fill="none" stroke="currentColor" strokeLinejoin="round" strokeWidth="1.6"/><path d="M10 7v4.5M10 14.2v.1" stroke="currentColor" strokeLinecap="round" strokeWidth="1.6"/></svg>
          </span>
          <div className="min-w-0">
            <h3 id="confirm-dialog-title" className="text-lg font-semibold text-[#102033]">{dialog.title}</h3>
        {dialog.description ? (
          <p className="mt-2 whitespace-pre-line text-sm leading-6 text-[#58708d]">{dialog.description}</p>
        ) : null}
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button
            ref={cancelButtonRef}
            className="rounded-lg border border-[#c9d8eb] bg-white px-4 py-2 text-sm font-medium text-[#52677f] transition hover:border-[#3370ff]/40 hover:bg-[#f2f7ff] hover:text-[#2456d6]"
            onClick={() => handleResolve(false)}
            type="button"
          >
            {dialog.cancelLabel || "取消"}
          </button>
          <button
            className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
              toneButton[dialog.tone || "neutral"]
            }`}
            onClick={() => handleResolve(true)}
            type="button"
          >
            {dialog.confirmLabel || "确认"}
          </button>
        </div>
      </div>
    </div>
  );
}
