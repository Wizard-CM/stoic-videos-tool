import { useState } from "react";
import { createProject, getErrorMessage } from "../../api/client";
import { PlusIcon } from "../../components/icons";
import { ErrorMessage, LoadingMessage } from "../../components/Messages";
import { PRIMARY_BUTTON, TEXT_INPUT } from "../../components/styles";
import { navigateTo, ROUTES } from "../../routes";
import { ProjectCard } from "./ProjectCard";
import { useProjectList } from "./useProjectList";

export function ProjectsScreen() {
  const { projects, projectsError, reloadProjects } = useProjectList();
  const [searchText, setSearchText] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const normalizedSearch = searchText.trim().toLowerCase();
  const visibleProjects = (projects ?? []).filter((project) =>
    project.title.toLowerCase().includes(normalizedSearch),
  );
  const hasNoSearchMatches = normalizedSearch !== "" && visibleProjects.length === 0;

  const handleNewVideoClick = async () => {
    setIsCreating(true);
    setCreateError(null);
    try {
      const project = await createProject();
      navigateTo(ROUTES.projectStep(project.id, "script"));
    } catch (error) {
      setCreateError(getErrorMessage(error));
      setIsCreating(false);
    }
  };

  return (
    <div className="flex max-w-[1040px] flex-col gap-7">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <h1 className="m-0 text-[30px] font-semibold tracking-[-0.01em]">Projects</h1>
          <p className="m-0 text-[15px] text-muted">Paste a tagged script, pick your cast, and render.</p>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <button type="button" className={PRIMARY_BUTTON} disabled={isCreating} onClick={handleNewVideoClick}>
            <PlusIcon />
            New video
          </button>
          <ErrorMessage message={createError} />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <label htmlFor="project-search" className="text-sm text-ink-soft">
          Search
        </label>
        <input
          id="project-search"
          type="search"
          placeholder="Project title"
          value={searchText}
          onChange={(event) => setSearchText(event.target.value)}
          className={`${TEXT_INPUT} min-h-11 flex-[0_1_320px]`}
        />
      </div>

      <ErrorMessage message={projectsError} />
      {projects === null && !projectsError && <LoadingMessage />}
      {hasNoSearchMatches && <p className="m-0 text-[15px] text-muted">No projects match “{searchText}”.</p>}

      <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-5">
        {visibleProjects.map((project) => (
          <ProjectCard key={project.id} project={project} onProjectsChange={reloadProjects} />
        ))}
        <button
          type="button"
          disabled={isCreating}
          onClick={handleNewVideoClick}
          className="flex min-h-[220px] flex-col items-center justify-center gap-2 rounded-xl border-[1.5px] border-dashed border-soft-line bg-transparent text-[15px] text-ink-soft"
        >
          <PlusIcon size={28} />
          <span className="font-semibold">Start a new video</span>
          <span className="text-[13.5px] text-muted">Title, script, cast, render</span>
        </button>
      </div>
    </div>
  );
}
