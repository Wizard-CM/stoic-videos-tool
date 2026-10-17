import { useEffect, useState, useSyncExternalStore } from "react";
import { listClaudeTasks, type ClaudeTask } from "../../api/client";
import { isTaskActive } from "../../hooks/useClaudeTask";
import { findTaskRoute, getTaskSlotsVersion, subscribeToTaskSlots } from "../../lib/taskSlots";
import { ActiveIcon } from "../icons";

const BUSY_POLL_MS = 3000;
const IDLE_POLL_MS = 15000;
const MAX_SHOWN_TASKS = 3;

// Polls GET /api/claude/tasks: quickly while something runs, slowly otherwise, and right away when a task starts.
function useActiveClaudeTasks() {
  const [activeTasks, setActiveTasks] = useState<ClaudeTask[]>([]);
  const slotsVersion = useSyncExternalStore(subscribeToTaskSlots, getTaskSlotsVersion);

  useEffect(() => {
    let isCancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | undefined;

    const pollTasks = async () => {
      let nextDelay = IDLE_POLL_MS;
      try {
        const runningTasks = (await listClaudeTasks()).filter(isTaskActive);
        if (isCancelled) return;
        setActiveTasks(runningTasks);
        if (runningTasks.length > 0) nextDelay = BUSY_POLL_MS;
      } catch {
        // The widget is only a hint; the screens show real errors.
      }
      if (!isCancelled) timeoutId = setTimeout(pollTasks, nextDelay);
    };

    pollTasks();

    return () => {
      isCancelled = true;
      clearTimeout(timeoutId);
    };
  }, [slotsVersion]);

  return activeTasks;
}

// A small "Claude is working" list in the sidebar, so running tasks stay visible on every screen.
export function ClaudeActivityWidget() {
  const activeTasks = useActiveClaudeTasks();
  if (activeTasks.length === 0) return null;

  const hiddenCount = activeTasks.length - MAX_SHOWN_TASKS;

  return (
    <section aria-label="Claude is working" className="flex flex-col gap-1 rounded-lg bg-accent-tint p-2.5">
      <p className="m-0 flex items-center gap-2 px-1 text-[13px] font-semibold text-accent-dark">
        <ActiveIcon isSpinning size={16} />
        Claude is working
      </p>
      {activeTasks.slice(0, MAX_SHOWN_TASKS).map((task) => {
        const taskRoute = findTaskRoute(task.id);
        const content = (
          <>
            <span className="block text-[13px] font-medium text-ink">{task.title}</span>
            {task.message && <span className="line-clamp-2 block text-[12px] text-muted">{task.message}</span>}
          </>
        );
        if (!taskRoute) {
          return (
            <div key={task.id} className="px-1 py-1">
              {content}
            </div>
          );
        }
        return (
          <a key={task.id} href={taskRoute} className="block min-h-11 rounded-md px-1 py-1 no-underline hover:bg-accent-soft">
            {content}
          </a>
        );
      })}
      {hiddenCount > 0 && <p className="m-0 px-1 text-[12px] text-muted">and {hiddenCount} more</p>}
    </section>
  );
}
