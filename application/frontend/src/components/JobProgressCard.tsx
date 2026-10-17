import type { ReactNode } from "react";
import type { Job } from "../api/client";
import { formatTimeLeft } from "../lib/format";
import { ProgressBar } from "./ProgressBar";

type JobProgressCardProps = {
  job: Job;
  // Extra content under the bar, e.g. a note and a Cancel button.
  children?: ReactNode;
};

export function JobProgressCard({ job, children }: JobProgressCardProps) {
  return (
    <section aria-label="Progress" className="flex flex-col gap-4 rounded-xl border border-line bg-surface p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <p className="m-0 text-[15px] text-muted">{job.message}</p>
          <p className="m-0 text-[40px] font-semibold tracking-[-0.02em] tabular-nums">{Math.round(job.percent)}%</p>
        </div>
        {job.eta_s !== null && <p className="m-0 text-[15px] text-ink-soft">{formatTimeLeft(job.eta_s)}</p>}
      </div>
      <ProgressBar percent={job.percent} label="Overall progress" />
      {children}
    </section>
  );
}
