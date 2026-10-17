import { useEffect, useState } from "react";
import { getErrorMessage, testClaude, type ClaudeTestResult } from "../../api/client";
import { refreshClaudeStatus, useClaudeStatus } from "../../hooks/useClaudeStatus";
import { WarningIcon } from "../icons";
import { ErrorMessage } from "../Messages";
import { SECONDARY_BUTTON } from "../styles";

// Explains what to do when Claude Code isn't installed or signed in on this PC.
export function ClaudeStatusBanner() {
  const { status } = useClaudeStatus();
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<ClaudeTestResult | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  const isNotReady = status?.ready === false;

  // Re-check when the user comes back from setting Claude up in another window.
  useEffect(() => {
    if (!isNotReady) return;
    const handleFocus = () => refreshClaudeStatus();
    window.addEventListener("focus", handleFocus);
    return () => window.removeEventListener("focus", handleFocus);
  }, [isNotReady]);

  if (!status || !isNotReady) return null;

  const handleTestClick = async () => {
    setIsTesting(true);
    setTestError(null);
    setTestResult(null);
    try {
      setTestResult(await testClaude());
      await refreshClaudeStatus();
    } catch (error) {
      setTestError(getErrorMessage(error));
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <aside
      aria-label="Claude status"
      className="mb-6 flex max-w-[1120px] flex-wrap items-start gap-3 rounded-xl border border-line bg-warning-soft px-4 py-3.5"
    >
      <WarningIcon />
      <div className="flex min-w-0 flex-[1_1_320px] flex-col gap-1">
        <p className="m-0 text-[15px] font-semibold text-warning-ink">Claude isn’t ready on this PC</p>
        <p className="m-0 text-sm whitespace-pre-line text-warning-ink">{status.message}</p>
        {testResult && (
          <p role="status" className={`m-0 text-sm ${testResult.ok ? "text-success" : "text-danger"}`}>
            {testResult.message}
          </p>
        )}
        <ErrorMessage message={testError} />
      </div>
      <button type="button" className={SECONDARY_BUTTON} disabled={isTesting} onClick={handleTestClick}>
        {isTesting ? "Testing…" : "Test connection"}
      </button>
    </aside>
  );
}
