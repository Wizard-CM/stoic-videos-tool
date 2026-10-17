import { useState } from "react";

type PreviewImageProps = {
  src: string;
  alt: string;
  // Size and aspect classes for the frame, e.g. "aspect-[4/5]".
  className?: string;
  loadingText?: string;
};

// An engine-rendered image with "Drawing…" while it loads and a note if it fails.
export function PreviewImage({ src, alt, className = "", loadingText = "Drawing…" }: PreviewImageProps) {
  const [loadedSrc, setLoadedSrc] = useState<string | null>(null);
  const [failedSrc, setFailedSrc] = useState<string | null>(null);

  const hasFailed = failedSrc === src;
  const isLoading = loadedSrc !== src && !hasFailed;

  return (
    <div className={`relative overflow-hidden rounded-xl bg-placeholder ${className}`}>
      {!hasFailed && (
        <img
          src={src}
          alt={alt}
          onLoad={() => setLoadedSrc(src)}
          onError={() => setFailedSrc(src)}
          className="block h-full w-full object-contain"
        />
      )}
      {isLoading && (
        <span className="absolute top-3 left-3 rounded-full bg-surface px-2.5 py-1 text-[12.5px] text-muted">
          {loadingText}
        </span>
      )}
      {hasFailed && (
        <p className="absolute inset-0 m-0 flex items-center justify-center p-4 text-center text-sm text-muted">
          Couldn’t load this image.
        </p>
      )}
    </div>
  );
}
