import { useId, useState } from "react";
import type { TaskStarted } from "../../api/client";
import { useClaudeTaskSlot } from "../../hooks/useClaudeTaskSlot";
import { readTaskSlot } from "../../lib/taskSlots";
import { ErrorMessage } from "../Messages";
import { SURFACE_CARD, TEXT_AREA } from "../styles";
import { ClaudeButton } from "./ClaudeButton";
import { ClaudeTaskPanel } from "./ClaudeTaskPanel";

type ReviseInput = { feedback: string };

type ReviseWithClaudeProps = {
  slotKey: string;
  subjectName: string;
  placeholder: string;
  revise: (feedback: string) => Promise<TaskStarted>;
  // Reloads the revised item so the previews refresh.
  onRevised: () => Promise<void>;
};

// "Ask Claude for changes": a feedback box that starts a revision task and follows it.
export function ReviseWithClaude({ slotKey, subjectName, placeholder, revise, onRevised }: ReviseWithClaudeProps) {
  const feedbackId = useId();
  const [feedback, setFeedback] = useState(() => readTaskSlot<ReviseInput>(slotKey)?.input.feedback ?? "");
  const [isRevised, setIsRevised] = useState(false);

  const controller = useClaudeTaskSlot<ReviseInput>({
    slotKey,
    start: (input) => revise(input.feedback),
    onDone: async () => {
      await onRevised();
      setFeedback("");
      setIsRevised(true);
    },
  });

  if (controller.slot) {
    return (
      <ClaudeTaskPanel controller={controller} pendingTitle={`Revising ${subjectName}`} dismissLabel="Edit the request" />
    );
  }

  const handleAskClick = () => {
    setIsRevised(false);
    controller.startTask({ feedback: feedback.trim() });
  };

  return (
    <section aria-label="Ask Claude for changes" className={`${SURFACE_CARD} flex flex-col gap-2.5 p-5`}>
      <label htmlFor={feedbackId} className="text-[15px] font-semibold">
        Ask Claude for changes
      </label>
      <textarea
        id={feedbackId}
        rows={3}
        value={feedback}
        placeholder={placeholder}
        onChange={(event) => setFeedback(event.target.value)}
        className={TEXT_AREA}
      />
      <ClaudeButton
        label="Ask Claude"
        busyLabel="Starting…"
        isBusy={controller.isStarting}
        disabled={feedback.trim() === ""}
        disabledReason="Describe what to change first."
        onClick={handleAskClick}
      />
      {isRevised && <p className="m-0 text-sm text-success">Done. The previews show Claude’s changes.</p>}
      <ErrorMessage message={controller.startError} />
    </section>
  );
}
