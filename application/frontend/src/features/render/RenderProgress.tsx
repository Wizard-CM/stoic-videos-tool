import type { Job } from "../../api/client";
import { JobProgressCard } from "../../components/JobProgressCard";
import { ErrorMessage } from "../../components/Messages";
import { StageList } from "../../components/StageList";
import { DANGER_BUTTON, getAspectClass } from "../../components/styles";

type RenderProgressProps = {
  job: Job;
  aspect: string;
  isCancelling: boolean;
  cancelError: string | null;
  onCancelClick: () => void;
};

function getResumeNote(job: Job) {
  if (job.chunk) {
    return `You can keep using your PC. If it sleeps or restarts, rendering picks up from part ${job.chunk.done + 1}.`;
  }
  return "You can keep using your PC. If it sleeps or restarts, rendering picks up where it stopped.";
}

export function RenderProgress({ job, aspect, isCancelling, cancelError, onCancelClick }: RenderProgressProps) {
  return (
    <>
      <JobProgressCard job={job}>
        <p className="m-0 text-sm text-muted">{getResumeNote(job)}</p>
        <div className="flex flex-wrap items-center gap-2.5">
          <button type="button" className={DANGER_BUTTON} disabled={isCancelling} onClick={onCancelClick}>
            Cancel render
          </button>
          <ErrorMessage message={cancelError} />
        </div>
      </JobProgressCard>

      <div className="flex flex-wrap items-start gap-6">
        <StageList stages={job.stages} />
        <aside aria-label="Latest frame" className="flex min-w-0 flex-[1_1_300px] flex-col gap-2.5">
          <h2 className="m-0 text-base font-semibold">Latest frame</h2>
          <div className={`overflow-hidden rounded-xl bg-placeholder ${getAspectClass(aspect)}`}>
            {job.latest_frame_url && <img src={job.latest_frame_url} alt="" className="size-full object-cover" />}
          </div>
          {job.latest_frame_caption && <p className="m-0 text-[13.5px] text-muted">{job.latest_frame_caption}</p>}
        </aside>
      </div>
    </>
  );
}
