import { useEffect, useState } from "react";
import { ApiError, getClaudeTask, getErrorMessage, type ClaudeTask } from "../api/client";

const POLL_INTERVAL_MS = 2000;

export function isTaskActive(task: ClaudeTask | null) {
  return task !== null && (task.state === "queued" || task.state === "running");
}

// Loads a Claude task, then polls it every 2 s while it is queued or running.
// `isMissing` turns true when the backend no longer knows the task (finished more than an hour ago).
export function useClaudeTask(taskId: string | null) {
  const [task, setTask] = useState<ClaudeTask | null>(null);
  const [taskError, setTaskError] = useState<string | null>(null);
  const [isMissing, setIsMissing] = useState(false);

  useEffect(() => {
    setTask(null);
    setTaskError(null);
    setIsMissing(false);
    if (!taskId) return;

    let isCancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | undefined;

    const pollTask = async () => {
      try {
        const latestTask = await getClaudeTask(taskId);
        if (isCancelled) return;
        setTask(latestTask);
        setTaskError(null);
        if (isTaskActive(latestTask)) timeoutId = setTimeout(pollTask, POLL_INTERVAL_MS);
      } catch (error) {
        if (isCancelled) return;
        if (error instanceof ApiError && error.status === 404) {
          setIsMissing(true);
          return;
        }
        // Keep trying: the backend may be restarting.
        setTaskError(getErrorMessage(error));
        timeoutId = setTimeout(pollTask, POLL_INTERVAL_MS);
      }
    };

    pollTask();

    return () => {
      isCancelled = true;
      clearTimeout(timeoutId);
    };
  }, [taskId]);

  return { task, setTask, taskError, isMissing };
}
