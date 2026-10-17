import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { ApiError, cancelClaudeTask, getErrorMessage, type ClaudeTask, type TaskStarted } from "../api/client";
import {
  clearTaskSlot,
  parseTaskSlot,
  readTaskSlotRaw,
  subscribeToTaskSlots,
  writeTaskSlot,
} from "../lib/taskSlots";
import { refreshClaudeStatus } from "./useClaudeStatus";
import { useClaudeTask } from "./useClaudeTask";

type ClaudeTaskSlotConfig<TInput> = {
  slotKey: string;
  start: (input: TInput) => Promise<TaskStarted>;
  // Runs once when the task is done (also when it finished while the user was away).
  // When given, the slot is cleared after it succeeds; otherwise the caller calls dismiss().
  onDone?: (task: ClaudeTask) => Promise<void> | void;
};

export function useTaskSlot<TInput>(slotKey: string) {
  const rawSlot = useSyncExternalStore(subscribeToTaskSlots, () => readTaskSlotRaw(slotKey));
  return useMemo(() => parseTaskSlot<TInput>(rawSlot), [rawSlot]);
}

// Starts a Claude task for one place in the UI and follows it until it is handled.
// The task id is stored per slot, so the panel comes back after navigating away.
export function useClaudeTaskSlot<TInput>({ slotKey, start, onDone }: ClaudeTaskSlotConfig<TInput>) {
  const slot = useTaskSlot<TInput>(slotKey);
  const { task, setTask, taskError, isMissing } = useClaudeTask(slot?.taskId ?? null);
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [isFinishing, setIsFinishing] = useState(false);
  const [finishError, setFinishError] = useState<string | null>(null);
  const handledTaskIdRef = useRef<string | null>(null);
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  const startTask = async (input: TInput) => {
    setIsStarting(true);
    setStartError(null);
    setCancelError(null);
    setFinishError(null);
    try {
      const { task_id } = await start(input);
      writeTaskSlot(slotKey, { taskId: task_id, input, route: window.location.hash });
    } catch (error) {
      setStartError(getErrorMessage(error));
      // 409 means Claude isn't ready; refresh the banner so it explains why.
      if (error instanceof ApiError && error.status === 409) refreshClaudeStatus();
    } finally {
      setIsStarting(false);
    }
  };

  const finishTask = async (doneTask: ClaudeTask) => {
    const handleDone = onDoneRef.current;
    if (!handleDone) return;
    setIsFinishing(true);
    setFinishError(null);
    try {
      await handleDone(doneTask);
      clearTaskSlot(slotKey);
    } catch (error) {
      setFinishError(getErrorMessage(error));
    } finally {
      setIsFinishing(false);
    }
  };

  useEffect(() => {
    if (task?.state !== "done" || handledTaskIdRef.current === task.id) return;
    handledTaskIdRef.current = task.id;
    finishTask(task);
  }, [task]);

  // Remember that the task stopped, so other parts of the screen stop saying "Claude is working".
  useEffect(() => {
    if (!slot || slot.stopped || !task || task.id !== slot.taskId) return;
    if (task.state === "failed" || task.state === "cancelled") writeTaskSlot(slotKey, { ...slot, stopped: true });
  }, [task, slot, slotKey]);

  // A stored task the backend has forgotten can't be resumed.
  useEffect(() => {
    if (isMissing) clearTaskSlot(slotKey);
  }, [isMissing, slotKey]);

  const cancel = async () => {
    if (!slot) return;
    setIsCancelling(true);
    setCancelError(null);
    try {
      setTask(await cancelClaudeTask(slot.taskId));
    } catch (error) {
      setCancelError(getErrorMessage(error));
    } finally {
      setIsCancelling(false);
    }
  };

  const retry = () => {
    if (slot) startTask(slot.input);
  };

  const retryFinish = () => {
    if (task) finishTask(task);
  };

  const dismiss = () => {
    setFinishError(null);
    clearTaskSlot(slotKey);
  };

  return {
    slot,
    task,
    taskError,
    isStarting,
    startError,
    isCancelling,
    cancelError,
    isFinishing,
    finishError,
    startTask,
    cancel,
    retry,
    retryFinish,
    dismiss,
  };
}

// What the task panel needs; startTask stays with the form that owns the input type.
export type ClaudeTaskController = Omit<ReturnType<typeof useClaudeTaskSlot>, "startTask">;
