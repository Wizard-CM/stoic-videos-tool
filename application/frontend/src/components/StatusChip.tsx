export type ChipTone = "ready" | "draft" | "busy" | "warning" | "failed";

const TONE_CLASSES: Record<ChipTone, string> = {
  ready: "bg-success-soft text-success",
  draft: "bg-chip text-chip-ink",
  busy: "bg-accent-soft text-accent-dark",
  warning: "bg-warning-soft text-warning-icon",
  failed: "bg-danger-soft text-danger",
};

type StatusChipProps = {
  label: string;
  tone: ChipTone;
};

export function StatusChip({ label, tone }: StatusChipProps) {
  return (
    <span className={`flex-none rounded-full px-2.5 py-[3px] text-[12.5px] font-medium ${TONE_CLASSES[tone]}`}>
      {label}
    </span>
  );
}
