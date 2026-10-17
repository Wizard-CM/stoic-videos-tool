import { useEffect, useState } from "react";
import { getErrorMessage, renderCharacterPreview, type Character } from "../../api/client";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";

const PREVIEW_DELAY_MS = 150;

// Re-renders the engine preview shortly after the character or emotion changes.
export function useCharacterPreview(character: Character, emotion: string) {
  const debouncedCharacter = useDebouncedValue(character, PREVIEW_DELAY_MS);
  const debouncedEmotion = useDebouncedValue(emotion, PREVIEW_DELAY_MS);
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;
    let createdImageUrl: string | null = null;

    renderCharacterPreview(debouncedCharacter, debouncedEmotion)
      .then((imageBlob) => {
        if (isCancelled) return;
        createdImageUrl = URL.createObjectURL(imageBlob);
        setPreviewImageUrl(createdImageUrl);
        setPreviewError(null);
      })
      .catch((error) => {
        if (!isCancelled) setPreviewError(getErrorMessage(error));
      });

    return () => {
      isCancelled = true;
      if (createdImageUrl) URL.revokeObjectURL(createdImageUrl);
    };
  }, [debouncedCharacter, debouncedEmotion]);

  return { previewImageUrl, previewError };
}
