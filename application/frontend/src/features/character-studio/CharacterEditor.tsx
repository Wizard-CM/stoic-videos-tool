import { useState } from "react";
import {
  getCharacter,
  reviseCharacter,
  updateCharacter,
  type Character,
  type ChoiceOption,
  type Options,
  type Voice,
} from "../../api/client";
import { ReviseWithClaude } from "../../components/claude/ReviseWithClaude";
import { PageHeader } from "../../components/PageHeader";
import { SaveStatus } from "../../components/SaveStatus";
import { FIELD_LABEL, SELECT_INPUT, SURFACE_CARD, TEXT_AREA, TEXT_INPUT } from "../../components/styles";
import { useAutosaveDraft } from "../../hooks/useAutosaveDraft";
import { formatCost, formatModelName } from "../../lib/format";
import { SLOT_KEYS } from "../../lib/taskSlots";
import { ROUTES } from "../../routes";
import { CharacterPoseViewer } from "./CharacterPoseViewer";
import { ContactSheets } from "./ContactSheets";
import { VoiceSettings } from "./VoiceSettings";

type CharacterDraft = {
  name: string;
  description: string;
  gender: string | null;
  age: string | null;
  voice: Voice;
};

function toDraft(character: Character): CharacterDraft {
  const { name, description, gender, age, voice } = character;
  return { name, description, gender, age, voice };
}

type DetailSelectProps = {
  id: string;
  label: string;
  value: string | null;
  choices: ChoiceOption[];
  onValueChange: (value: string) => void;
};

function DetailSelect({ id, label, value, choices, onValueChange }: DetailSelectProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className={FIELD_LABEL}>
        {label}
      </label>
      <select id={id} value={value ?? ""} onChange={(event) => onValueChange(event.target.value)} className={SELECT_INPUT}>
        {!value && <option value="">Not set</option>}
        {choices.map((choice) => (
          <option key={choice.value} value={choice.value}>
            {choice.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function MadeByNote({ character }: { character: Character }) {
  if (!character.made_by) return null;
  const modelNames = character.made_by.models.map(formatModelName).join(", ");
  return (
    <p className="m-0 text-[13px] text-muted">
      Designed by Claude{modelNames && ` (${modelNames})`} for {formatCost(character.made_by.cost_usd)}.
    </p>
  );
}

type CharacterEditorProps = {
  initialCharacter: Character;
  options: Options;
};

// The studio for a saved character: previews, contact sheets, revisions, details and voice (autosaved).
export function CharacterEditor({ initialCharacter, options }: CharacterEditorProps) {
  const [character, setCharacter] = useState(initialCharacter);
  const { draft, updateDraft, resetDraft, hasUnsavedChanges, saveError } = useAutosaveDraft(
    toDraft(initialCharacter),
    async (draftToSave) => toDraft(await updateCharacter(initialCharacter.id, draftToSave)),
  );

  const handleRevised = async () => {
    const revisedCharacter = await getCharacter(character.id);
    setCharacter(revisedCharacter);
    resetDraft(toDraft(revisedCharacter));
  };

  const displayName = draft.name || "Untitled character";

  return (
    <div className="flex max-w-[1120px] flex-col gap-6">
      <PageHeader
        parentLabel="Library"
        parentHref={ROUTES.library("characters")}
        title={displayName}
        statusText={<SaveStatus hasUnsavedChanges={hasUnsavedChanges} saveError={saveError} />}
      />

      <div className="flex flex-wrap items-start gap-6">
        <div className="flex min-w-0 flex-[1_1_300px] flex-col gap-4">
          <CharacterPoseViewer character={character} options={options} />
        </div>

        <div className="flex min-w-0 flex-[999_1_420px] flex-col gap-5">
          <ReviseWithClaude
            slotKey={SLOT_KEYS.reviseCharacter(character.id)}
            subjectName={displayName}
            placeholder="e.g. make the hair shorter, add round glasses, and make the angry face more intense"
            revise={(feedback) => reviseCharacter(character.id, feedback)}
            onRevised={handleRevised}
          />

          <section aria-label="Details" className={`${SURFACE_CARD} flex flex-col gap-[18px] p-5`}>
            <h2 className="m-0 text-[17px] font-semibold">Details</h2>
            <div className="grid grid-cols-[repeat(auto-fit,minmax(160px,1fr))] gap-x-6 gap-y-[18px]">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="character-name" className={FIELD_LABEL}>
                  Name
                </label>
                <input
                  id="character-name"
                  type="text"
                  value={draft.name}
                  onChange={(event) => updateDraft({ name: event.target.value })}
                  className={TEXT_INPUT}
                />
              </div>
              <DetailSelect
                id="character-gender"
                label="Gender"
                value={draft.gender}
                choices={options.genders}
                onValueChange={(gender) => updateDraft({ gender })}
              />
              <DetailSelect
                id="character-age"
                label="Age"
                value={draft.age}
                choices={options.ages}
                onValueChange={(age) => updateDraft({ age })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="character-description" className={FIELD_LABEL}>
                Description
              </label>
              <textarea
                id="character-description"
                rows={3}
                value={draft.description}
                onChange={(event) => updateDraft({ description: event.target.value })}
                className={TEXT_AREA}
              />
              <p className="m-0 text-[13px] text-muted">
                Editing these doesn’t redraw the character. To change the drawing, ask Claude above.
              </p>
            </div>
            <MadeByNote character={character} />
          </section>

          <section aria-label="Voice" className={`${SURFACE_CARD} flex flex-col gap-[18px] p-5`}>
            <h2 className="m-0 text-[17px] font-semibold">Voice</h2>
            <VoiceSettings
              voice={draft.voice}
              voices={options.voices}
              gender={draft.gender}
              age={draft.age}
              onVoiceChange={(voice) => updateDraft({ voice })}
            />
          </section>
        </div>
      </div>

      <ContactSheets character={character} />
    </div>
  );
}
