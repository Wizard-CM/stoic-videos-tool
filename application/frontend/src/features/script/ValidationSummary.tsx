import type { ScriptIssue, ScriptValidation } from "../../api/client";
import { ErrorIcon, WarningIcon } from "../../components/icons";
import { pluralize } from "../../lib/format";

type ValidationSummaryProps = {
  validation: ScriptValidation | null;
  validationError: string | null;
};

function getIssueCountText(errorCount: number, warningCount: number) {
  const errorText = errorCount === 0 ? "No errors" : pluralize(errorCount, "error");
  const warningText = warningCount === 0 ? "no warnings" : pluralize(warningCount, "warning");
  return `${errorText}, ${warningText}.`;
}

function IssueRow({ issue }: { issue: ScriptIssue }) {
  const issueText = issue.line_no === null ? issue.message : `Line ${issue.line_no}: ${issue.message}`;

  if (issue.level === "error") {
    return (
      <div className="flex items-start gap-2.5 rounded-lg bg-danger-soft px-3 py-2.5">
        <ErrorIcon />
        <p className="m-0 text-sm text-danger-ink">{issueText}</p>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2.5 rounded-lg bg-warning-soft px-3 py-2.5">
      <WarningIcon />
      <p className="m-0 text-sm text-warning-ink">{issueText}</p>
    </div>
  );
}

function ValidationText({ validation, validationError }: ValidationSummaryProps) {
  if (validationError) return <p className="m-0 text-sm text-danger">Couldn’t check the script: {validationError}</p>;
  if (!validation) return <p className="m-0 text-[14.5px] text-muted">Checking script…</p>;

  return (
    <p className="m-0 text-[14.5px]">
      <strong className="font-semibold">
        {pluralize(validation.lines.length, "line")}, {pluralize(validation.speakers.length, "speaker")}
      </strong>{" "}
      <span className="text-muted">
        {validation.speakers.length > 0 && `(${validation.speakers.join(", ")}). `}
        {getIssueCountText(validation.error_count, validation.warning_count)}
      </span>
    </p>
  );
}

export function ValidationSummary({ validation, validationError }: ValidationSummaryProps) {
  return (
    <div role="status" className="flex flex-col gap-2.5 rounded-[10px] border border-line bg-surface px-4 py-3.5">
      <ValidationText validation={validation} validationError={validationError} />
      {validation?.issues.map((issue, index) => (
        <IssueRow key={`${issue.line_no}-${index}`} issue={issue} />
      ))}
    </div>
  );
}
