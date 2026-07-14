import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { confirm } from "../ui/confirm-dialog";
import type { SyncTask } from "../../types";
import { TaskSettingsPanel } from "./TaskSettingsPanel";

type TaskSettingsModalProps = {
  task: SyncTask;
  processed: number;
  total: number;
  onClose: () => void;
  onDelete: () => void | Promise<void>;
  onSave: (patch: Record<string, unknown>) => Promise<void>;
};

export function TaskSettingsDialog({
  task,
  processed,
  total,
  onClose,
  onDelete,
  onSave,
}: TaskSettingsModalProps) {
  const [dirty, setDirty] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeConfirmationPendingRef = useRef(false);

  const requestClose = useCallback(async () => {
    if (closeConfirmationPendingRef.current) return;
    if (dirty) {
      closeConfirmationPendingRef.current = true;
      try {
        const shouldDiscard = await confirm({
          title: "放弃未保存的更改？",
          description: "当前任务设置尚未保存。关闭弹窗后，本次修改将全部丢失。",
          confirmLabel: "放弃更改",
          tone: "warning",
        });
        if (!shouldDiscard) return;
      } finally {
        closeConfirmationPendingRef.current = false;
      }
    }
    onClose();
  }, [dirty, onClose]);
  const requestCloseRef = useRef(requestClose);

  useEffect(() => {
    requestCloseRef.current = requestClose;
  }, [requestClose]);

  useEffect(() => {
    const previousActiveElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const focusTimer = window.setTimeout(() => {
      dialogRef.current?.querySelector<HTMLElement>("[data-task-settings-close]")?.focus();
    }, 0);

    const handleKeyDown = (event: KeyboardEvent) => {
      if (document.querySelector('[data-confirm-dialog="true"]')) return;
      if (event.key === "Escape") {
        event.preventDefault();
        void requestCloseRef.current();
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), select:not([disabled]), input:not([disabled]), summary, [tabindex]:not([tabindex="-1"])',
        ),
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      window.clearTimeout(focusTimer);
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      previousActiveElement?.focus();
    };
  }, []);

  return (
    <div data-task-settings-modal="true" className="fixed inset-0 z-50 flex items-center justify-center bg-[#102033]/35 p-4 backdrop-blur-sm">
      <div
        ref={dialogRef}
        aria-labelledby="task-settings-dialog-title"
        aria-modal="true"
        className="max-h-[88vh] w-[1040px] max-w-[calc(100vw-32px)] overflow-y-auto rounded-xl"
        role="dialog"
      >
        <TaskSettingsPanel
          task={task}
          processed={processed}
          total={total}
          onClose={() => void requestClose()}
          onDelete={onDelete}
          onDirtyChange={setDirty}
          onSave={onSave}
        />
      </div>
    </div>
  );
}

export function TaskSettingsModal(props: TaskSettingsModalProps) {
  return createPortal(<TaskSettingsDialog {...props} />, document.body);
}
