import { useState } from "react";
import {
  deleteBackground,
  getBackground,
  getBackgroundPreviewUrl,
  getErrorMessage,
  reviseBackground,
  updateBackground,
  type BackgroundSummary,
  type CharacterSummary,
} from "../../api/client";
import { CharacterSelect } from "../../components/CharacterSelect";
import { ReviseWithClaude } from "../../components/claude/ReviseWithClaude";
import { ErrorMessage } from "../../components/Messages";
import { PageHeader } from "../../components/PageHeader";
import { PreviewImage } from "../../components/PreviewImage";
import { SaveStatus } from "../../components/SaveStatus";
import { DANGER_BUTTON, FIELD_LABEL, SURFACE_CARD, TEXT_AREA, TEXT_INPUT } from "../../components/styles";
import { useAutosaveDraft } from "../../hooks/useAutosaveDraft";
import { formatCost } from "../../lib/format";
import { SLOT_KEYS } from "../../lib/taskSlots";
import { navigateTo, ROUTES } from "../../routes";

const PREVIEW_WIDTH = 960;

type BackgroundDraft = { name: string; description: string };

type BackgroundEditorProps = {
  initialBackground: BackgroundSummary;
  characters: CharacterSummary[] | null;
};

// The studio for a saved background: preview (optionally with a character), revisions and details.
export function BackgroundEditor({ initialBackground, characters }: BackgroundEditorProps) {
  const backgroundId = initialBackground.id;
  const [updatedAt, setUpdatedAt] = useState(initialBackground.updated_at);
  const [previewCharacterId, setPreviewCharacterId] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const { draft, updateDraft, resetDraft, hasUnsavedChanges, saveError } = useAutosaveDraft<BackgroundDraft>(
    { name: initialBackground.name, description: initialBackground.description },
    async (draftToSave) => {
      const { name, description } = await updateBackground(backgroundId, draftToSave);
      return { name, description };
    },
  );

  const handleRevised = async () => {
    const revisedBackground = await getBackground(backgroundId);
    setUpdatedAt(revisedBackground.updated_at);
    resetDraft({ name: revisedBackground.name, description: revisedBackground.description });
  };

  const handleDeleteClick = async () => {
    if (!window.confirm(`Delete “${draft.name}” from the library? Projects keep their own copy.`)) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await deleteBackground(backgroundId);
      navigateTo(ROUTES.library("backgrounds"));
    } catch (error) {
      setDeleteError(getErrorMessage(error));
      setIsDeleting(false);
    }
  };

  const displayName = draft.name || "Untitled background";
  const previewUrl = getBackgroundPreviewUrl(backgroundId, {
    width: PREVIEW_WIDTH,
    characterId: previewCharacterId || null,
    version: updatedAt,
  });

  return (
    <div className="flex max-w-[1120px] flex-col gap-6">
      <PageHeader
        parentLabel="Library"
        parentHref={ROUTES.library("backgrounds")}
        title={displayName}
        statusText={<SaveStatus hasUnsavedChanges={hasUnsavedChanges} saveError={saveError} />}
      />

      <div className="flex flex-wrap items-start gap-6">
        <section aria-label="Preview" className="flex min-w-0 flex-[999_1_520px] flex-col gap-4">
          <PreviewImage
            src={previewUrl}
            alt={`${displayName} background preview`}
            className="aspect-video border border-line"
          />
          <div className="max-w-xs">
            <CharacterSelect
              id="background-preview-character"
              label="Show a character in it"
              characters={characters}
              value={previewCharacterId}
              onValueChange={setPreviewCharacterId}
            />
          </div>
        </section>

        <div className="flex min-w-0 flex-[1_1_320px] flex-col gap-5">
          <ReviseWithClaude
            slotKey={SLOT_KEYS.reviseBackground(backgroundId)}
            subjectName={displayName}
            placeholder="e.g. make it evening with warmer light, and add a plant on the left"
            revise={(feedback) => reviseBackground(backgroundId, feedback)}
            onRevised={handleRevised}
          />

          <section aria-label="Details" className={`${SURFACE_CARD} flex flex-col gap-[18px] p-5`}>
            <h2 className="m-0 text-[17px] font-semibold">Details</h2>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="background-name" className={FIELD_LABEL}>
                Name
              </label>
              <input
                id="background-name"
                type="text"
                value={draft.name}
                onChange={(event) => updateDraft({ name: event.target.value })}
                className={TEXT_INPUT}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="background-description" className={FIELD_LABEL}>
                Description
              </label>
              <textarea
                id="background-description"
                rows={3}
                value={draft.description}
                onChange={(event) => updateDraft({ description: event.target.value })}
                className={TEXT_AREA}
              />
              <p className="m-0 text-[13px] text-muted">
                Editing these doesn’t redraw the set. To change it, ask Claude above.
              </p>
            </div>
            {initialBackground.made_by && (
              <p className="m-0 text-[13px] text-muted">
                Designed by Claude for {formatCost(initialBackground.made_by.cost_usd)}.
              </p>
            )}
            <div className="flex flex-col items-start gap-1.5 border-t border-line pt-4">
              <button type="button" className={DANGER_BUTTON} disabled={isDeleting} onClick={handleDeleteClick}>
                Delete background
              </button>
              <ErrorMessage message={deleteError} />
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
