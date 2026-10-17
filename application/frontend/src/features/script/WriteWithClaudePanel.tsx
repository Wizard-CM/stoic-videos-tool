import { useState } from "react";
import { generateScript, getErrorMessage, type ClaudeTask, type Options, type ScriptRequest } from "../../api/client";
import { ClaudeButton } from "../../components/claude/ClaudeButton";
import { ClaudeTaskPanel } from "../../components/claude/ClaudeTaskPanel";
import { SparkleIcon } from "../../components/icons";
import { ErrorMessage } from "../../components/Messages";
import {
  FIELD_LABEL,
  PRIMARY_BUTTON,
  SECONDARY_BUTTON,
  SELECT_INPUT,
  SURFACE_CARD,
  TEXT_AREA,
} from "../../components/styles";
import { useClaudeTaskSlot, type ClaudeTaskController } from "../../hooks/useClaudeTaskSlot";
import { formatCost } from "../../lib/format";
import { readTaskSlot, SLOT_KEYS } from "../../lib/taskSlots";

type WriteWithClaudePanelProps = {
  projectId: string;
  options: Options;
  currentScript: string;
  // Saves Claude's title and script to the project.
  onUseScript: (title: string, script: string) => Promise<void>;
};

type ScriptProposalProps = {
  task: ClaudeTask;
  controller: ClaudeTaskController;
  currentScript: string;
  onUseScript: (title: string, script: string) => Promise<void>;
};

// Claude's finished script, read-only, until the user uses or discards it.
function ScriptProposal({ task, controller, currentScript, onUseScript }: ScriptProposalProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const title = task.result?.title ?? "";
  const script = task.result?.script ?? "";

  const handleUseClick = async () => {
    if (currentScript.trim() !== "" && !window.confirm("Replace your current script with Claude’s?")) return;
    setIsSaving(true);
    setSaveError(null);
    try {
      await onUseScript(title, script);
      controller.dismiss();
    } catch (error) {
      setSaveError(getErrorMessage(error));
      setIsSaving(false);
    }
  };

  return (
    <section aria-label="Claude’s script" className={`${SURFACE_CARD} flex flex-col gap-3.5 p-5`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="m-0 text-[17px] font-semibold">Claude’s script: {title || "Untitled"}</h2>
        <p className="m-0 text-[13px] text-muted">Written for {formatCost(task.cost_usd)}</p>
      </div>
      <pre className="m-0 max-h-[420px] overflow-auto rounded-[10px] border border-line bg-page px-4 py-3 font-mono text-[13.5px] leading-[1.9] whitespace-pre-wrap text-ink">
        {script || "Claude returned an empty script."}
      </pre>
      <div className="flex flex-wrap gap-2.5">
        <button type="button" className={PRIMARY_BUTTON} disabled={isSaving || !script} onClick={handleUseClick}>
          {isSaving ? "Saving…" : "Use this script"}
        </button>
        <button type="button" className={SECONDARY_BUTTON} disabled={isSaving} onClick={controller.dismiss}>
          Discard
        </button>
      </div>
      <ErrorMessage message={saveError} />
    </section>
  );
}

// Idea → "Write with Claude" → task panel → proposed script to use or discard.
export function WriteWithClaudePanel({ projectId, options, currentScript, onUseScript }: WriteWithClaudePanelProps) {
  const slotKey = SLOT_KEYS.script(projectId);
  const [request, setRequest] = useState<ScriptRequest>(
    () =>
      readTaskSlot<ScriptRequest>(slotKey)?.input ?? {
        idea: "",
        length: options.script_lengths[0]?.value ?? "short",
        use_library: true,
      },
  );
  const [isOpen, setIsOpen] = useState(() => currentScript.trim() === "");
  const controller = useClaudeTaskSlot<ScriptRequest>({
    slotKey,
    start: (input) => generateScript(projectId, input),
  });

  const { task } = controller;
  if (task?.state === "done") {
    return <ScriptProposal task={task} controller={controller} currentScript={currentScript} onUseScript={onUseScript} />;
  }
  if (controller.slot) {
    return <ClaudeTaskPanel controller={controller} pendingTitle="Writing the script" dismissLabel="Edit the idea" />;
  }

  if (!isOpen) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-[10px] border border-line bg-surface px-4 py-2.5">
        <p className="m-0 text-[14.5px] text-muted">Have an idea but no script? Claude can write it.</p>
        <button type="button" className={SECONDARY_BUTTON} onClick={() => setIsOpen(true)}>
          <SparkleIcon />
          Write with Claude
        </button>
      </div>
    );
  }

  const updateRequest = (changes: Partial<ScriptRequest>) => setRequest({ ...request, ...changes });

  return (
    <section aria-label="Write with Claude" className={`${SURFACE_CARD} flex flex-col gap-4 p-5`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="m-0 text-[17px] font-semibold">Write with Claude</h2>
        <button type="button" className={SECONDARY_BUTTON} onClick={() => setIsOpen(false)}>
          Close
        </button>
      </div>
      <div className="flex flex-col gap-1.5">
        <label htmlFor="script-idea" className={FIELD_LABEL}>
          Idea
        </label>
        <textarea
          id="script-idea"
          rows={3}
          value={request.idea}
          placeholder="e.g. two coworkers argue about a missing report, and the quiet one turns out to be right"
          onChange={(event) => updateRequest({ idea: event.target.value })}
          className={TEXT_AREA}
        />
      </div>
      <div className="flex flex-wrap items-end gap-x-6 gap-y-3">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="script-length" className={FIELD_LABEL}>
            Length
          </label>
          <select
            id="script-length"
            value={request.length}
            onChange={(event) => updateRequest({ length: event.target.value })}
            className={SELECT_INPUT}
          >
            {options.script_lengths.map((length) => (
              <option key={length.value} value={length.value}>
                {length.label}
              </option>
            ))}
          </select>
        </div>
        <label className="flex min-h-11 items-center gap-2.5 text-[14.5px]">
          <input
            type="checkbox"
            checked={request.use_library}
            onChange={(event) => updateRequest({ use_library: event.target.checked })}
            className="size-5 accent-accent"
          />
          Use characters from my library
        </label>
      </div>
      <ClaudeButton
        label="Write with Claude"
        busyLabel="Starting…"
        isBusy={controller.isStarting}
        disabled={request.idea.trim() === ""}
        disabledReason="Describe the idea first."
        onClick={() => controller.startTask({ ...request, idea: request.idea.trim() })}
      />
      <ErrorMessage message={controller.startError} />
    </section>
  );
}
