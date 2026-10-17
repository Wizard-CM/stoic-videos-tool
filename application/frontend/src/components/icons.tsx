// Inline SVG icons copied from the designs in docs/ui.

export function LogoIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true">
      <rect x="2" y="3" width="24" height="18" rx="6" fill="#2D55E0" />
      <path d="M8 20 L7 26 L14 20 Z" fill="#2D55E0" />
      <circle cx="10" cy="12" r="2" fill="#FFFFFF" />
      <circle cx="18" cy="12" r="2" fill="#FFFFFF" />
    </svg>
  );
}

export function ProjectsIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M10 9.5 L10 14.5 L14 12 Z" />
    </svg>
  );
}

export function PlusIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
      <path d="M12 5 L12 19 M5 12 L19 12" />
    </svg>
  );
}

export function PlayIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M7 4 L20 12 L7 20 Z" />
    </svg>
  );
}

export function RefreshIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3A3D45" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 12 A8 8 0 1 1 17.7 6.3" />
      <path d="M20 4 L20 9 L15 9" />
    </svg>
  );
}

export function WarningIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#8A3A08" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="mt-0.5 flex-none">
      <path d="M12 3 L22 20 L2 20 Z" />
      <path d="M12 10 L12 14 M12 17 L12 17.5" />
    </svg>
  );
}

export function ErrorIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#A1271B" strokeWidth="2" strokeLinecap="round" aria-hidden="true" className="mt-0.5 flex-none">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.5 L12 13 M12 16.5 L12 17" />
    </svg>
  );
}

export function DoneIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" className="flex-none">
      <circle cx="12" cy="12" r="10" fill="#E3F2E8" />
      <path d="M7.5 12.5 L10.5 15.5 L16.5 9" stroke="#1D6A40" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function ActiveIcon({ isSpinning = false, size = 20 }: { isSpinning?: boolean; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      className={`flex-none ${isSpinning ? "motion-safe:animate-spin" : ""}`}
    >
      <circle cx="12" cy="12" r="9" fill="none" stroke="#DCE3FA" strokeWidth="3" />
      <path d="M12 3 A9 9 0 0 1 21 12" fill="none" stroke="#2D55E0" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function WaitingIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" className="flex-none">
      <circle cx="12" cy="12" r="9" fill="none" stroke="#C9C9C1" strokeWidth="2" />
    </svg>
  );
}

export function FailedCheckIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" className="flex-none">
      <circle cx="12" cy="12" r="10" fill="#FCEBE9" />
      <path d="M8.5 8.5 L15.5 15.5 M15.5 8.5 L8.5 15.5" stroke="#A1271B" strokeWidth="2" fill="none" strokeLinecap="round" />
    </svg>
  );
}

export function SparkleIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className="flex-none">
      <path d="M12 2 C12.8 7.5 16.5 11.2 22 12 C16.5 12.8 12.8 16.5 12 22 C11.2 16.5 7.5 12.8 2 12 C7.5 11.2 11.2 7.5 12 2 Z" />
    </svg>
  );
}

export function LibraryIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="9" cy="8" r="3.5" />
      <path d="M3 19 C4.2 15.5 6.4 14 9 14 C11.6 14 13.8 15.5 15 19" />
      <rect x="14.5" y="4" width="7" height="6" rx="1.5" />
    </svg>
  );
}
