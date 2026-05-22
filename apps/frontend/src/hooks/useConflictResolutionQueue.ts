import { useCallback, useMemo, useRef, useState } from "react";

import {
  isTaskBusyConflictError,
  summarizeConflictResolutionStates,
  type ConflictResolutionStatus,
} from "../lib/conflictResolution";
import type { ConflictResolutionAction, Tone } from "../types";

const CONFLICT_BUSY_RETRY_DELAY_MS = 5_000;
const CONFLICT_BUSY_RETRY_LIMIT = 24;

type ConflictResolutionQueueItem = {
  id: string;
  action: ConflictResolutionAction;
  successMessage: string;
};

type ResolveConflictAsync = (payload: { id: string; action: ConflictResolutionAction }) => Promise<unknown>;
type ToastFn = (message: string, tone?: Tone) => void;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    globalThis.setTimeout(resolve, ms);
  });
}

export function useConflictResolutionQueue({
  resolveConflictAsync,
  toast,
}: {
  resolveConflictAsync: ResolveConflictAsync;
  toast: ToastFn;
}) {
  const queueRef = useRef<ConflictResolutionQueueItem[]>([]);
  const processingRef = useRef(false);
  const activeConflictResolutionIdRef = useRef<string | null>(null);
  const [conflictResolutionStates, setConflictResolutionStates] = useState<
    Record<string, ConflictResolutionStatus>
  >({});

  const processConflictResolutionQueue = useCallback(async () => {
    if (processingRef.current) {
      return;
    }
    processingRef.current = true;
    try {
      while (queueRef.current.length > 0) {
        const [next, ...rest] = queueRef.current;
        queueRef.current = rest;
        activeConflictResolutionIdRef.current = next.id;
        const resolveWithRetry = async (attempt: number): Promise<void> => {
          setConflictResolutionStates((current) => ({
            ...current,
            [next.id]: {
              action: next.action,
              state: attempt === 0 ? "running" : "waiting",
              message:
                attempt === 0
                  ? "正在提交处理请求…"
                  : `目标任务仍在同步，${Math.ceil(CONFLICT_BUSY_RETRY_DELAY_MS / 1000)} 秒后自动重试（第 ${attempt + 1} 次）`,
              attempt,
            },
          }));
          if (attempt > 0) {
            await sleep(CONFLICT_BUSY_RETRY_DELAY_MS);
            setConflictResolutionStates((current) => ({
              ...current,
              [next.id]: {
                action: next.action,
                state: "running",
                message: `正在重试（第 ${attempt + 1} 次）…`,
                attempt,
              },
            }));
          }
          try {
            await resolveConflictAsync({ id: next.id, action: next.action });
            setConflictResolutionStates((current) => ({
              ...current,
              [next.id]: {
                action: next.action,
                state: "success",
                message: next.successMessage,
                attempt,
              },
            }));
            toast(next.successMessage, "success");
          } catch (error) {
            const message = error instanceof Error ? error.message : "冲突处理失败";
            if (isTaskBusyConflictError(message) && attempt < CONFLICT_BUSY_RETRY_LIMIT) {
              await resolveWithRetry(attempt + 1);
              return;
            }
            setConflictResolutionStates((current) => ({
              ...current,
              [next.id]: {
                action: next.action,
                state: "error",
                message,
                attempt,
              },
            }));
            toast(message, "danger");
          }
        };
        await resolveWithRetry(0);
      }
    } finally {
      activeConflictResolutionIdRef.current = null;
      processingRef.current = false;
      if (queueRef.current.length > 0) {
        void processConflictResolutionQueue();
      }
    }
  }, [resolveConflictAsync, toast]);

  const handleResolveConflict = useCallback((
    id: string,
    action: ConflictResolutionAction,
    successMessage: string,
  ) => {
    setConflictResolutionStates((current) => {
      if (current[id] && current[id].state !== "error") return current;
      return {
        ...current,
        [id]: { action, state: "queued", message: "已加入处理队列" },
      };
    });
    if (
      queueRef.current.some((item) => item.id === id) ||
      activeConflictResolutionIdRef.current === id
    ) {
      return;
    }
    queueRef.current = [...queueRef.current, { id, action, successMessage }];
    void processConflictResolutionQueue();
  }, [processConflictResolutionQueue]);

  const queueSummary = useMemo(
    () => summarizeConflictResolutionStates(conflictResolutionStates),
    [conflictResolutionStates],
  );

  return {
    conflictResolutionStates,
    queueSummary,
    handleResolveConflict,
  };
}
