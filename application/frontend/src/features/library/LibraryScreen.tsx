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

export function LibraryScreen() {
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
    <div className="flex max-w-[1040px] flex-col gap-7">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <h1 className="m-0 text-[30px] font-semibold tracking-[-0.01em]">Characters</h1>
          <p className="m-0 text-[15px] text-muted">Saved characters you can reuse in any video.</p>
        </div>
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
              New character
            </a>
          </div>
          <ErrorMessage message={importError} />
        </div>
      </div>

      <ErrorMessage message={charactersError} />
      {characters === null && !charactersError && <LoadingMessage />}
      {characters?.length === 0 && (
        <p className="m-0 text-[15px] text-muted">No saved characters yet. Make one here or save one from a project’s cast.</p>
      )}

      <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-5">
        {characters?.map((character) => (
          <LibraryCharacterCard key={character.id} character={character} onCharactersChange={reloadCharacters} />
        ))}
      </div>
    </div>
  );
}
