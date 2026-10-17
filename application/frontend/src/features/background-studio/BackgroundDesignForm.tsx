import { useId, useState } from "react";
import { generateBackground, type CharacterSummary, type ClaudeTask } from "../../api/client";
import { CharacterSelect } from "../../components/CharacterSelect";
import { ClaudeButton } from "../../components/claude/ClaudeButton";
import { ClaudeTaskPanel } from "../../components/claude/ClaudeTaskPanel";
import { ErrorMessage } from "../../components/Messages";
import { FIELD_LABEL, SECONDARY_BUTTON, SURFACE_CARD, TEXT_AREA, TEXT_INPUT } from "../../components/styles";
import { useClaudeTaskSlot } from "../../hooks/useClaudeTaskSlot";
import { readTaskSlot } from "../../lib/taskSlots";

type BackgroundDesignInput = {
  name: string;
  description: string;
  // "" for no character.
  characterId: string;
};

type BackgroundDesignFormProps = {
  slotKey: string;
  heading: string;
  characters: CharacterSummary[] | null;
  initialName?: string;
  defaultCharacterId?: string | null;
  // Called with the new library background once Claude has finished it.
  onCreated: (backgroundId: string) => Promise<void> | void;
  onCancel?: () => void;
};

const DESCRIPTION_PLACEHOLDER =
  "Describe the place: setting, colors, props, mood… e.g. paneled green office wall, framed abstract art, warm desk lamp";

function startBackgroundDesign(input: BackgroundDesignInput) {
  return generateBackground({
    name: input.name,
    description: input.description,
    character_id: input.characterId || undefined,
  });
}

function getCreatedBackgroundId(task: ClaudeTask) {
  const backgroundId = task.result?.background_id;
  if (!backgroundId) throw new Error("Claude finished without returning a background.");
  return backgroundId;
}

// Name + description (+ a character to frame) → "Design with Claude" → task panel.
export function BackgroundDesignForm({
  slotKey,
  heading,
  characters,
  initialName = "",
  defaultCharacterId = null,
  onCreated,
  onCancel,
}: BackgroundDesignFormProps) {
  const fieldId = useId();
  const [input, setInput] = useState<BackgroundDesignInput>(
    () =>
      readTaskSlot<BackgroundDesignInput>(slotKey)?.input ?? {
        name: initialName,
        description: "",
        characterId: defaultCharacterId ?? "",
      },
  );

  const controller = useClaudeTaskSlot<BackgroundDesignInput>({
    slotKey,
    start: startBackgroundDesign,
    onDone: (task) => onCreated(getCreatedBackgroundId(task)),
  });

  if (controller.slot) {
    return (
      <ClaudeTaskPanel
        controller={controller}
        pendingTitle={`Designing ${input.name || "the background"}`}
        dismissLabel="Edit and try again"
      />
    );
  }

  const updateInput = (changes: Partial<BackgroundDesignInput>) => setInput({ ...input, ...changes });
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

      <div className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-x-6 gap-y-[18px]">
        <div className="flex flex-col gap-1.5">
          <label htmlFor={`${fieldId}-name`} className={FIELD_LABEL}>
            Name
          </label>
          <input
            id={`${fieldId}-name`}
            type="text"
            value={input.name}
            placeholder="e.g. Green office"
            onChange={(event) => updateInput({ name: event.target.value })}
            className={TEXT_INPUT}
          />
        </div>
        <CharacterSelect
          id={`${fieldId}-character`}
          label="Character to frame"
          characters={characters}
          value={input.characterId}
          onValueChange={(characterId) => updateInput({ characterId })}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor={`${fieldId}-description`} className={FIELD_LABEL}>
          Description
        </label>
        <textarea
          id={`${fieldId}-description`}
          rows={5}
          value={input.description}
          placeholder={DESCRIPTION_PLACEHOLDER}
          onChange={(event) => updateInput({ description: event.target.value })}
          className={TEXT_AREA}
        />
        <p className="m-0 text-[13px] text-muted">
          With a character chosen, Claude composes the set around them and the preview shows them in it.
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
