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
  danger: "bg-rose-600 hover:bg-rose-500 text-white",
  warning: "bg-amber-600 hover:bg-amber-500 text-white",
  neutral: "bg-blue-600 hover:bg-blue-500 text-white",
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
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/50 px-4">
      <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-zinc-900 p-6 shadow-2xl">
        <h3 className="text-lg font-semibold text-zinc-100">{dialog.title}</h3>
        {dialog.description ? (
          <p className="mt-2 text-sm text-zinc-400">{dialog.description}</p>
        ) : null}
        <div className="mt-6 flex justify-end gap-3">
          <button
            className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 transition hover:bg-zinc-800"
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
