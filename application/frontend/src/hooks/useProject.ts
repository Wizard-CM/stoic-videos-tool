import { useCallback, useEffect, useState } from "react";
import { getErrorMessage, getProject, type Project } from "../api/client";

export function useProject(projectId: string) {
  const [project, setProject] = useState<Project | null>(null);
  const [projectError, setProjectError] = useState<string | null>(null);

  // Memoized because job polling calls it from inside an effect when a job finishes.
  const reloadProject = useCallback(async () => {
    try {
      setProject(await getProject(projectId));
      setProjectError(null);
    } catch (error) {
      setProjectError(getErrorMessage(error));
    }
  }, [projectId]);

  useEffect(() => {
    reloadProject();
  }, [reloadProject]);

  return { project, setProject, projectError, reloadProject };
}
