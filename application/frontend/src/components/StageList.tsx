import type { JobStage } from "../api/client";
import { ActiveIcon, DoneIcon, WaitingIcon } from "./icons";

// Longer notes, like Claude's latest activity while it directs, wrap under the label.
const LONG_NOTE_LENGTH = 32;

function StageIcon({ state }: { state: JobStage["state"] }) {
  if (state === "done") return <DoneIcon />;
  if (state === "active") return <ActiveIcon isSpinning />;
  return <WaitingIcon />;
}

function getStageNote(stage: JobStage) {
  if (stage.note) return stage.note;
  if (stage.state === "waiting") return "Waiting";
  if (stage.state === "skipped") return "Skipped";
  return "";
}

function getStageLabelClass(state: JobStage["state"]) {
  if (state === "active") return "font-semibold text-ink";
  if (state === "done") return "text-ink-soft";
  return "text-muted";
}

export function StageList({ stages }: { stages: JobStage[] }) {
  return (
    <section aria-label="Stages" className="min-w-0 flex-[999_1_420px] rounded-xl border border-line bg-surface py-2">
      <h2 className="m-0 px-5 pt-3.5 pb-2 text-base font-semibold">Stages</h2>
      <ol className="m-0 list-none p-0">
        {stages.map((stage) => {
          const note = getStageNote(stage);
          const isLongNote = note.length > LONG_NOTE_LENGTH;
          return (
            <li key={stage.key} className="flex min-h-[46px] items-center gap-3 border-t border-divider px-5 py-2">
              <StageIcon state={stage.state} />
              <span className="flex min-w-0 flex-1 flex-col">
                <span className={`text-[15px] ${getStageLabelClass(stage.state)}`}>{stage.label}</span>
                {isLongNote && <span className="text-[13px] break-words text-muted">{note}</span>}
              </span>
              {!isLongNote && <span className="text-[13.5px] text-muted tabular-nums">{note}</span>}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
