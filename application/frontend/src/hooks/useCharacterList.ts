import { useEffect, useState } from "react";
import { getErrorMessage, listCharacters, type Character } from "../api/client";

export function useCharacterList() {
  const [characters, setCharacters] = useState<Character[] | null>(null);
  const [charactersError, setCharactersError] = useState<string | null>(null);

  const reloadCharacters = async () => {
    try {
      setCharacters(await listCharacters());
      setCharactersError(null);
    } catch (error) {
      setCharactersError(getErrorMessage(error));
    }
  };

  useEffect(() => {
    reloadCharacters();
  }, []);

  return { characters, charactersError, reloadCharacters };
}
