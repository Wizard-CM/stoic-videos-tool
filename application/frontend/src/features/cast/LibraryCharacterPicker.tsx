import type { CharacterSummary } from "../../api/client";
import { CharacterAvatar } from "../../components/CharacterAvatar";
import { LoadingMessage } from "../../components/Messages";

const SELECTED_CARD = "border-[1.5px] border-accent bg-accent-tint";
const UNSELECTED_CARD = "border border-line bg-surface";

type LibraryCharacterPickerProps = {
  characters: CharacterSummary[] | null;
  selectedId: string | null;
  isBusy: boolean;
  onPick: (characterId: string) => void;
};

export function LibraryCharacterPicker({ characters, selectedId, isBusy, onPick }: LibraryCharacterPickerProps) {
  if (characters === null) return <LoadingMessage />;
  if (characters.length === 0) {
    return <p className="m-0 text-sm text-muted">Your library is empty. Design a new character instead.</p>;
  }

  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-3">
      {characters.map((character) => (
        <button
          key={character.id}
          type="button"
          aria-pressed={character.id === selectedId}
          disabled={isBusy}
          onClick={() => onPick(character.id)}
          className={`flex min-h-11 flex-col items-center gap-2 rounded-[10px] p-3 disabled:opacity-60 ${character.id === selectedId ? SELECTED_CARD : UNSELECTED_CARD}`}
        >
          <CharacterAvatar
            characterId={character.id}
            name={character.name}
            version={character.updated_at}
            sizeClass="size-16"
          />
          <span className="text-[14.5px] font-semibold text-ink">{character.name}</span>
          {character.description && (
            <span className="line-clamp-2 text-center text-[12.5px] text-muted">{character.description}</span>
          )}
        </button>
      ))}
    </div>
  );
}
