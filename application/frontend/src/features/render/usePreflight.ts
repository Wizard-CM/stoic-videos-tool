import { useEffect, useState } from "react";
import { getErrorMessage, getPreflight, type Preflight } from "../../api/client";

export function usePreflight(projectId: string) {
  const [preflight, setPreflight] = useState<Preflight | null>(null);
  const [preflightError, setPreflightError] = useState<string | null>(null);

  useEffect(() => {
    getPreflight(projectId)
      .then(setPreflight)
      .catch((error) => setPreflightError(getErrorMessage(error)));
  }, [projectId]);

  return { preflight, preflightError };
}
