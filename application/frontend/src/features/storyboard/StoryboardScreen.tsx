import { useEffect, useRef, useState } from "react";
import { getErrorMessage, startStoryboard } from "../../api/client";
import { JobProgressCard } from "../../components/JobProgressCard";
import { ErrorMessage, LoadingMessage } from "../../components/Messages";
import { StageList } from "../../components/StageList";
import { StepHeader } from "../../components/StepHeader";
import { PRIMARY_BUTTON, SECONDARY_BUTTON } from "../../components/styles";
import { useJobPolling } from "../../hooks/useJobPolling";
import { useProject } from "../../hooks/useProject";
import { ROUTES } from "../../routes";
import { StoryboardResult } from "./StoryboardResult";
import { useStoryboard } from "./useStoryboard";

export function StoryboardScreen({ projectId }: { projectId: string }) {
  const { project, projectError, reloadProject } = useProject(projectId);
  const { job, setJob, hasLoadedJob, isRunning, jobError } = useJobPolling(projectId, reloadProject);
  const { storyboard, storyboardError } = useStoryboard(project);
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const hasAutoStartedRef = useRef(false);

  const handleStartStoryboard = async () => {
    setIsStarting(true);
    setStartError(null);
    try {
      setJob(await startStoryboard(projectId));
    } catch (error) {
      setStartError(getErrorMessage(error));
    } finally {
      setIsStarting(false);
    }
  };

  // Starts a storyboard automatically, once, when the project has none and nothing is running.
  useEffect(() => {
    if (!project || !hasLoadedJob || hasAutoStartedRef.current) return;
    if (project.has_storyboard || isRunning) return;
    hasAutoStartedRef.current = true;
    handleStartStoryboard();
  }, [project, hasLoadedJob, isRunning]);

  if (projectError) return <ErrorMessage message={projectError} />;
  if (!project) return <LoadingMessage />;

  const renderContent = () => {
    if (jobError && !hasLoadedJob) return <ErrorMessage message={jobError} />;
    if (!hasLoadedJob || isStarting) return <LoadingMessage text="Starting the storyboard…" />;

    if (job && isRunning) {
      return (
        <>
          <JobProgressCard job={job}>
            <p className="m-0 text-sm text-muted">
              Making voices, Claude directing the shots, and drawing frames. The final render reuses this work.
            </p>
          </JobProgressCard>
          <div className="flex">
            <StageList stages={job.stages} />
          </div>
        </>
      );
    }

    // The job just finished and the project is being reloaded.
    const isWaitingForProjectReload = job?.state === "done" && !project.has_storyboard && !startError;
    if (isWaitingForProjectReload) return <LoadingMessage />;

    if (!project.has_storyboard) {
      return (
        <section className="flex flex-col items-start gap-3 rounded-xl border border-line bg-surface p-6">
          <p className="m-0 text-[15px]">The storyboard couldn’t be made.</p>
          <ErrorMessage message={startError ?? job?.error ?? null} />
          <div className="flex flex-wrap gap-2.5">
            <button type="button" className={PRIMARY_BUTTON} onClick={handleStartStoryboard}>
              Try again
            </button>
            <a href={ROUTES.projectStep(projectId, "cast")} className={SECONDARY_BUTTON}>
              Back to cast
            </a>
          </div>
        </section>
      );
    }

    if (storyboardError) return <ErrorMessage message={storyboardError} />;
    if (!storyboard) return <LoadingMessage />;
    return <StoryboardResult projectId={projectId} storyboard={storyboard} />;
  };

  return (
    <div className="flex max-w-[1120px] flex-col gap-6">
      <StepHeader projectId={projectId} title={project.title} activeStep="storyboard" />
      {renderContent()}
    </div>
  );
}
