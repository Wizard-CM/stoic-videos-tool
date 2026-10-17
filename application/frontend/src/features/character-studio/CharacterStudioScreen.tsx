import { useEffect, useState } from "react";
import { getCharacter, getErrorMessage, type Character, type Options } from "../../api/client";
import { ErrorMessage, LoadingMessage } from "../../components/Messages";
import { PageHeader } from "../../components/PageHeader";
import { useOptions } from "../../hooks/useOptions";
import { SLOT_KEYS } from "../../lib/taskSlots";
import { navigateTo, ROUTES } from "../../routes";
import { CharacterDesignForm } from "./CharacterDesignForm";
import { CharacterEditor } from "./CharacterEditor";

function NewCharacterStudio({ options }: { options: Options }) {
  return (
    <div className="flex max-w-[860px] flex-col gap-6">
      <PageHeader parentLabel="Library" parentHref={ROUTES.library("characters")} title="Design a character" />
      <p className="m-0 text-[15px] text-muted">
        Describe who you want and Claude designs a complete cartoon puppet you can reuse in any video.
      </p>
      <CharacterDesignForm
        slotKey={SLOT_KEYS.newCharacter}
        options={options}
        heading="Your character"
        onCreated={(characterId) => navigateTo(ROUTES.editCharacter(characterId))}
      />
    </div>
  );
}

function SavedCharacterStudio({ characterId, options }: { characterId: string; options: Options }) {
  const [character, setCharacter] = useState<Character | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    getCharacter(characterId)
      .then(setCharacter)
      .catch((error) => setLoadError(getErrorMessage(error)));
  }, [characterId]);

  if (loadError) return <ErrorMessage message={loadError} />;
  if (!character) return <LoadingMessage />;
  return <CharacterEditor initialCharacter={character} options={options} />;
}

// `characterId` is null for #/characters/new.
export function CharacterStudioScreen({ characterId }: { characterId: string | null }) {
  const { options, optionsError } = useOptions();

  if (optionsError) return <ErrorMessage message={optionsError} />;
  if (!options) return <LoadingMessage />;
  if (characterId === null) return <NewCharacterStudio options={options} />;
  return <SavedCharacterStudio characterId={characterId} options={options} />;
}
