import { useClaudeStatus } from "../../hooks/useClaudeStatus";
import { SparkleIcon } from "../icons";
import { PRIMARY_BUTTON } from "../styles";

type ClaudeButtonProps = {
  label: string;
  busyLabel?: string;
  isBusy?: boolean;
  disabled?: boolean;
  // Why the button is disabled (other than Claude not being ready), shown as a tooltip.
  disabledReason?: string;
  onClick: () => void;
};

// The primary "… with Claude" button. Disabled, with the reason, while Claude isn't ready on this PC.
export function ClaudeButton({ label, busyLabel, isBusy = false, disabled = false, disabledReason, onClick }: ClaudeButtonProps) {
  const { isReady, notReadyMessage } = useClaudeStatus();

  return (
    <div className="flex flex-col items-start gap-1.5">
      <button
        type="button"
        className={PRIMARY_BUTTON}
        disabled={!isReady || disabled || isBusy}
        title={notReadyMessage ?? (disabled ? disabledReason : undefined)}
        onClick={onClick}
      >
        <SparkleIcon />
        {isBusy ? (busyLabel ?? label) : label}
      </button>
      {!isReady && (
        <p className="m-0 text-[13px] text-muted">Claude isn’t ready yet. See the notice at the top of the page.</p>
      )}
    </div>
  );
}
