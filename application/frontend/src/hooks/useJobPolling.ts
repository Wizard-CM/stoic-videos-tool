import { useEffect, useState } from "react";
import { getErrorMessage, getJob, type Job } from "../api/client";

const POLL_INTERVAL_MS = 1000;

export function isJobActive(job: Job | null) {
  return job !== null && (job.state === "queued" || job.state === "running");
}

// Loads the project's job once, then polls every second while it is queued or running.
// `onJobFinish` must be stable (wrap it in useCallback) because it is an effect dependency.
export function useJobPolling(projectId: string, onJobFinish: () => void) {
  const [job, setJob] = useState<Job | null>(null);
  const [hasLoadedJob, setHasLoadedJob] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);

  const isRunning = isJobActive(job);

  useEffect(() => {
    let isCancelled = false;

    getJob(projectId)
      .then((loadedJob) => {
        if (isCancelled) return;
        setJob(loadedJob);
        setHasLoadedJob(true);
      })
      .catch((error) => {
        if (!isCancelled) setJobError(getErrorMessage(error));
      });

    return () => {
      isCancelled = true;
    };
  }, [projectId]);

  useEffect(() => {
    if (!isRunning) return;
    let isCancelled = false;

    const intervalId = setInterval(async () => {
      try {
        const latestJob = await getJob(projectId);
        if (isCancelled) return;
        setJob(latestJob);
        setJobError(null);
        if (!isJobActive(latestJob)) onJobFinish();
      } catch (error) {
        if (!isCancelled) setJobError(getErrorMessage(error));
      }
    }, POLL_INTERVAL_MS);

    return () => {
      isCancelled = true;
      clearInterval(intervalId);
    };
  }, [projectId, isRunning, onJobFinish]);

  return { job, setJob, hasLoadedJob, isRunning, jobError };
}
