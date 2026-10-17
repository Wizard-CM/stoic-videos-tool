import { DoneIcon, FailedCheckIcon } from "../../components/icons";
import { ErrorMessage, LoadingMessage } from "../../components/Messages";
import { PRIMARY_BUTTON } from "../../components/styles";
import { usePreflight } from "./usePreflight";

type RenderSetupProps = {
  projectId: string;
  isStarting: boolean;
  startError: string | null;
  onStartClick: () => void;
};

// Preflight checklist shown before the first render.
export function RenderSetup({ projectId, isStarting, startError, onStartClick }: RenderSetupProps) {
  const { preflight, preflightError } = usePreflight(projectId);

  if (preflightError) return <ErrorMessage message={preflightError} />;
  if (!preflight) return <LoadingMessage text="Checking everything is ready…" />;

  return (
    <section aria-label="Preflight check" className="flex flex-col rounded-xl border border-line bg-surface py-2">
      <h2 className="m-0 px-5 pt-3.5 pb-2 text-base font-semibold">Before rendering</h2>
      <ul className="m-0 list-none p-0">
        {preflight.checks.map((check) => (
          <li key={check.key} className="flex min-h-[46px] items-center gap-3 border-t border-divider px-5 py-2">
            {check.ok ? <DoneIcon /> : <FailedCheckIcon />}
            <span className="flex-1 text-[15px] text-ink-soft">{check.label}</span>
            <span className={`text-[13.5px] ${check.ok ? "text-muted" : "text-danger"}`}>{check.message}</span>
          </li>
        ))}
      </ul>
      <div className="flex flex-col items-start gap-2 border-t border-divider px-5 pt-4 pb-3">
        <button
          type="button"
          className={`${PRIMARY_BUTTON} min-h-[46px]`}
          disabled={!preflight.ok || isStarting}
          onClick={onStartClick}
        >
          Start render
        </button>
        {!preflight.ok && <p className="m-0 text-sm text-muted">Fix the items above to start rendering.</p>}
        <ErrorMessage message={startError} />
      </div>
    </section>
  );
}
