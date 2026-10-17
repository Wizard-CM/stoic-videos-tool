import type { ClaudeTask } from "../../api/client";
import { isTaskActive } from "../../hooks/useClaudeTask";
import type { ClaudeTaskController } from "../../hooks/useClaudeTaskSlot";
import { useNow } from "../../hooks/useNow";
import { formatClock, formatCost } from "../../lib/format";
import { ActiveIcon, DoneIcon, FailedCheckIcon } from "../icons";
import { ErrorMessage } from "../Messages";
import { DANGER_BUTTON, PRIMARY_BUTTON, SECONDARY_BUTTON } from "../styles";
import { ActivityFeed } from "./ActivityFeed";

type ClaudeTaskPanelProps = {
  controller: ClaudeTaskController;
  // Heading until the task has loaded, e.g. "Designing Jade".
  pendingTitle: string;
  // The button that closes a failed or cancelled task, e.g. "Edit and try again".
  dismissLabel?: string;
};

function getElapsedSeconds(task: ClaudeTask, now: number) {
  const startedAt = Date.parse(task.started_at);
  const endedAt = isTaskActive(task) ? now : Date.parse(task.updated_at);
  const elapsedSeconds = (endedAt - startedAt) / 1000;
  return Number.isFinite(elapsedSeconds) ? Math.max(0, elapsedSeconds) : 0;
}

function TaskStateIcon({ task }: { task: ClaudeTask | null }) {
  if (task === null || isTaskActive(task)) return <ActiveIcon isSpinning size={22} />;
  if (task.state === "done") return <DoneIcon />;
  return <FailedCheckIcon />;
}

function TaskStat({ label, value }: { label: string; value: string }) {
  return (
    <span className="flex flex-col items-end">
      <span className="text-[12px] text-muted">{label}</span>
      <span className="text-[15px] font-semibold tabular-nums">{value}</span>
    </span>
  );
}

function getQueuedMessage(task: ClaudeTask | null) {
  if (task === null) return "Starting Claude…";
  if (task.message) return task.message;
  if (task.state === "queued") return "Waiting for Claude to start…";
  return "";
}

function FinishedActions({ controller, dismissLabel }: { controller: ClaudeTaskController; dismissLabel: string }) {
  const { task, isStarting, isFinishing, finishError } = controller;
  if (!task || isTaskActive(task)) return null;

  if (task.state === "done") {
    if (isFinishing) return <p className="m-0 text-sm text-muted">Loading the result…</p>;
    if (!finishError) return null;
    return (
      <div className="flex flex-col gap-2.5">
        <ErrorMessage message={`Claude finished, but the result couldn’t be used: ${finishError}`} />
        <div className="flex flex-wrap gap-2.5">
          <button type="button" className={PRIMARY_BUTTON} onClick={controller.retryFinish}>
            Try again
          </button>
          <button type="button" className={SECONDARY_BUTTON} onClick={controller.dismiss}>
            {dismissLabel}
          </button>
        </div>
      </div>
    );
  }

  const failureText =
    task.state === "cancelled" ? "Cancelled. Nothing was saved." : `Claude couldn’t finish: ${task.error ?? "unknown error."}`;

  return (
    <div className="flex flex-col gap-2.5">
      <p role="alert" className="m-0 rounded-lg bg-danger-soft px-3 py-2.5 text-sm text-danger-ink">
        {failureText}
      </p>
      <div className="flex flex-wrap gap-2.5">
        <button type="button" className={PRIMARY_BUTTON} disabled={isStarting} onClick={controller.retry}>
          {isStarting ? "Starting…" : "Retry"}
        </button>
        <button type="button" className={SECONDARY_BUTTON} onClick={controller.dismiss}>
          {dismissLabel}
        </button>
      </div>
    </div>
  );
}

// Shows a running Claude task: what it is doing now, the team's activity, time and cost, and Cancel.
export function ClaudeTaskPanel({ controller, pendingTitle, dismissLabel = "Close" }: ClaudeTaskPanelProps) {
  const { slot, task, taskError, isCancelling, cancelError, startError } = controller;
  const isActive = task === null || isTaskActive(task);
  const now = useNow(isActive && task !== null);

  if (!slot) return null;

  return (
    <section aria-label="Claude task" className="flex flex-col gap-4 rounded-xl border border-line bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2.5">
          <TaskStateIcon task={task} />
          <div className="flex min-w-0 flex-col gap-0.5">
            <h2 className="m-0 text-[17px] font-semibold">{task?.title || pendingTitle}</h2>
            {isActive && (
              <p aria-live="polite" className="m-0 text-[14.5px] text-ink-soft">
                {getQueuedMessage(task)}
              </p>
            )}
          </div>
        </div>
        {task && (
          <div className="flex gap-5">
            <TaskStat label={isActive ? "Elapsed" : "Took"} value={formatClock(getElapsedSeconds(task, now))} />
            <TaskStat label={isActive ? "Cost so far" : "Cost"} value={formatCost(task.cost_usd)} />
          </div>
        )}
      </div>

      {taskError && <ErrorMessage message={`Can’t reach Claude’s task right now (${taskError}). Retrying…`} />}

      {task && isActive && <ActivityFeed activity={task.activity} startedAt={task.started_at} />}
      {task && !isActive && task.activity.length > 0 && (
        <details>
          <summary className="flex min-h-11 items-center text-sm font-medium text-ink-soft">
            Show what Claude did ({task.activity.length} steps)
          </summary>
          <ActivityFeed activity={task.activity} startedAt={task.started_at} />
        </details>
      )}

      {isActive && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="m-0 max-w-[520px] text-[13px] text-muted">
            This can take several minutes. You can leave this page: Claude keeps working and this panel comes back
            when you return.
          </p>
          <button type="button" className={DANGER_BUTTON} disabled={isCancelling || !task} onClick={controller.cancel}>
            {isCancelling ? "Cancelling…" : "Cancel"}
          </button>
        </div>
      )}

      <FinishedActions controller={controller} dismissLabel={dismissLabel} />
      <ErrorMessage message={cancelError ?? startError} />
    </section>
  );
}
