// Remembers which Claude task belongs to which place in the UI ("slot"), so leaving a screen and coming back
// resumes the task panel. Slots live in localStorage, with an in-memory fallback when storage is blocked.

export type TaskSlot<TInput = unknown> = {
  taskId: string;
  // The request that started the task, used for Retry and to refill the form.
  input: TInput;
  // The screen that started it, so the sidebar can link back.
  route: string;
  // Set once the task failed or was cancelled, until the user retries or closes it.
  stopped?: boolean;
};

const STORAGE_PREFIX = "toonforge.claude-task.";

const memorySlots = new Map<string, string>();
const listeners = new Set<() => void>();
let version = 0;

function readRaw(slotKey: string) {
  try {
    return window.localStorage.getItem(STORAGE_PREFIX + slotKey);
  } catch {
    return memorySlots.get(slotKey) ?? null;
  }
}

function notify() {
  version += 1;
  listeners.forEach((listener) => listener());
}

// Another tab started or finished a task.
window.addEventListener("storage", (event) => {
  if (event.key === null || event.key.startsWith(STORAGE_PREFIX)) notify();
});

export function subscribeToTaskSlots(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

// Changes whenever any slot changes; used as a useSyncExternalStore snapshot.
export function getTaskSlotsVersion() {
  return version;
}

// Returns the stored JSON text, which is a stable snapshot for useSyncExternalStore.
export function readTaskSlotRaw(slotKey: string) {
  return readRaw(slotKey);
}

export function parseTaskSlot<TInput>(rawSlot: string | null): TaskSlot<TInput> | null {
  if (!rawSlot) return null;
  try {
    return JSON.parse(rawSlot) as TaskSlot<TInput>;
  } catch {
    return null;
  }
}

export function readTaskSlot<TInput>(slotKey: string) {
  return parseTaskSlot<TInput>(readRaw(slotKey));
}

export function writeTaskSlot<TInput>(slotKey: string, slot: TaskSlot<TInput>) {
  const rawSlot = JSON.stringify(slot);
  try {
    window.localStorage.setItem(STORAGE_PREFIX + slotKey, rawSlot);
  } catch {
    memorySlots.set(slotKey, rawSlot);
  }
  notify();
}

export function clearTaskSlot(slotKey: string) {
  try {
    window.localStorage.removeItem(STORAGE_PREFIX + slotKey);
  } catch {
    // Storage is blocked; the memory copy below is the only one.
  }
  memorySlots.delete(slotKey);
  notify();
}

function listSlotKeys() {
  try {
    return Object.keys(window.localStorage)
      .filter((storageKey) => storageKey.startsWith(STORAGE_PREFIX))
      .map((storageKey) => storageKey.slice(STORAGE_PREFIX.length));
  } catch {
    return [...memorySlots.keys()];
  }
}

// The screen that started a task, if this browser started it.
export function findTaskRoute(taskId: string) {
  for (const slotKey of listSlotKeys()) {
    const slot = readTaskSlot(slotKey);
    if (slot?.taskId === taskId) return slot.route;
  }
  return null;
}

// Slot keys, one per place a task can be started from.
export const SLOT_KEYS = {
  newCharacter: "character-new",
  reviseCharacter: (characterId: string) => `character-revise:${characterId}`,
  newBackground: "background-new",
  reviseBackground: (backgroundId: string) => `background-revise:${backgroundId}`,
  script: (projectId: string) => `script:${projectId}`,
  castCharacter: (projectId: string, speaker: string) => `cast-character:${projectId}:${speaker}`,
  castBackground: (projectId: string, speaker: string) => `cast-background:${projectId}:${speaker}`,
};
