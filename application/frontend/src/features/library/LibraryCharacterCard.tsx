import { useState } from "react";
import {
  deleteCharacter,
  getCharacterAvatarUrl,
  getCharacterExportUrl,
  getErrorMessage,
  type Character,
} from "../../api/client";
import { ErrorMessage } from "../../components/Messages";
import { SECONDARY_BUTTON } from "../../components/styles";
import { ROUTES } from "../../routes";

const AVATAR_SIZE = 192;
const CARD_BUTTON = `${SECONDARY_BUTTON} flex-1 px-3 text-sm`;

type LibraryCharacterCardProps = {
  character: Character;
  onCharactersChange: () => void;
};

export function LibraryCharacterCard({ character, onCharactersChange }: LibraryCharacterCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const characterId = character.id ?? "";

  const handleDeleteClick = async () => {
    const isConfirmed = window.confirm(`Delete “${character.name}” from the library? Projects keep their own copy.`);
    if (!isConfirmed) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await deleteCharacter(characterId);
      onCharactersChange();
    } catch (error) {
      setDeleteError(getErrorMessage(error));
      setIsDeleting(false);
    }
  };

  return (
    <article className="flex flex-col overflow-hidden rounded-xl border border-line bg-surface">
      <div className="aspect-square bg-placeholder">
        <img
          src={getCharacterAvatarUrl(characterId, AVATAR_SIZE, character.updated_at)}
          alt=""
          className="size-full object-cover"
        />
      </div>
      <div className="flex flex-col gap-1.5 px-4 pt-3.5 pb-4">
        <h2 className="m-0 text-base font-semibold">{character.name}</h2>
        {character.description && <p className="m-0 text-[13.5px] text-muted">{character.description}</p>}
        <div className="mt-2 flex gap-2">
          <a href={ROUTES.editCharacter(characterId)} className={CARD_BUTTON}>
            Edit
          </a>
          <a href={getCharacterExportUrl(characterId)} download className={CARD_BUTTON}>
            Export
          </a>
          <button type="button" className={CARD_BUTTON} disabled={isDeleting} onClick={handleDeleteClick}>
            Delete
          </button>
        </div>
        <ErrorMessage message={deleteError} />
      </div>
    </article>
  );
}
