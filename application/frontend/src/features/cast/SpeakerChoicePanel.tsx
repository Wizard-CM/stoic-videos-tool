import { getCharacterAvatarUrl, type Character } from "../../api/client";
import { ErrorMessage, LoadingMessage } from "../../components/Messages";
import { PRIMARY_BUTTON, SECONDARY_BUTTON } from "../../components/styles";

const AVATAR_SIZE = 96;

type SpeakerChoicePanelProps = {
  speaker: string;
  libraryCharacters: Character[] | null;
  charactersError: string | null;
  isCreating: boolean;
  createError: string | null;
  canCancel: boolean;
  onLibraryCharacterPick: (character: Character) => void;
  onCreateNewClick: () => void;
  onCancelClick: () => void;
};

function LibraryCharacterGrid({
  libraryCharacters,
  onLibraryCharacterPick,
}: Pick<SpeakerChoicePanelProps, "libraryCharacters" | "onLibraryCharacterPick">) {
  if (libraryCharacters === null) return <LoadingMessage />;
  if (libraryCharacters.length === 0) {
    return <p className="m-0 text-sm text-muted">Your library is empty. Create a new character instead.</p>;
  }

  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(140px,1fr))] gap-3">
      {libraryCharacters.map((character) => (
        <button
          key={character.id}
          type="button"
          onClick={() => onLibraryCharacterPick(character)}
          className="flex min-h-11 flex-col items-center gap-2 rounded-[10px] border border-line bg-surface p-3"
        >
          <img
            src={getCharacterAvatarUrl(character.id ?? "", AVATAR_SIZE, character.updated_at)}
            alt=""
            className="size-16 rounded-full bg-placeholder object-cover"
          />
          <span className="text-[14.5px] font-semibold text-ink">{character.name}</span>
        </button>
      ))}
    </div>
  );
}

export function SpeakerChoicePanel({
  speaker,
  libraryCharacters,
  charactersError,
  isCreating,
  createError,
  canCancel,
  onLibraryCharacterPick,
  onCreateNewClick,
  onCancelClick,
}: SpeakerChoicePanelProps) {
  return (
    <section
      aria-label="Choose a character"
      className="flex min-w-0 flex-[999_1_680px] flex-col gap-5 rounded-xl border border-line bg-surface p-5"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="m-0 text-[17px] font-semibold">Choose a character for {speaker}</h2>
        <div className="flex gap-2">
          {canCancel && (
            <button type="button" className={SECONDARY_BUTTON} onClick={onCancelClick}>
              Cancel
            </button>
          )}
          <button type="button" className={PRIMARY_BUTTON} disabled={isCreating} onClick={onCreateNewClick}>
            Create new
          </button>
        </div>
      </div>
      <ErrorMessage message={createError} />

      <div className="flex flex-col gap-3">
        <h3 className="m-0 text-[15px] font-semibold">Pick from library</h3>
        <ErrorMessage message={charactersError} />
        <LibraryCharacterGrid libraryCharacters={libraryCharacters} onLibraryCharacterPick={onLibraryCharacterPick} />
      </div>
    </section>
  );
}
