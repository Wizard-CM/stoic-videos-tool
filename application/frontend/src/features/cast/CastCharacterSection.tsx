import { useState } from "react";
import {
  getErrorMessage,
  setCastCharacter,
  type CastEntry,
  type CharacterSummary,
  type Options,
  type Project,
} from "../../api/client";
import { CharacterAvatar } from "../../components/CharacterAvatar";
import { SparkleIcon } from "../../components/icons";
import { ErrorMessage } from "../../components/Messages";
import { LINK_BUTTON, PRIMARY_BUTTON, SECONDARY_BUTTON, SURFACE_CARD } from "../../components/styles";
import { capitalize } from "../../lib/format";
import { readTaskSlot, SLOT_KEYS } from "../../lib/taskSlots";
import { ROUTES } from "../../routes";
import { CharacterDesignForm } from "../character-studio/CharacterDesignForm";
import { LibraryCharacterPicker } from "./LibraryCharacterPicker";

type SectionMode = "view" | "choose" | "design";

type CastCharacterSectionProps = {
  project: Project;
  speaker: string;
  options: Options;
  characters: CharacterSummary[] | null;
  charactersError: string | null;
  onProjectChange: (project: Project) => void;
  onCharactersChange: () => void;
};

function isLibraryNewer(castEntry: CastEntry, libraryCharacter: CharacterSummary | undefined) {
  if (!libraryCharacter) return false;
  return Date.parse(libraryCharacter.updated_at) > Date.parse(castEntry.character.updated_at);
}

type CastCharacterCardProps = {
  castEntry: CastEntry;
  options: Options;
  libraryCharacter: CharacterSummary | undefined;
  isSaving: boolean;
  onChangeClick: () => void;
  onUseLatestClick: () => void;
};

function CastCharacterCard({
  castEntry,
  options,
  libraryCharacter,
  isSaving,
  onChangeClick,
  onUseLatestClick,
}: CastCharacterCardProps) {
  const { character, library_id: libraryId } = castEntry;
  const voiceLabel = options.voices.find((voice) => voice.id === character.voice.voice_id)?.label;

  return (
    <div className="flex flex-wrap items-start gap-4">
      <CharacterAvatar characterId={libraryId} name={character.name} version={character.updated_at} sizeClass="size-20" />
      <div className="flex min-w-0 flex-[1_1_280px] flex-col gap-1.5">
        <p className="m-0 text-[17px] font-semibold">{character.name}</p>
        {character.description && <p className="m-0 text-sm text-muted">{character.description}</p>}
        {voiceLabel && <p className="m-0 text-[13px] text-muted">Voice: {voiceLabel}</p>}
        {isLibraryNewer(castEntry, libraryCharacter) && (
          <p className="m-0 text-sm text-ink-soft">
            The library version changed since it was cast.{" "}
            <button type="button" className={LINK_BUTTON} disabled={isSaving} onClick={onUseLatestClick}>
              Use the latest version
            </button>
          </p>
        )}
        <div className="mt-2 flex flex-wrap gap-2.5">
          <button type="button" className={SECONDARY_BUTTON} onClick={onChangeClick}>
            Change character
          </button>
          {libraryId && (
            <a href={ROUTES.editCharacter(libraryId)} className={SECONDARY_BUTTON}>
              Edit look and voice in studio
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

// Who plays this speaker: a library character, or a new one Claude designs right here.
export function CastCharacterSection({
  project,
  speaker,
  options,
  characters,
  charactersError,
  onProjectChange,
  onCharactersChange,
}: CastCharacterSectionProps) {
  const castEntry: CastEntry | undefined = project.cast[speaker];
  const slotKey = SLOT_KEYS.castCharacter(project.id, speaker);
  const [mode, setMode] = useState<SectionMode>(() => {
    if (readTaskSlot(slotKey)) return "design";
    return castEntry ? "view" : "choose";
  });
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const assignCharacter = async (characterId: string) => {
    onProjectChange(await setCastCharacter(project.id, speaker, characterId));
    setMode("view");
  };

  const handleCharacterPick = async (characterId: string) => {
    setIsSaving(true);
    setSaveError(null);
    try {
      await assignCharacter(characterId);
    } catch (error) {
      setSaveError(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  };

  const handleCharacterCreated = async (characterId: string) => {
    await assignCharacter(characterId);
    onCharactersChange();
  };

  if (mode === "design") {
    return (
      <CharacterDesignForm
        slotKey={slotKey}
        options={options}
        heading={`Design a new character for ${speaker}`}
        initialName={capitalize(speaker)}
        onCreated={handleCharacterCreated}
        onCancel={() => setMode(castEntry ? "view" : "choose")}
      />
    );
  }

  if (mode === "choose" || !castEntry) {
    return (
      <section aria-label="Choose a character" className={`${SURFACE_CARD} flex flex-col gap-5 p-5`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="m-0 text-[17px] font-semibold">Choose a character for {speaker}</h2>
          <div className="flex flex-wrap gap-2">
            {castEntry && (
              <button type="button" className={SECONDARY_BUTTON} onClick={() => setMode("view")}>
                Cancel
              </button>
            )}
            <button type="button" className={PRIMARY_BUTTON} onClick={() => setMode("design")}>
              <SparkleIcon />
              Design a new character
            </button>
          </div>
        </div>
        <div className="flex flex-col gap-3">
          <h3 className="m-0 text-[15px] font-semibold">Pick from library</h3>
          <ErrorMessage message={charactersError} />
          <LibraryCharacterPicker
            characters={characters}
            selectedId={castEntry?.library_id ?? null}
            isBusy={isSaving}
            onPick={handleCharacterPick}
          />
        </div>
        <ErrorMessage message={saveError} />
      </section>
    );
  }

  return (
    <section aria-label={`Character for ${speaker}`} className={`${SURFACE_CARD} flex flex-col gap-3 p-5`}>
      <h2 className="m-0 text-[15px] font-semibold text-muted">Character for {speaker}</h2>
      <CastCharacterCard
        castEntry={castEntry}
        options={options}
        libraryCharacter={characters?.find((character) => character.id === castEntry.library_id)}
        isSaving={isSaving}
        onChangeClick={() => setMode("choose")}
        onUseLatestClick={() => castEntry.library_id && handleCharacterPick(castEntry.library_id)}
      />
      <ErrorMessage message={saveError} />
    </section>
  );
}
