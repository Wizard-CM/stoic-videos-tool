import { useState } from "react";
import {
  deleteProject,
  duplicateProject,
  getErrorMessage,
  getProjectThumbnailUrl,
  type ProjectListItem,
} from "../../api/client";
import { ErrorMessage } from "../../components/Messages";
import { StatusChip } from "../../components/StatusChip";
import { SECONDARY_BUTTON } from "../../components/styles";
import { getProjectChip, getProjectMeta, getProjectOpenRoute } from "./projectCardHelpers";

const CARD_BUTTON = `${SECONDARY_BUTTON} flex-1 px-3 text-sm`;

type ProjectCardProps = {
  project: ProjectListItem;
  onProjectsChange: () => void;
};

export function ProjectCard({ project, onProjectsChange }: ProjectCardProps) {
  const [isBusy, setIsBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const chip = getProjectChip(project);
  const openRoute = getProjectOpenRoute(project);

  const runCardAction = async (action: () => Promise<unknown>) => {
    setIsBusy(true);
    setActionError(null);
    try {
      await action();
      onProjectsChange();
    } catch (error) {
      setActionError(getErrorMessage(error));
    } finally {
      setIsBusy(false);
    }
  };

  const handleDuplicateClick = () => runCardAction(() => duplicateProject(project.id));

  const handleDeleteClick = () => {
    const isConfirmed = window.confirm(`Delete “${project.title}”? This can’t be undone.`);
    if (!isConfirmed) return;
    runCardAction(() => deleteProject(project.id));
  };

  return (
    <article className="flex flex-col overflow-hidden rounded-xl border border-line bg-surface">
      <a href={openRoute} tabIndex={-1} aria-hidden="true" className="block aspect-video bg-placeholder">
        {project.has_thumbnail && (
          <img
            src={getProjectThumbnailUrl(project.id, project.updated_at)}
            alt=""
            className="size-full object-cover"
          />
        )}
      </a>
      <div className="flex flex-col gap-1.5 px-4 pt-3.5 pb-4">
        <div className="flex items-center justify-between gap-2">
          <h2 className="m-0 text-base font-semibold">
            <a href={openRoute} className="text-ink no-underline hover:text-accent-dark">
              {project.title}
            </a>
          </h2>
          <StatusChip label={chip.label} tone={chip.tone} />
        </div>
        <p className="m-0 text-[13.5px] text-muted">{getProjectMeta(project)}</p>
        <div className="mt-2 flex gap-2">
          <button type="button" className={CARD_BUTTON} disabled={isBusy} onClick={handleDuplicateClick}>
            Duplicate
          </button>
          <button type="button" className={CARD_BUTTON} disabled={isBusy} onClick={handleDeleteClick}>
            Delete
          </button>
        </div>
        <ErrorMessage message={actionError} />
      </div>
    </article>
  );
}
