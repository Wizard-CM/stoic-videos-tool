import { useState } from "react";
import { deleteBackground, getBackgroundPreviewUrl, getErrorMessage, type BackgroundSummary } from "../../api/client";
import { ErrorMessage } from "../../components/Messages";
import { SECONDARY_BUTTON } from "../../components/styles";
import { ROUTES } from "../../routes";

const PREVIEW_WIDTH = 480;
const CARD_BUTTON = `${SECONDARY_BUTTON} flex-1 px-3 text-sm`;

type LibraryBackgroundCardProps = {
  background: BackgroundSummary;
  onBackgroundsChange: () => void;
};

export function LibraryBackgroundCard({ background, onBackgroundsChange }: LibraryBackgroundCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDeleteClick = async () => {
    const isConfirmed = window.confirm(`Delete “${background.name}” from the library? Projects keep their own copy.`);
    if (!isConfirmed) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await deleteBackground(background.id);
      onBackgroundsChange();
    } catch (error) {
      setDeleteError(getErrorMessage(error));
      setIsDeleting(false);
    }
  };

  return (
    <article className="flex flex-col overflow-hidden rounded-xl border border-line bg-surface">
      <a href={ROUTES.editBackground(background.id)} tabIndex={-1} aria-hidden="true" className="block aspect-video bg-placeholder">
        <img
          src={getBackgroundPreviewUrl(background.id, { width: PREVIEW_WIDTH, version: background.updated_at })}
          alt=""
          className="size-full object-cover"
        />
      </a>
      <div className="flex flex-1 flex-col gap-1.5 px-4 pt-3.5 pb-4">
        <h2 className="m-0 text-base font-semibold">{background.name}</h2>
        {background.description && (
          <p className="m-0 line-clamp-3 text-[13.5px] text-muted">{background.description}</p>
        )}
        <div className="mt-auto flex gap-2 pt-2">
          <a href={ROUTES.editBackground(background.id)} className={CARD_BUTTON}>
            Edit
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
