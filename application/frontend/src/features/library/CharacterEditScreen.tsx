import { useEffect, useState } from "react";
import {
  createCharacter,
  getCharacter,
  getErrorMessage,
  newCharacter,
  updateCharacter,
  type Character,
} from "../../api/client";
import { ErrorMessage, LoadingMessage } from "../../components/Messages";
import { useOptions } from "../../hooks/useOptions";
import { navigateTo, ROUTES } from "../../routes";
import { CharacterBuilder } from "../character-builder/CharacterBuilder";

// `characterId` is null for #/characters/new.
export function CharacterEditScreen({ characterId }: { characterId: string | null }) {
  const { options, optionsError } = useOptions();
  const [character, setCharacter] = useState<Character | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    const loadCharacter = characterId ? getCharacter(characterId) : newCharacter({});
    loadCharacter.then(setCharacter).catch((error) => setLoadError(getErrorMessage(error)));
  }, [characterId]);

  const handleSave = async () => {
    if (!character) throw new Error("The character hasn’t loaded yet.");
    if (characterId) {
      const savedCharacter = await updateCharacter(characterId, character);
      setCharacter(savedCharacter);
      return savedCharacter;
    }
    const createdCharacter = await createCharacter(character);
    navigateTo(ROUTES.editCharacter(createdCharacter.id ?? ""));
    return createdCharacter;
  };

  if (loadError || optionsError) return <ErrorMessage message={loadError ?? optionsError} />;
  if (!character || !options) return <LoadingMessage />;

  const pageTitle = character.name || "New character";

  return (
    <div className="flex max-w-[1120px] flex-col gap-6">
      <header className="flex flex-col gap-3.5">
        <p className="m-0 text-sm text-muted">
          <a href={ROUTES.characters}>Characters</a> / {pageTitle}
        </p>
        <h1 className="m-0 text-[28px] font-semibold tracking-[-0.01em]">{pageTitle}</h1>
      </header>
      <div className="flex flex-wrap items-start gap-5">
        <CharacterBuilder
          character={character}
          options={options}
          usedVoiceIds={[]}
          onCharacterChange={setCharacter}
          onSave={handleSave}
        />
      </div>
    </div>
  );
}
