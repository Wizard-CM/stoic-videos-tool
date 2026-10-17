import { useEffect, useState } from "react";
import { getErrorMessage } from "../api/client";
import { useDebouncedValue } from "./useDebouncedValue";

const AUTOSAVE_DELAY_MS = 600;

// Holds an editable draft and saves it shortly after each change.
// `save` returns the draft as the server stored it (e.g. with an automatic voice picked).
export function useAutosaveDraft<T>(initialDraft: T, save: (draft: T) => Promise<T>) {
  const [draft, setDraft] = useState(initialDraft);
  const [savedDraft, setSavedDraft] = useState(initialDraft);
  const [saveError, setSaveError] = useState<string | null>(null);

  const debouncedDraft = useDebouncedValue(draft, AUTOSAVE_DELAY_MS);
  const hasUnsavedChanges = draft !== savedDraft;

  const saveDraft = async (draftToSave: T) => {
    try {
      const storedDraft = await save(draftToSave);
      setSavedDraft(storedDraft);
      // Show what the server stored, unless the user kept typing meanwhile.
      setDraft((currentDraft) => (currentDraft === draftToSave ? storedDraft : currentDraft));
      setSaveError(null);
    } catch (error) {
      setSaveError(getErrorMessage(error));
    }
  };

  useEffect(() => {
    if (debouncedDraft === savedDraft) return;
    saveDraft(debouncedDraft);
  }, [debouncedDraft]);

  const updateDraft = (changes: Partial<T>) => {
    setDraft((currentDraft) => ({ ...currentDraft, ...changes }));
  };

  // Replaces the draft with fresh server data, e.g. after Claude revised the item.
  const resetDraft = (freshDraft: T) => {
    setDraft(freshDraft);
    setSavedDraft(freshDraft);
  };

  return { draft, updateDraft, resetDraft, hasUnsavedChanges, saveError };
}
