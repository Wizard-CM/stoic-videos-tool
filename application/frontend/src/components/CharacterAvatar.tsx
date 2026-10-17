import { useState } from "react";
import { getCharacterAvatarUrl } from "../api/client";

type CharacterAvatarProps = {
  // The library character to draw; null shows the initial only.
  characterId: string | null;
  name: string;
  version?: string;
  // Tailwind size class, e.g. "size-9".
  sizeClass?: string;
};

const AVATAR_PIXELS = 96;

// A round head shot, falling back to the first letter when there's no image.
export function CharacterAvatar({ characterId, name, version = "", sizeClass = "size-9" }: CharacterAvatarProps) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const src = characterId ? getCharacterAvatarUrl(characterId, AVATAR_PIXELS, version) : null;

  if (!src || failedSrc === src) {
    return (
      <span
        aria-hidden="true"
        className={`inline-flex flex-none items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent-dark ${sizeClass}`}
      >
        {name.charAt(0).toUpperCase()}
      </span>
    );
  }

  return (
    <img
      src={src}
      alt=""
      onError={() => setFailedSrc(src)}
      className={`flex-none rounded-full bg-placeholder object-cover ${sizeClass}`}
    />
  );
}
