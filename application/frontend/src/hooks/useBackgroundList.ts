import { useEffect, useState } from "react";
import { getErrorMessage, listBackgrounds, type BackgroundSummary } from "../api/client";

export function useBackgroundList() {
  const [backgrounds, setBackgrounds] = useState<BackgroundSummary[] | null>(null);
  const [backgroundsError, setBackgroundsError] = useState<string | null>(null);

  const reloadBackgrounds = async () => {
    try {
      setBackgrounds(await listBackgrounds());
      setBackgroundsError(null);
    } catch (error) {
      setBackgroundsError(getErrorMessage(error));
    }
  };

  useEffect(() => {
    reloadBackgrounds();
  }, []);

  return { backgrounds, backgroundsError, reloadBackgrounds };
}
