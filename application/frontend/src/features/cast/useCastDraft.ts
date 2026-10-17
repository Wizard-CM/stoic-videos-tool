import { useEffect, useState } from "react";
import { getErrorMessage, setCastMember, type CastEntry, type Project } from "../../api/client";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";

const AUTOSAVE_DELAY_MS = 500;

type CastMap = Record<string, CastEntry>;

// Holds the project's cast while it is edited, and autosaves each changed speaker shortly after a change.
export function useCastDraft(project: Project) {
  const [cast, setCast] = useState<CastMap>(() => project.cast);
  const [savedCast, setSavedCast] = useState(cast);
  const [saveError, setSaveError] = useState<string | null>(null);

  const debouncedCast = useDebouncedValue(cast, AUTOSAVE_DELAY_MS);
  const hasUnsavedChanges = cast !== savedCast;

  const saveChangedSpeakers = async (castToSave: CastMap) => {
    const changedSpeakers = Object.keys(castToSave).filter((speaker) => castToSave[speaker] !== savedCast[speaker]);
    try {
      for (const speaker of changedSpeakers) {
        await setCastMember(project.id, speaker, castToSave[speaker]);
      }
      setSavedCast(castToSave);
      setSaveError(null);
      return true;
    } catch (error) {
      setSaveError(getErrorMessage(error));
      return false;
    }
  };

  useEffect(() => {
    if (debouncedCast === savedCast) return;
    saveChangedSpeakers(debouncedCast);
  }, [debouncedCast]);

  const setCastEntry = (speaker: string, castEntry: CastEntry) => {
    setCast((currentCast) => ({ ...currentCast, [speaker]: castEntry }));
  };

  // Saves one speaker right away (used after "Save to library"), skipping the autosave delay.
  const saveCastEntryNow = async (speaker: string, castEntry: CastEntry) => {
    await setCastMember(project.id, speaker, castEntry);
    setCast((currentCast) => ({ ...currentCast, [speaker]: castEntry }));
    setSavedCast((currentSavedCast) => ({ ...currentSavedCast, [speaker]: castEntry }));
  };

  const saveUnsavedChanges = async () => {
    if (!hasUnsavedChanges) return true;
    return saveChangedSpeakers(cast);
  };

  return { cast, setCastEntry, saveCastEntryNow, hasUnsavedChanges, saveError, saveUnsavedChanges };
}
