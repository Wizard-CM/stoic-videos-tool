import { useState } from "react";
import {
  getBackgroundPreviewUrl,
  getErrorMessage,
  setCastBackground,
  type BackgroundSummary,
  type CastEntry,
  type CharacterSummary,
  type Project,
} from "../../api/client";
import { ErrorMessage } from "../../components/Messages";
import { PreviewImage } from "../../components/PreviewImage";
import { SURFACE_CARD } from "../../components/styles";
import { readTaskSlot, SLOT_KEYS } from "../../lib/taskSlots";
import { BackgroundDesignForm } from "../background-studio/BackgroundDesignForm";
import { LibraryBackgroundPicker } from "./LibraryBackgroundPicker";

const PREVIEW_WIDTH = 640;
const SELECTED_CHOICE = "border-[1.5px] border-accent bg-accent-tint";
const UNSELECTED_CHOICE = "border border-field bg-surface";

type SectionMode = "view" | "library" | "design";

type CastBackgroundSectionProps = {
  project: Project;
  speaker: string;
  characters: CharacterSummary[] | null;
  backgrounds: BackgroundSummary[] | null;
  backgroundsError: string | null;
  onProjectChange: (project: Project) => void;
  onBackgroundsChange: () => void;
};

type ChoiceButtonProps = {
  title: string;
  note: string;
  isSelected: boolean;
  disabled: boolean;
  onClick: () => void;
};

function ChoiceButton({ title, note, isSelected, disabled, onClick }: ChoiceButtonProps) {
  return (
    <button
      type="button"
      aria-pressed={isSelected}
      disabled={disabled}
      onClick={onClick}
      className={`flex min-h-11 flex-col gap-0.5 rounded-lg px-3.5 py-2.5 text-left disabled:opacity-60 ${isSelected ? SELECTED_CHOICE : UNSELECTED_CHOICE}`}
    >
      <span className="text-[14.5px] font-semibold text-ink">{title}</span>
      <span className="text-[13px] text-muted">{note}</span>
    </button>
  );
}

function PlaceholderFrame({ title, note }: { title: string; note: string }) {
  return (
    <div className="flex aspect-video flex-col items-center justify-center gap-1 rounded-xl border-[1.5px] border-dashed border-soft-line bg-page p-6 text-center">
      <p className="m-0 text-[15px] font-semibold text-ink-soft">{title}</p>
      <p className="m-0 max-w-sm text-[13.5px] text-muted">{note}</p>
    </div>
  );
}

// What the speaker's background currently is.
function CurrentBackground({ castEntry }: { castEntry: CastEntry }) {
  const { background, background_library_id: libraryId } = castEntry;

  if (libraryId) {
    const previewUrl = getBackgroundPreviewUrl(libraryId, {
      width: PREVIEW_WIDTH,
      characterId: castEntry.library_id,
      version: background?.updated_at,
    });
    return (
      <figure className="m-0 flex flex-col gap-2">
        <PreviewImage src={previewUrl} alt={`${background?.name ?? "Background"} preview`} className="aspect-video" />
        <figcaption className="text-[13.5px] text-muted">{background?.name ?? "Library background"}, from your library</figcaption>
      </figure>
    );
  }

  if (background) {
    return (
      <PlaceholderFrame
        title="Designed by Claude for this video"
        note={[background.name, background.description].filter(Boolean).join(": ")}
      />
    );
  }

  return (
    <PlaceholderFrame
      title="Claude designs it for this video"
      note="Claude paints a set that fits the script when you make the storyboard or render."
    />
  );
}

// Where this speaker is: Claude's choice for this video, a library background, or a new one designed here.
export function CastBackgroundSection({
  project,
  speaker,
  characters,
  backgrounds,
  backgroundsError,
  onProjectChange,
  onBackgroundsChange,
}: CastBackgroundSectionProps) {
  const castEntry: CastEntry | undefined = project.cast[speaker];
  const slotKey = SLOT_KEYS.castBackground(project.id, speaker);
  const [mode, setMode] = useState<SectionMode>(() => (readTaskSlot(slotKey) ? "design" : "view"));
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  if (!castEntry) {
    return (
      <section aria-label={`Background for ${speaker}`} className={`${SURFACE_CARD} flex flex-col gap-2 p-5`}>
        <h2 className="m-0 text-[15px] font-semibold text-muted">Background for {speaker}</h2>
        <p className="m-0 text-sm text-muted">Pick a character first, then choose where they are.</p>
      </section>
    );
  }

  const chooseBackground = async (libraryId: string | null) => {
    setIsSaving(true);
    setSaveError(null);
    try {
      onProjectChange(await setCastBackground(project.id, speaker, libraryId));
      setMode("view");
    } catch (error) {
      setSaveError(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  };

  const handleBackgroundCreated = async (backgroundId: string) => {
    onProjectChange(await setCastBackground(project.id, speaker, backgroundId));
    onBackgroundsChange();
    setMode("view");
  };

  if (mode === "design") {
    return (
      <BackgroundDesignForm
        slotKey={slotKey}
        heading={`Design a background for ${speaker}`}
        characters={characters}
        defaultCharacterId={castEntry.library_id}
        onCreated={handleBackgroundCreated}
        onCancel={() => setMode("view")}
      />
    );
  }

  const isClaudeChoice = castEntry.background_library_id === null;

  return (
    <section aria-label={`Background for ${speaker}`} className={`${SURFACE_CARD} flex flex-col gap-4 p-5`}>
      <h2 className="m-0 text-[15px] font-semibold text-muted">Background for {speaker}</h2>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(190px,1fr))] gap-2">
        <ChoiceButton
          title="Claude designs it"
          note="A set made for this video"
          isSelected={isClaudeChoice && mode === "view"}
          disabled={isSaving}
          onClick={() => (isClaudeChoice ? setMode("view") : chooseBackground(null))}
        />
        <ChoiceButton
          title="From the library"
          note="Reuse a saved set"
          isSelected={mode === "library" || (!isClaudeChoice && mode === "view")}
          disabled={isSaving}
          onClick={() => setMode("library")}
        />
        <ChoiceButton
          title="Design a background"
          note="Describe it, Claude paints it"
          isSelected={false}
          disabled={isSaving}
          onClick={() => setMode("design")}
        />
      </div>

      {mode === "library" ? (
        <div className="flex flex-col gap-3">
          <ErrorMessage message={backgroundsError} />
          <LibraryBackgroundPicker
            backgrounds={backgrounds}
            selectedId={castEntry.background_library_id}
            isBusy={isSaving}
            onPick={chooseBackground}
          />
        </div>
      ) : (
        <CurrentBackground castEntry={castEntry} />
      )}
      <ErrorMessage message={saveError} />
    </section>
  );
}
