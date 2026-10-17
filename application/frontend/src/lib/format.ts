const MONTH_DAY_FORMAT = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" });

// "58 s", "2 min 14 s", "1 min 08 s"
export function formatDuration(totalSeconds: number) {
  const roundedSeconds = Math.round(totalSeconds);
  const minutes = Math.floor(roundedSeconds / 60);
  const seconds = roundedSeconds % 60;
  if (minutes === 0) return `${seconds} s`;
  return `${minutes} min ${String(seconds).padStart(2, "0")} s`;
}

// "0:04", "2:08"
export function formatClock(totalSeconds: number) {
  const roundedSeconds = Math.round(totalSeconds);
  const minutes = Math.floor(roundedSeconds / 60);
  const seconds = roundedSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

// "About 6 min left", "Less than a minute left"
export function formatTimeLeft(secondsLeft: number) {
  const minutesLeft = Math.round(secondsLeft / 60);
  if (minutesLeft < 1) return "Less than a minute left";
  return `About ${minutesLeft} min left`;
}

function isSameDay(firstDate: Date, secondDate: Date) {
  return firstDate.toDateString() === secondDate.toDateString();
}

// "edited today", "edited yesterday", "edited Oct 12"
export function formatEditedDate(isoDate: string) {
  const editedDate = new Date(isoDate);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);

  if (isSameDay(editedDate, today)) return "edited today";
  if (isSameDay(editedDate, yesterday)) return "edited yesterday";
  return `edited ${MONTH_DAY_FORMAT.format(editedDate)}`;
}

// "1 warning", "2 warnings"
export function pluralize(count: number, singularWord: string) {
  if (count === 1) return `1 ${singularWord}`;
  return `${count} ${singularWord}s`;
}

// "Ron" from "RON", "Lower" from "lower"
export function capitalize(text: string) {
  const lowerCaseText = text.toLowerCase();
  return lowerCaseText.charAt(0).toUpperCase() + lowerCaseText.slice(1);
}

// "$0.73", "<$0.01", "—" while a task is still running and its cost isn't known yet
export function formatCost(usd: number | null) {
  if (usd === null) return "—";
  if (usd > 0 && usd < 0.01) return "<$0.01";
  return `$${usd.toFixed(2)}`;
}

// "Opus 5.5" from "claude-opus-5-5"
export function formatModelName(modelId: string) {
  const match = /claude-([a-z]+)-(\d+)-(\d+)/.exec(modelId);
  if (!match) return modelId;
  return `${capitalize(match[1])} ${match[2]}.${match[3]}`;
}

// "Stress marks" from "stress_marks"
export function humanizeName(name: string) {
  const spacedName = name.replace(/[_-]+/g, " ").trim();
  return spacedName.charAt(0).toUpperCase() + spacedName.slice(1);
}
