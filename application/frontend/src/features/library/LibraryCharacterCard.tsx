import { useState } from "react";
import {
  deleteCharacter,
  getCharacterAvatarUrl,
  getCharacterExportUrl,
  getErrorMessage,
  type CharacterSummary,
} from "../../api/client";
import { ErrorMessage } from "../../components/Messages";
import { SECONDARY_BUTTON } from "../../components/styles";
import { ROUTES } from "../../routes";

const AVATAR_SIZE = 192;
const CARD_BUTTON = `${SECONDARY_BUTTON} flex-1 px-3 text-sm`;

type LibraryCharacterCardProps = {
  character: CharacterSummary;
  onCharactersChange: () => void;
};

export function LibraryCharacterCard({ character, onCharactersChange }: LibraryCharacterCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDeleteClick = async () => {
    const isConfirmed = window.confirm(`Delete “${character.name}” from the library? Projects keep their own copy.`);
    if (!isConfirmed) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await deleteCharacter(character.id);
      onCharactersChange();
    } catch (error) {
      setDeleteError(getErrorMessage(error));
      setIsDeleting(false);
    }
  };

  return (
    <article className="flex flex-col overflow-hidden rounded-xl border border-line bg-surface">
      <a href={ROUTES.editCharacter(character.id)} tabIndex={-1} aria-hidden="true" className="block aspect-square bg-placeholder">
        <img
          src={getCharacterAvatarUrl(character.id, AVATAR_SIZE, character.updated_at)}
          alt=""
          className="size-full object-cover"
        />
      </a>
      <div className="flex flex-1 flex-col gap-1.5 px-4 pt-3.5 pb-4">
        <h2 className="m-0 text-base font-semibold">{character.name}</h2>
        {character.description && (
          <p className="m-0 line-clamp-3 text-[13.5px] text-muted">{character.description}</p>
        )}
        <div className="mt-auto flex gap-2 pt-2">
          <a href={ROUTES.editCharacter(character.id)} className={CARD_BUTTON}>
            Edit
          </a>
          <a href={getCharacterExportUrl(character.id)} download className={CARD_BUTTON}>
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
