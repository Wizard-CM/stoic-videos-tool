import type { Storyboard } from "../../api/client";
import { WorkerBadge } from "../../components/claude/ActivityFeed";
import { getAspectClass, PRIMARY_BUTTON, SECONDARY_BUTTON } from "../../components/styles";
import { formatDuration } from "../../lib/format";
import { ROUTES } from "../../routes";

type StoryboardResultProps = {
  projectId: string;
  storyboard: Storyboard;
};

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="m-0 text-[13.5px] text-muted">{label}</p>
      <p className="mt-0.5 mb-0 text-[22px] font-semibold">{value}</p>
    </div>
  );
}

export function StoryboardResult({ projectId, storyboard }: StoryboardResultProps) {
  const aspectClass = getAspectClass(storyboard.aspect);

  return (
    <>
      <div className="flex flex-wrap items-stretch gap-6">
        <section aria-label="Preview clip" className="flex min-w-0 flex-[999_1_520px] flex-col gap-2.5">
          <div className="overflow-hidden rounded-xl bg-ink">
            <video src={storyboard.preview_url} controls className={`block w-full ${aspectClass}`} />
          </div>
          <p className="m-0 text-[13.5px] text-muted">
            Preview of the first {formatDuration(storyboard.preview_length_s)} at 540p with final voices. The full
            render reuses these voices.
          </p>
        </section>

        <aside
          aria-label="Storyboard summary"
          className="flex min-w-0 flex-[1_1_280px] flex-col gap-[18px] rounded-xl border border-line bg-surface p-5"
        >
          <div className="grid grid-cols-2 gap-3.5">
            <SummaryStat label="Final length" value={formatDuration(storyboard.length_s)} />
            <SummaryStat label="Shots" value={String(storyboard.shot_count)} />
            <SummaryStat label="Reaction shots" value={String(storyboard.reaction_count)} />
            <SummaryStat label="Preview" value={formatDuration(storyboard.preview_length_s)} />
          </div>
          {storyboard.director_notes && (
            <div className="flex flex-col gap-1.5 rounded-lg bg-page p-3.5">
              <p className="m-0 flex flex-wrap items-center gap-2 text-sm font-semibold">
                Director’s notes <WorkerBadge who="lead" />
              </p>
              <p className="m-0 text-sm whitespace-pre-line text-ink-soft">{storyboard.director_notes}</p>
            </div>
          )}
          <div className="mt-auto flex flex-col gap-2">
            <a href={ROUTES.projectStep(projectId, "render")} className={`${PRIMARY_BUTTON} min-h-[46px]`}>
              Looks good, render video
            </a>
            <a href={ROUTES.projectStep(projectId, "script")} className={SECONDARY_BUTTON}>
              Back to the script
            </a>
          </div>
        </aside>
      </div>

      <section aria-label="Storyboard frames" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="m-0 text-[17px] font-semibold">Storyboard</h2>
          <p className="m-0 text-[13.5px] text-muted">
            {storyboard.frames.length} frames spread across the whole video
          </p>
        </div>
        <div className="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-3.5">
          {storyboard.frames.map((frame) => (
            <figure key={frame.url} className="m-0 overflow-hidden rounded-[10px] border border-line bg-surface">
              <img src={frame.url} alt="" className={`block w-full bg-placeholder object-cover ${aspectClass}`} />
              <figcaption className="flex flex-col gap-[3px] px-3 py-2.5">
                <span className="flex justify-between gap-2 text-[12.5px] text-muted">
                  <span className="tabular-nums">{frame.t_label}</span>
                  <span>{frame.shot_label}</span>
                </span>
                <span className="text-[13.5px] leading-snug text-ink">{frame.caption}</span>
              </figcaption>
            </figure>
          ))}
        </div>
      </section>
    </>
  );
}
