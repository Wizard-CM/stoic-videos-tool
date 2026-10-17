type ProgressBarProps = {
  percent: number;
  label: string;
};

export function ProgressBar({ percent, label }: ProgressBarProps) {
  const roundedPercent = Math.round(percent);

  return (
    <div
      role="progressbar"
      aria-valuenow={roundedPercent}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
      className="h-2.5 overflow-hidden rounded-[5px] bg-track"
    >
      <div className="h-full bg-accent" style={{ width: `${roundedPercent}%` }} />
    </div>
  );
}
