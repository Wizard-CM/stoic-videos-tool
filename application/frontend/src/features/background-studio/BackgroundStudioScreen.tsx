import { useEffect, useState } from "react";
import { getBackground, getErrorMessage, type Background } from "../../api/client";
import { ErrorMessage, LoadingMessage } from "../../components/Messages";
import { PageHeader } from "../../components/PageHeader";
import { useCharacterList } from "../../hooks/useCharacterList";
import { SLOT_KEYS } from "../../lib/taskSlots";
import { navigateTo, ROUTES } from "../../routes";
import { BackgroundDesignForm } from "./BackgroundDesignForm";
import { BackgroundEditor } from "./BackgroundEditor";

function useSavedBackground(backgroundId: string | null) {
  const [background, setBackground] = useState<Background | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!backgroundId) return;
    getBackground(backgroundId)
      .then(setBackground)
      .catch((error) => setLoadError(getErrorMessage(error)));
  }, [backgroundId]);

  return { background, loadError };
}

// `backgroundId` is null for #/backgrounds/new.
export function BackgroundStudioScreen({ backgroundId }: { backgroundId: string | null }) {
  const { characters } = useCharacterList();
  const { background, loadError } = useSavedBackground(backgroundId);

  if (backgroundId === null) {
    return (
      <div className="flex max-w-[860px] flex-col gap-6">
        <PageHeader parentLabel="Library" parentHref={ROUTES.library("backgrounds")} title="Design a background" />
        <p className="m-0 text-[15px] text-muted">
          Describe a place and Claude paints a set you can reuse behind any character.
        </p>
        <BackgroundDesignForm
          slotKey={SLOT_KEYS.newBackground}
          heading="Your background"
          characters={characters}
          onCreated={(createdId) => navigateTo(ROUTES.editBackground(createdId))}
        />
      </div>
    );
  }

  if (loadError) return <ErrorMessage message={loadError} />;
  if (!background) return <LoadingMessage />;
  return <BackgroundEditor initialBackground={{ ...background, id: backgroundId }} characters={characters} />;
}
