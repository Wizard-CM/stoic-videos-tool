import type { JobStage } from "../api/client";
import { ActiveIcon, DoneIcon, WaitingIcon } from "./icons";

function StageIcon({ state }: { state: JobStage["state"] }) {
  if (state === "done") return <DoneIcon />;
  if (state === "active") return <ActiveIcon />;
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
        {stages.map((stage) => (
          <li key={stage.key} className="flex min-h-[46px] items-center gap-3 border-t border-divider px-5">
            <StageIcon state={stage.state} />
            <span className={`flex-1 text-[15px] ${getStageLabelClass(stage.state)}`}>{stage.label}</span>
            <span className="text-[13.5px] text-muted tabular-nums">{getStageNote(stage)}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
