import type { ScriptIssue } from "../../api/client";

const MIN_VISIBLE_ROWS = 12;

const SCRIPT_PLACEHOLDER = `JADE [angry]: You knew about this the whole time!
RON [smug]: Of course I did.
JADE [shocked, 0.8]: And you said nothing?
RON: Nobody asked.`;

type ScriptBoxProps = {
  script: string;
  issues: ScriptIssue[];
  onScriptChange: (script: string) => void;
};

function getLineNumberClass(lineNumber: number, issues: ScriptIssue[]) {
  const lineIssues = issues.filter((issue) => issue.line_no === lineNumber);
  if (lineIssues.some((issue) => issue.level === "error")) return "font-semibold text-danger";
  if (lineIssues.length > 0) return "font-semibold text-warning-icon";
  return "";
}

// A plain textarea that grows with the script, next to a line-number gutter.
export function ScriptBox({ script, issues, onScriptChange }: ScriptBoxProps) {
  const lineCount = script.split("\n").length;
  const lineNumbers = Array.from({ length: lineCount }, (_, index) => index + 1);

  return (
    <div className="flex overflow-hidden rounded-[10px] border border-field bg-surface py-3 font-mono text-[13.5px] leading-[1.9] focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-accent">
      <div aria-hidden="true" className="mr-3.5 ml-4 min-w-[22px] flex-none text-right text-faint select-none">
        {lineNumbers.map((lineNumber) => (
          <div key={lineNumber} className={getLineNumberClass(lineNumber, issues)}>
            {lineNumber}
          </div>
        ))}
      </div>
      <textarea
        aria-label="Script"
        value={script}
        onChange={(event) => onScriptChange(event.target.value)}
        rows={Math.max(lineCount, MIN_VISIBLE_ROWS)}
        wrap="off"
        spellCheck={false}
        placeholder={SCRIPT_PLACEHOLDER}
        className="min-w-0 flex-1 resize-none overflow-x-auto overflow-y-hidden border-0 bg-transparent p-0 pr-4 font-mono text-[13.5px] leading-[1.9] whitespace-pre text-ink focus-visible:outline-none"
      />
    </div>
  );
}
