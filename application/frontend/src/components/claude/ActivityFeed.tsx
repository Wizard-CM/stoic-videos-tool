import { useEffect, useRef } from "react";
import type { ClaudeActivity } from "../../api/client";
import { formatClock } from "../../lib/format";

// Within this many px of the bottom, new entries keep the feed scrolled down.
const STICKY_BOTTOM_PX = 40;

type WorkerTone = "lead" | "sonnet" | "haiku" | "other";

const WORKER_TONE_CLASSES: Record<WorkerTone, string> = {
  lead: "bg-accent-soft text-accent-dark",
  sonnet: "bg-chip text-chip-ink",
  haiku: "bg-success-soft text-success",
  other: "bg-chip text-chip-ink",
};

const KIND_TEXT_CLASSES: Record<string, string> = {
  delegate: "text-accent-dark",
  tool: "text-muted",
  error: "text-danger",
};

export function getWorkerLabel(who: string): { label: string; tone: WorkerTone } {
  const name = who.toLowerCase();
  if (name === "lead" || name.includes("opus")) return { label: "Opus · lead", tone: "lead" };
  if (name.includes("sonnet")) return { label: "Sonnet worker", tone: "sonnet" };
  if (name.includes("haiku")) return { label: "Haiku worker", tone: "haiku" };
  return { label: who, tone: "other" };
}

export function WorkerBadge({ who }: { who: string }) {
  const worker = getWorkerLabel(who);
  return (
    <span
      className={`inline-flex flex-none items-center rounded-full px-2 py-px text-[12px] font-medium whitespace-nowrap ${WORKER_TONE_CLASSES[worker.tone]}`}
    >
      {worker.label}
    </span>
  );
}

// "1:10" after the task started.
function getEntryTime(entryTime: string, startedAt: string) {
  const secondsIn = (Date.parse(entryTime) - Date.parse(startedAt)) / 1000;
  if (!Number.isFinite(secondsIn) || secondsIn < 0) return "";
  return formatClock(secondsIn);
}

type ActivityFeedProps = {
  activity: ClaudeActivity[];
  startedAt: string;
};

// Claude's activity, oldest first, kept scrolled to the newest entry unless the user scrolled up.
export function ActivityFeed({ activity, startedAt }: ActivityFeedProps) {
  const feedRef = useRef<HTMLOListElement>(null);
  const isNearBottomRef = useRef(true);
  const lastEntry = activity[activity.length - 1];

  useEffect(() => {
    const feed = feedRef.current;
    if (feed && isNearBottomRef.current) feed.scrollTop = feed.scrollHeight;
  }, [lastEntry?.t, lastEntry?.text, activity.length]);

  const handleScroll = () => {
    const feed = feedRef.current;
    if (!feed) return;
    isNearBottomRef.current = feed.scrollHeight - feed.scrollTop - feed.clientHeight < STICKY_BOTTOM_PX;
  };

  if (activity.length === 0) {
    return <p className="m-0 rounded-lg bg-page px-3.5 py-3 text-sm text-muted">Waiting for Claude’s first update…</p>;
  }

  return (
    <ol
      ref={feedRef}
      onScroll={handleScroll}
      aria-label="Claude’s activity"
      className="m-0 flex max-h-72 list-none flex-col gap-0 overflow-y-auto rounded-lg bg-page p-0 py-1.5"
    >
      {activity.map((entry, index) => (
        <li key={`${entry.t}-${index}`} className="flex items-start gap-2.5 px-3.5 py-1.5">
          <span className="w-9 flex-none pt-0.5 text-right text-[12px] text-faint tabular-nums">
            {getEntryTime(entry.t, startedAt)}
          </span>
          <WorkerBadge who={entry.who} />
          <span className={`min-w-0 text-[13.5px] leading-snug break-words ${KIND_TEXT_CLASSES[entry.kind] ?? "text-ink"}`}>
            {entry.text}
          </span>
        </li>
      ))}
    </ol>
  );
}
