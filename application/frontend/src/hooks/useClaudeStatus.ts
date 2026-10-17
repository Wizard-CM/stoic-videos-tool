import { useEffect, useSyncExternalStore } from "react";
import { getClaudeStatus, getErrorMessage, type ClaudeStatus } from "../api/client";

// One shared copy of GET /api/claude/status for the whole app.

type StatusSnapshot = {
  status: ClaudeStatus | null;
  statusError: string | null;
};

let snapshot: StatusSnapshot = { status: null, statusError: null };
let pendingRefresh: Promise<void> | null = null;
const listeners = new Set<() => void>();

function setSnapshot(nextSnapshot: StatusSnapshot) {
  snapshot = nextSnapshot;
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function refreshClaudeStatus() {
  if (pendingRefresh) return pendingRefresh;
  pendingRefresh = getClaudeStatus()
    .then((status) => setSnapshot({ status, statusError: null }))
    .catch((error) => setSnapshot({ ...snapshot, statusError: getErrorMessage(error) }))
    .finally(() => {
      pendingRefresh = null;
    });
  return pendingRefresh;
}

const NOT_READY_FALLBACK = "Claude isn’t ready on this PC yet.";

export function useClaudeStatus() {
  const { status, statusError } = useSyncExternalStore(subscribe, () => snapshot);

  useEffect(() => {
    if (!snapshot.status) refreshClaudeStatus();
  }, []);

  // Unknown counts as ready: starting a task while not ready returns a clear 409 anyway.
  const isReady = status?.ready !== false;
  const notReadyMessage = isReady ? null : status?.message || NOT_READY_FALLBACK;

  return { status, statusError, isReady, notReadyMessage };
}
