import { getBackgroundPreviewUrl, type BackgroundSummary } from "../../api/client";
import { LoadingMessage } from "../../components/Messages";

const THUMBNAIL_WIDTH = 320;
const SELECTED_CARD = "border-[1.5px] border-accent bg-accent-tint";
const UNSELECTED_CARD = "border border-line bg-surface";

type LibraryBackgroundPickerProps = {
  backgrounds: BackgroundSummary[] | null;
  selectedId: string | null;
  isBusy: boolean;
  onPick: (backgroundId: string) => void;
};

export function LibraryBackgroundPicker({ backgrounds, selectedId, isBusy, onPick }: LibraryBackgroundPickerProps) {
  if (backgrounds === null) return <LoadingMessage />;
  if (backgrounds.length === 0) {
    return <p className="m-0 text-sm text-muted">No backgrounds in your library yet. Design one instead.</p>;
  }

  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(170px,1fr))] gap-3">
      {backgrounds.map((background) => (
        <button
          key={background.id}
          type="button"
          aria-pressed={background.id === selectedId}
          disabled={isBusy}
          onClick={() => onPick(background.id)}
          className={`flex min-h-11 flex-col overflow-hidden rounded-[10px] text-left disabled:opacity-60 ${background.id === selectedId ? SELECTED_CARD : UNSELECTED_CARD}`}
        >
          <img
            src={getBackgroundPreviewUrl(background.id, { width: THUMBNAIL_WIDTH, version: background.updated_at })}
            alt=""
            className="block aspect-video w-full bg-placeholder object-cover"
          />
          <span className="px-3 py-2 text-[14px] font-semibold text-ink">{background.name}</span>
        </button>
      ))}
    </div>
  );
}
