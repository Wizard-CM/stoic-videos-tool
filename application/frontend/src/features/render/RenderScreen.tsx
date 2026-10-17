import { useState } from "react";
import { cancelJob, getDownloadUrl, getErrorMessage, startRender, type Job, type Project } from "../../api/client";
import { ErrorMessage, LoadingMessage } from "../../components/Messages";
import { StageList } from "../../components/StageList";
import { StepHeader } from "../../components/StepHeader";
import { getAspectClass, PRIMARY_BUTTON } from "../../components/styles";
import { useJobPolling } from "../../hooks/useJobPolling";
import { useProject } from "../../hooks/useProject";
import { RenderProgress } from "./RenderProgress";
import { RenderSetup } from "./RenderSetup";

type RenderView = "running" | "finishing" | "done" | "stopped" | "setup";

const STOPPED_JOB_STATES = ["stopped", "cancelled", "failed"];

function getRenderView(job: Job | null, isRunning: boolean, project: Project): RenderView {
  if (isRunning) return "running";
  if (project.status === "ready" && project.output_url) return "done";

  const isRenderJob = job?.kind === "render";
  // The render just finished and the project is being reloaded.
  if (isRenderJob && job.state === "done") return "finishing";
  if (isRenderJob && STOPPED_JOB_STATES.includes(job.state)) return "stopped";
  if (project.status === "stopped" || project.status === "failed") return "stopped";
  return "setup";
}

function getStoppedMessage(job: Job | null) {
  if (job?.state === "cancelled") {
    return "Render cancelled. Finished parts are kept, so resuming picks up where it stopped.";
  }
  if (job?.state === "failed") return "The render failed. Finished parts are kept, so you can try again.";
  return "Rendering stopped, probably because the PC restarted or went to sleep. Resume to continue from the last finished part.";
}

export function RenderScreen({ projectId }: { projectId: string }) {
  const { project, projectError, reloadProject } = useProject(projectId);
  const { job, setJob, hasLoadedJob, isRunning, jobError } = useJobPolling(projectId, reloadProject);
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  const handleStartRenderClick = async () => {
    setIsStarting(true);
    setStartError(null);
    try {
      setJob(await startRender(projectId));
    } catch (error) {
      setStartError(getErrorMessage(error));
    } finally {
      setIsStarting(false);
    }
  };

  const handleCancelClick = async () => {
    setIsCancelling(true);
    setCancelError(null);
    try {
      setJob(await cancelJob(projectId));
      reloadProject();
    } catch (error) {
      setCancelError(getErrorMessage(error));
    } finally {
      setIsCancelling(false);
    }
  };

  if (projectError) return <ErrorMessage message={projectError} />;
  if (!project) return <LoadingMessage />;

  const renderContent = () => {
    if (jobError && !hasLoadedJob) return <ErrorMessage message={jobError} />;
    if (!hasLoadedJob) return <LoadingMessage />;

    const view = getRenderView(job, isRunning, project);

    if (view === "running" && job) {
      return (
        <RenderProgress
          job={job}
          aspect={project.settings.aspect}
          isCancelling={isCancelling}
          cancelError={cancelError}
          onCancelClick={handleCancelClick}
        />
      );
    }

    if (view === "finishing") return <LoadingMessage text="Saving the video…" />;

    if (view === "done" && project.output_url) {
      return (
        <section aria-label="Finished video" className="flex flex-col gap-4 rounded-xl border border-line bg-surface p-6">
          <div className="overflow-hidden rounded-xl bg-ink">
            <video src={project.output_url} controls className={`block w-full ${getAspectClass(project.settings.aspect)}`} />
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <a href={getDownloadUrl(project.output_url)} className={PRIMARY_BUTTON}>
              Download MP4
            </a>
            {project.output_path && <p className="m-0 text-sm text-muted">Saved to {project.output_path}</p>}
          </div>
        </section>
      );
    }

    if (view === "stopped") {
      return (
        <>
          <section className="flex flex-col items-start gap-3 rounded-xl border border-line bg-surface p-6">
            <p className="m-0 text-[15px]">{getStoppedMessage(job)}</p>
            <ErrorMessage message={job?.error ?? null} />
            <button
              type="button"
              className={`${PRIMARY_BUTTON} min-h-[46px]`}
              disabled={isStarting}
              onClick={handleStartRenderClick}
            >
              Resume render
            </button>
            <ErrorMessage message={startError} />
          </section>
          {job && job.stages.length > 0 && (
            <div className="flex">
              <StageList stages={job.stages} />
            </div>
          )}
        </>
      );
    }

    return (
      <RenderSetup
        projectId={projectId}
        isStarting={isStarting}
        startError={startError}
        onStartClick={handleStartRenderClick}
      />
    );
  };

  return (
    <div className="flex max-w-[1080px] flex-col gap-6">
      <StepHeader projectId={projectId} title={project.title} activeStep="render" />
      {renderContent()}
    </div>
  );
}
