type SaveStatusProps = {
  hasUnsavedChanges: boolean;
  saveError: string | null;
};

export function SaveStatus({ hasUnsavedChanges, saveError }: SaveStatusProps) {
  if (saveError) {
    return (
      <span role="alert" className="text-danger">
        Couldn’t save: {saveError}
      </span>
    );
  }
  if (hasUnsavedChanges) return <span>Saving…</span>;
  return <span>All changes saved</span>;
}
