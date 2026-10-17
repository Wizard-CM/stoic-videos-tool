import { useState } from "react";
import {
  createCharacter,
  getErrorMessage,
  newCharacter,
  updateCharacter,
  type Character,
  type Options,
  type Project,
} from "../../api/client";
import { ErrorMessage, LoadingMessage } from "../../components/Messages";
import { SaveStatus } from "../../components/SaveStatus";
import { StepHeader } from "../../components/StepHeader";
import { PRIMARY_BUTTON, SECONDARY_BUTTON } from "../../components/styles";
import { useCharacterList } from "../../hooks/useCharacterList";
import { useOptions } from "../../hooks/useOptions";
import { useProject } from "../../hooks/useProject";
import { useScriptValidation } from "../../hooks/useScriptValidation";
import { capitalize } from "../../lib/format";
import { navigateTo, ROUTES, type ProjectStep } from "../../routes";
import { CharacterBuilder } from "../character-builder/CharacterBuilder";
import { SpeakerChoicePanel } from "./SpeakerChoicePanel";
import { SpeakerList } from "./SpeakerList";
import { useCastDraft } from "./useCastDraft";

type CastEditorProps = {
  project: Project;
  options: Options;
  speakers: string[];
};

function CastEditor({ project, options, speakers }: CastEditorProps) {
  const { cast, setCastEntry, saveCastEntryNow, hasUnsavedChanges, saveError, saveUnsavedChanges } =
    useCastDraft(project);
  const { characters, charactersError, reloadCharacters } = useCharacterList();
  const [selectedSpeaker, setSelectedSpeaker] = useState<string | null>(null);
  const [isPickingFromLibrary, setIsPickingFromLibrary] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [isContinuing, setIsContinuing] = useState(false);
  const [continueError, setContinueError] = useState<string | null>(null);

  const activeSpeaker = selectedSpeaker ?? speakers[0];
  const activeEntry = cast[activeSpeaker];
  const isChoosingCharacter = !activeEntry || isPickingFromLibrary;
  const hasEveryCharacter = speakers.every((speaker) => Boolean(cast[speaker]));
  const usedVoiceIds = speakers
    .filter((speaker) => speaker !== activeSpeaker && cast[speaker])
    .map((speaker) => cast[speaker].character.voice.voice_id);

  const handleSpeakerSelect = (speaker: string) => {
    setSelectedSpeaker(speaker);
    setIsPickingFromLibrary(false);
    setCreateError(null);
  };

  const handleLibraryCharacterPick = (character: Character) => {
    setCastEntry(activeSpeaker, { character, library_id: character.id ?? null });
    setIsPickingFromLibrary(false);
  };

  const handleCreateNewClick = async () => {
    setIsCreating(true);
    setCreateError(null);
    try {
      const character = await newCharacter({ name: capitalize(activeSpeaker) });
      setCastEntry(activeSpeaker, { character, library_id: null });
      setIsPickingFromLibrary(false);
    } catch (error) {
      setCreateError(getErrorMessage(error));
    } finally {
      setIsCreating(false);
    }
  };

  const handleCharacterChange = (character: Character) => {
    setCastEntry(activeSpeaker, { ...activeEntry, character });
  };

  // Updates the library copy if this speaker came from the library, otherwise adds a new one.
  const handleSaveToLibrary = async () => {
    let savedCharacter: Character;
    if (activeEntry.library_id) {
      savedCharacter = await updateCharacter(activeEntry.library_id, activeEntry.character);
    } else {
      savedCharacter = await createCharacter(activeEntry.character);
    }
    await saveCastEntryNow(activeSpeaker, { character: savedCharacter, library_id: savedCharacter.id ?? null });
    reloadCharacters();
    return savedCharacter;
  };

  const handleContinueClick = async (nextStep: ProjectStep) => {
    setIsContinuing(true);
    setContinueError(null);
    const isSaved = await saveUnsavedChanges();
    if (isSaved) {
      navigateTo(ROUTES.projectStep(project.id, nextStep));
      return;
    }
    setContinueError("The cast isn’t saved yet. Try again.");
    setIsContinuing(false);
  };

  const isContinueDisabled = !hasEveryCharacter || isContinuing;

  return (
    <div className="flex max-w-[1120px] flex-col gap-6">
      <StepHeader
        title={project.title}
        activeStep={2}
        statusText={<SaveStatus hasUnsavedChanges={hasUnsavedChanges} saveError={saveError} />}
      />

      <div className="flex flex-wrap items-start gap-5">
        <SpeakerList
          speakers={speakers}
          cast={cast}
          activeSpeaker={activeSpeaker}
          onSpeakerSelect={handleSpeakerSelect}
          onPickFromLibraryClick={() => setIsPickingFromLibrary(true)}
        />

        {isChoosingCharacter && (
          <SpeakerChoicePanel
            speaker={activeSpeaker}
            libraryCharacters={characters}
            charactersError={charactersError}
            isCreating={isCreating}
            createError={createError}
            canCancel={Boolean(activeEntry)}
            onLibraryCharacterPick={handleLibraryCharacterPick}
            onCreateNewClick={handleCreateNewClick}
            onCancelClick={() => setIsPickingFromLibrary(false)}
          />
        )}

        {!isChoosingCharacter && (
          <CharacterBuilder
            key={activeSpeaker}
            character={activeEntry.character}
            options={options}
            usedVoiceIds={usedVoiceIds}
            onCharacterChange={handleCharacterChange}
            onSave={handleSaveToLibrary}
          />
        )}
      </div>

      <div className="flex flex-col items-end gap-2 border-t border-line pt-5">
        <div className="flex flex-wrap justify-end gap-2.5">
          <button
            type="button"
            className={`${SECONDARY_BUTTON} min-h-[46px]`}
            disabled={isContinueDisabled}
            onClick={() => handleContinueClick("render")}
          >
            Skip storyboard and render
          </button>
          <button
            type="button"
            className={`${PRIMARY_BUTTON} min-h-[46px]`}
            disabled={isContinueDisabled}
            onClick={() => handleContinueClick("storyboard")}
          >
            Continue to storyboard
          </button>
        </div>
        {!hasEveryCharacter && <p className="m-0 text-sm text-muted">Give every speaker a character to continue.</p>}
        <ErrorMessage message={continueError} />
      </div>
    </div>
  );
}

function CastSpeakersLoader({ project, options }: { project: Project; options: Options }) {
  const { validation, validationError } = useScriptValidation(project.script);

  if (validationError) return <ErrorMessage message={validationError} />;
  if (!validation) return <LoadingMessage />;
  if (validation.speakers.length === 0) {
    return (
      <div className="flex max-w-[1120px] flex-col gap-6">
        <StepHeader title={project.title} activeStep={2} />
        <p className="m-0 text-[15px] text-muted">
          No speakers found in the script. <a href={ROUTES.projectStep(project.id, "script")}>Go back to the script</a>.
        </p>
      </div>
    );
  }
  return <CastEditor project={project} options={options} speakers={validation.speakers} />;
}

export function CastScreen({ projectId }: { projectId: string }) {
  const { project, projectError } = useProject(projectId);
  const { options, optionsError } = useOptions();

  if (projectError || optionsError) return <ErrorMessage message={projectError ?? optionsError} />;
  if (!project || !options) return <LoadingMessage />;
  return <CastSpeakersLoader project={project} options={options} />;
}
