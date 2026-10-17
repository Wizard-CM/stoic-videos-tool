import { useEffect, useState } from "react";
import { getErrorMessage, updateProject, type Project, type ProjectSettings } from "../../api/client";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";

const AUTOSAVE_DELAY_MS = 600;

export type ScriptDraft = {
  title: string;
  script: string;
  settings: ProjectSettings;
};

// Holds the editable title, script and settings, and autosaves them shortly after each change.
export function useScriptDraft(project: Project) {
  const [draft, setDraft] = useState<ScriptDraft>(() => ({
    title: project.title,
    script: project.script,
    settings: project.settings,
  }));
  const [savedDraft, setSavedDraft] = useState(draft);
  const [saveError, setSaveError] = useState<string | null>(null);

  const debouncedDraft = useDebouncedValue(draft, AUTOSAVE_DELAY_MS);
  const hasUnsavedChanges = draft !== savedDraft;

  const saveDraft = async (draftToSave: ScriptDraft) => {
    try {
      await updateProject(project.id, draftToSave);
      setSavedDraft(draftToSave);
      setSaveError(null);
      return true;
    } catch (error) {
      setSaveError(getErrorMessage(error));
      return false;
    }
  };

  useEffect(() => {
    if (debouncedDraft === savedDraft) return;
    saveDraft(debouncedDraft);
  }, [debouncedDraft]);

  const updateDraft = (changes: Partial<ScriptDraft>) => {
    setDraft((currentDraft) => ({ ...currentDraft, ...changes }));
  };

  const saveUnsavedChanges = async () => {
    if (!hasUnsavedChanges) return true;
    return saveDraft(draft);
  };

  // Records changes that were already saved elsewhere (e.g. a script Claude wrote), without saving again.
  const applySavedChanges = (changes: Partial<ScriptDraft>) => {
    const nextDraft = { ...draft, ...changes };
    setDraft(nextDraft);
    setSavedDraft(nextDraft);
  };

  return { draft, updateDraft, applySavedChanges, hasUnsavedChanges, saveError, saveUnsavedChanges };
}
