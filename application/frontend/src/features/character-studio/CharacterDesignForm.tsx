import { useId, useState } from "react";
import { generateCharacter, type ChoiceOption, type ClaudeTask, type Options } from "../../api/client";
import { ClaudeButton } from "../../components/claude/ClaudeButton";
import { ClaudeTaskPanel } from "../../components/claude/ClaudeTaskPanel";
import { ErrorMessage } from "../../components/Messages";
import {
  FIELD_LABEL,
  SECONDARY_BUTTON,
  SELECT_INPUT,
  SURFACE_CARD,
  TEXT_AREA,
  TEXT_INPUT,
} from "../../components/styles";
import { useClaudeTaskSlot } from "../../hooks/useClaudeTaskSlot";
import { readTaskSlot } from "../../lib/taskSlots";

type CharacterDesignInput = {
  name: string;
  description: string;
  // "" lets Claude decide.
  gender: string;
  age: string;
};

type CharacterDesignFormProps = {
  slotKey: string;
  options: Options;
  heading: string;
  initialName?: string;
  // Called with the new library character once Claude has finished it.
  onCreated: (characterId: string) => Promise<void> | void;
  // Shows a Cancel button next to the heading.
  onCancel?: () => void;
};

const DESCRIPTION_PLACEHOLDER =
  "Describe the character: look, age, clothes, personality… e.g. sharp project manager in her 30s, long black hair, green blouse, dark blazer, teal earrings";

function startCharacterDesign(input: CharacterDesignInput) {
  return generateCharacter({
    name: input.name,
    description: input.description,
    gender: input.gender || undefined,
    age: input.age || undefined,
  });
}

function getCreatedCharacterId(task: ClaudeTask) {
  const characterId = task.result?.character_id;
  if (!characterId) throw new Error("Claude finished without returning a character.");
  return characterId;
}

type OptionalSelectProps = {
  id: string;
  label: string;
  value: string;
  choices: ChoiceOption[];
  onValueChange: (value: string) => void;
};

function OptionalSelect({ id, label, value, choices, onValueChange }: OptionalSelectProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className={FIELD_LABEL}>
        {label} <span className="font-normal text-muted">(optional)</span>
      </label>
      <select id={id} value={value} onChange={(event) => onValueChange(event.target.value)} className={SELECT_INPUT}>
        <option value="">Let Claude decide</option>
        {choices.map((choice) => (
          <option key={choice.value} value={choice.value}>
            {choice.label}
          </option>
        ))}
      </select>
    </div>
  );
}

// Name + description → "Design with Claude" → task panel. Used by the studio and the cast screen.
export function CharacterDesignForm({
  slotKey,
  options,
  heading,
  initialName = "",
  onCreated,
  onCancel,
}: CharacterDesignFormProps) {
  const fieldId = useId();
  const [input, setInput] = useState<CharacterDesignInput>(
    () => readTaskSlot<CharacterDesignInput>(slotKey)?.input ?? { name: initialName, description: "", gender: "", age: "" },
  );

  const controller = useClaudeTaskSlot<CharacterDesignInput>({
    slotKey,
    start: startCharacterDesign,
    onDone: (task) => onCreated(getCreatedCharacterId(task)),
  });

  if (controller.slot) {
    return (
      <ClaudeTaskPanel
        controller={controller}
        pendingTitle={`Designing ${input.name || "the character"}`}
        dismissLabel="Edit and try again"
      />
    );
  }

  const updateInput = (changes: Partial<CharacterDesignInput>) => setInput({ ...input, ...changes });
  const isIncomplete = input.name.trim() === "" || input.description.trim() === "";

  const handleDesignClick = () => {
    controller.startTask({ ...input, name: input.name.trim(), description: input.description.trim() });
  };

  return (
    <section aria-label={heading} className={`${SURFACE_CARD} flex flex-col gap-5 p-5`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="m-0 text-[17px] font-semibold">{heading}</h2>
        {onCancel && (
          <button type="button" className={SECONDARY_BUTTON} onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-x-6 gap-y-[18px]">
        <div className="flex flex-col gap-1.5">
          <label htmlFor={`${fieldId}-name`} className={FIELD_LABEL}>
            Name
          </label>
          <input
            id={`${fieldId}-name`}
            type="text"
            value={input.name}
            onChange={(event) => updateInput({ name: event.target.value })}
            className={TEXT_INPUT}
          />
        </div>
        <OptionalSelect
          id={`${fieldId}-gender`}
          label="Gender"
          value={input.gender}
          choices={options.genders}
          onValueChange={(gender) => updateInput({ gender })}
        />
        <OptionalSelect
          id={`${fieldId}-age`}
          label="Age"
          value={input.age}
          choices={options.ages}
          onValueChange={(age) => updateInput({ age })}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor={`${fieldId}-description`} className={FIELD_LABEL}>
          Description
        </label>
        <textarea
          id={`${fieldId}-description`}
          rows={6}
          value={input.description}
          placeholder={DESCRIPTION_PLACEHOLDER}
          onChange={(event) => updateInput({ description: event.target.value })}
          className={TEXT_AREA}
        />
        <p className="m-0 text-[13px] text-muted">
          Claude draws the whole puppet from this: face, every expression and mouth shape, and the hand gestures. It
          usually takes a few minutes.
        </p>
      </div>

      <ClaudeButton
        label="Design with Claude"
        busyLabel="Starting…"
        isBusy={controller.isStarting}
        disabled={isIncomplete}
        disabledReason="Add a name and a description first."
        onClick={handleDesignClick}
      />
      <ErrorMessage message={controller.startError} />
    </section>
  );
}
