import { PlusIcon } from "../../components/icons";
import { ErrorMessage, LoadingMessage } from "../../components/Messages";
import { PRIMARY_BUTTON } from "../../components/styles";
import { useBackgroundList } from "../../hooks/useBackgroundList";
import { ROUTES } from "../../routes";
import { LibraryBackgroundCard } from "./LibraryBackgroundCard";

export function BackgroundsTab() {
  const { backgrounds, backgroundsError, reloadBackgrounds } = useBackgroundList();

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="m-0 text-[15px] text-muted">Sets Claude painted, to put behind any character.</p>
        <a href={ROUTES.newBackground} className={PRIMARY_BUTTON}>
          <PlusIcon />
          Design a background
        </a>
      </div>

      <ErrorMessage message={backgroundsError} />
      {backgrounds === null && !backgroundsError && <LoadingMessage />}
      {backgrounds?.length === 0 && (
        <p className="m-0 text-[15px] text-muted">
          No backgrounds yet. Design one here, or let Claude design one for each video.
        </p>
      )}

      <div className="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-5">
        {backgrounds?.map((background) => (
          <LibraryBackgroundCard key={background.id} background={background} onBackgroundsChange={reloadBackgrounds} />
        ))}
      </div>
    </div>
  );
}
