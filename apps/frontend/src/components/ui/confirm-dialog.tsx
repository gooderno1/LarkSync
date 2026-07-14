/* ------------------------------------------------------------------ */
/*  确认对话框组件 (AlertDialog 替代)                                    */
/* ------------------------------------------------------------------ */

import { useCallback, useState } from "react";

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
  globalSetDialog = setDialog;

  const handleResolve = useCallback(
    (value: boolean) => {
      dialog?.resolve(value);
      setDialog(null);
    },
    [dialog]
  );

  if (!dialog) return null;

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-[#102033]/35 px-4 backdrop-blur-sm">
      <div data-confirm-dialog="true" aria-labelledby="confirm-dialog-title" aria-modal="true" className="w-full max-w-md rounded-lg border border-[#d7e4f5] bg-white p-6 shadow-[0_28px_90px_rgba(16,32,51,0.22)]" role="alertdialog">
        <h3 id="confirm-dialog-title" className="text-lg font-semibold text-[#102033]">{dialog.title}</h3>
        {dialog.description ? (
          <p className="mt-2 whitespace-pre-line text-sm leading-6 text-[#58708d]">{dialog.description}</p>
        ) : null}
        <div className="mt-6 flex justify-end gap-3">
          <button
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
