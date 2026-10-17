import { useEffect, useState } from "react";
import { getErrorMessage, getStoryboard, type Project, type Storyboard } from "../../api/client";

// Loads the storyboard once the project has one, and again whenever the project is updated.
export function useStoryboard(project: Project | null) {
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [storyboardError, setStoryboardError] = useState<string | null>(null);

  const projectId = project?.id;
  const hasStoryboard = project?.has_storyboard ?? false;
  const projectUpdatedAt = project?.updated_at;

  useEffect(() => {
    if (!projectId || !hasStoryboard) return;
    let isCancelled = false;

    getStoryboard(projectId)
      .then((loadedStoryboard) => {
        if (isCancelled) return;
        setStoryboard(loadedStoryboard);
        setStoryboardError(null);
      })
      .catch((error) => {
        if (!isCancelled) setStoryboardError(getErrorMessage(error));
      });

    return () => {
      isCancelled = true;
    };
  }, [projectId, hasStoryboard, projectUpdatedAt]);

  return { storyboard, storyboardError };
}
