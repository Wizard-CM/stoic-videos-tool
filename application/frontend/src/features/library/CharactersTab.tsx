import { useRef, useState, type ChangeEvent } from "react";
import { getErrorMessage, importCharacter } from "../../api/client";
import { PlusIcon } from "../../components/icons";
import { ErrorMessage, LoadingMessage } from "../../components/Messages";
import { PRIMARY_BUTTON, SECONDARY_BUTTON } from "../../components/styles";
import { useCharacterList } from "../../hooks/useCharacterList";
import { ROUTES } from "../../routes";
import { LibraryCharacterCard } from "./LibraryCharacterCard";

async function readJsonFile(file: File): Promise<unknown> {
  try {
    return JSON.parse(await file.text());
  } catch {
    throw new Error("That file isn’t valid character JSON.");
  }
}

export function CharactersTab() {
  const { characters, charactersError, reloadCharacters } = useCharacterList();
  const importInputRef = useRef<HTMLInputElement>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  const handleImportFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    event.target.value = "";
    if (!selectedFile) return;

    setIsImporting(true);
    setImportError(null);
    try {
      await importCharacter(await readJsonFile(selectedFile));
      await reloadCharacters();
    } catch (error) {
      setImportError(getErrorMessage(error));
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="m-0 text-[15px] text-muted">Characters Claude designed for you, ready for any video.</p>
        <div className="flex flex-col items-end gap-1.5">
          <div className="flex flex-wrap gap-2.5">
            <button
              type="button"
              className={SECONDARY_BUTTON}
              disabled={isImporting}
              onClick={() => importInputRef.current?.click()}
            >
              {isImporting ? "Importing…" : "Import JSON"}
            </button>
            <input
              ref={importInputRef}
              type="file"
              accept="application/json,.json"
              aria-label="Character JSON file"
              onChange={handleImportFileChange}
              className="hidden"
            />
            <a href={ROUTES.newCharacter} className={PRIMARY_BUTTON}>
              <PlusIcon />
              Design a character
            </a>
          </div>
          <ErrorMessage message={importError} />
        </div>
      </div>

      <ErrorMessage message={charactersError} />
      {characters === null && !charactersError && <LoadingMessage />}
      {characters?.length === 0 && (
        <p className="m-0 text-[15px] text-muted">
          No characters yet. Design one here, or from a project’s cast step.
        </p>
      )}

      <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-5">
        {characters?.map((character) => (
          <LibraryCharacterCard key={character.id} character={character} onCharactersChange={reloadCharacters} />
        ))}
      </div>
    </div>
  );
}
