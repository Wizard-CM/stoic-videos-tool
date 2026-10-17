import { useEffect, useState } from "react";
import { getErrorMessage, listProjects, type ProjectListItem } from "../../api/client";

export function useProjectList() {
  const [projects, setProjects] = useState<ProjectListItem[] | null>(null);
  const [projectsError, setProjectsError] = useState<string | null>(null);

  const reloadProjects = async () => {
    try {
      setProjects(await listProjects());
      setProjectsError(null);
    } catch (error) {
      setProjectsError(getErrorMessage(error));
    }
  };

  useEffect(() => {
    reloadProjects();
  }, []);

  return { projects, projectsError, reloadProjects };
}
