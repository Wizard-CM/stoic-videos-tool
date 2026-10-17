// Shared Tailwind class strings so buttons and fields look the same on every screen.

const BASE_BUTTON =
  "inline-flex items-center justify-center gap-2 min-h-11 px-[18px] rounded-lg text-[15px] no-underline disabled:cursor-not-allowed disabled:opacity-50";

export const PRIMARY_BUTTON = `${BASE_BUTTON} bg-accent font-semibold text-white hover:bg-accent-dark hover:text-white`;

export const SECONDARY_BUTTON = `${BASE_BUTTON} border border-field bg-surface font-medium text-ink hover:text-ink`;

export const DARK_BUTTON = `${BASE_BUTTON} bg-ink font-semibold text-white hover:text-white`;

export const DANGER_BUTTON = `${BASE_BUTTON} border border-danger-line bg-surface font-medium text-danger hover:text-danger`;

export const LINK_BUTTON = "min-h-11 px-1 text-left text-sm text-accent hover:text-accent-dark";

export const FIELD_LABEL = "text-sm font-medium";

export const TEXT_INPUT =
  "min-h-[42px] rounded-lg border border-field bg-surface px-3 text-[15px] text-ink";

export const SELECT_INPUT =
  "min-h-[42px] rounded-lg border border-field bg-surface px-2.5 text-[15px] text-ink";

export const RANGE_INPUT = "min-h-7 w-full accent-accent";

export const SURFACE_CARD = "rounded-xl border border-line bg-surface";

// Video frames follow the project's aspect ratio ("16:9" or "9:16").
export function getAspectClass(aspect: string) {
  if (aspect === "9:16") return "mx-auto aspect-[9/16] max-h-[70vh]";
  return "aspect-video";
}
