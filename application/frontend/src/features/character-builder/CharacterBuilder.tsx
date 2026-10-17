import { useState } from "react";
import {
  autofillCharacter,
  getErrorMessage,
  pickAutoVoice,
  randomizeCharacter,
  type Character,
  type Control,
  type Options,
  type ParamValue,
} from "../../api/client";
import { RefreshIcon } from "../../components/icons";
import { ErrorMessage } from "../../components/Messages";
import { DARK_BUTTON, FIELD_LABEL, SECONDARY_BUTTON, SELECT_INPUT, TEXT_INPUT } from "../../components/styles";
import { CharacterPreview } from "./CharacterPreview";
import { AGE_KEY, GENDER_KEY, setCharacterParam } from "./characterHelpers";
import { ControlField } from "./ControlField";
import { VoiceSettings } from "./VoiceSettings";

// These sections are always visible; the rest fold away in <details>.
const OPEN_SECTIONS = ["Identity", "Proportions"];
const MAX_BACKGROUND_SEED = 100000;
const CONTROL_GRID = "grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-x-6 gap-y-[18px]";

type AutofillSummary = {
  matched: string[];
  unmatched: string[];
};

type CharacterBuilderProps = {
  character: Character;
  options: Options;
  // Voices already used by other speakers, so auto-voice picks a different one.
  usedVoiceIds: string[];
  onCharacterChange: (character: Character) => void;
  onSave: () => Promise<Character>;
};

export function CharacterBuilder({ character, options, usedVoiceIds, onCharacterChange, onSave }: CharacterBuilderProps) {
  const [autofillSummary, setAutofillSummary] = useState<AutofillSummary | null>(null);
  const [isApplyingDescription, setIsApplyingDescription] = useState(false);
  const [builderError, setBuilderError] = useState<string | null>(null);
  const [autoVoiceError, setAutoVoiceError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [lastSavedCharacter, setLastSavedCharacter] = useState<Character | null>(null);

  const gender = String(character.params[GENDER_KEY] ?? "");
  const isSavedToLibrary = lastSavedCharacter === character;
  const displayName = character.name || "this character";

  // Applies a change, then picks a new voice if gender or age changed while the voice is still automatic.
  const applyCharacterChange = async (nextCharacter: Character) => {
    onCharacterChange(nextCharacter);

    const hasGenderChanged = nextCharacter.params[GENDER_KEY] !== character.params[GENDER_KEY];
    const hasAgeChanged = nextCharacter.params[AGE_KEY] !== character.params[AGE_KEY];
    if (!nextCharacter.voice.auto || (!hasGenderChanged && !hasAgeChanged)) return;

    try {
      const { voice_id } = await pickAutoVoice(
        String(nextCharacter.params[GENDER_KEY]),
        String(nextCharacter.params[AGE_KEY]),
        usedVoiceIds,
      );
      onCharacterChange({ ...nextCharacter, voice: { ...nextCharacter.voice, voice_id } });
      setAutoVoiceError(null);
    } catch (error) {
      setAutoVoiceError(getErrorMessage(error));
    }
  };

  const handleParamChange = (key: string, value: ParamValue) => {
    applyCharacterChange(setCharacterParam(character, key, value, options.controls));
  };

  const handleApplyDescriptionClick = async () => {
    setIsApplyingDescription(true);
    setBuilderError(null);
    try {
      const result = await autofillCharacter(character.description, character);
      setAutofillSummary({ matched: result.matched, unmatched: result.unmatched });
      await applyCharacterChange(result.character);
    } catch (error) {
      setBuilderError(getErrorMessage(error));
    } finally {
      setIsApplyingDescription(false);
    }
  };

  const handleRandomizeClick = async () => {
    setBuilderError(null);
    try {
      const result = await randomizeCharacter(character);
      applyCharacterChange(result.character);
    } catch (error) {
      setBuilderError(getErrorMessage(error));
    }
  };

  const handleBackgroundChange = (generator: string) => {
    onCharacterChange({ ...character, background: { ...character.background, generator } });
  };

  const handleNewBackgroundClick = () => {
    const seed = Math.floor(Math.random() * MAX_BACKGROUND_SEED);
    onCharacterChange({ ...character, background: { ...character.background, seed } });
  };

  const handleSaveClick = async () => {
    setIsSaving(true);
    setSaveError(null);
    try {
      setLastSavedCharacter(await onSave());
    } catch (error) {
      setSaveError(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  };

  const renderControls = (sectionControls: Control[]) =>
    sectionControls.map((control) => (
      <ControlField
        key={control.key}
        control={control}
        value={character.params[control.key]}
        gender={gender}
        onValueChange={(value) => handleParamChange(control.key, value)}
      />
    ));

  return (
    <div className="flex min-w-0 flex-[999_1_680px] flex-wrap items-start gap-5">
      <section
        aria-label="Character builder"
        className="flex min-w-0 flex-[999_1_380px] flex-col gap-[22px] rounded-xl border border-line bg-surface p-5"
      >
        <div className="flex flex-col gap-2">
          <label htmlFor="character-description" className="text-[15px] font-semibold">
            Describe {displayName}
          </label>
          <textarea
            id="character-description"
            rows={3}
            value={character.description}
            placeholder="e.g. old man, silver hair, blue suit, glasses"
            onChange={(event) => onCharacterChange({ ...character, description: event.target.value })}
            className="resize-y rounded-lg border border-field px-3 py-2.5 text-[15px] leading-normal text-ink"
          />
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className={SECONDARY_BUTTON}
              disabled={isApplyingDescription || character.description.trim() === ""}
              onClick={handleApplyDescriptionClick}
            >
              {isApplyingDescription ? "Applying…" : "Apply description"}
            </button>
          </div>
          {autofillSummary && autofillSummary.matched.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="mr-0.5 text-[13px] text-muted">Applied:</span>
              {autofillSummary.matched.map((matchedWord) => (
                <span key={matchedWord} className="rounded-full bg-success-soft px-2.5 py-[3px] text-[13px] text-success">
                  {matchedWord}
                </span>
              ))}
            </div>
          )}
          {autofillSummary && autofillSummary.unmatched.length > 0 && (
            <p className="m-0 text-[13px] text-muted">
              Not understood: {autofillSummary.unmatched.map((word) => `“${word}”`).join(", ")}. Set it with the
              controls below.
            </p>
          )}
        </div>

        {options.sections.map((section) => {
          const sectionControls = options.controls.filter((control) => control.section === section);
          const isIdentity = section === "Identity";

          if (OPEN_SECTIONS.includes(section)) {
            return (
              <div key={section} className="flex flex-col gap-3">
                <h3 className="m-0 text-[15px] font-semibold">{section}</h3>
                <div className={CONTROL_GRID}>
                  {isIdentity && (
                    <div className="flex flex-col gap-1.5">
                      <label htmlFor="character-name" className={FIELD_LABEL}>
                        Name
                      </label>
                      <input
                        id="character-name"
                        type="text"
                        value={character.name}
                        onChange={(event) => onCharacterChange({ ...character, name: event.target.value })}
                        className={TEXT_INPUT}
                      />
                    </div>
                  )}
                  {renderControls(sectionControls)}
                </div>
              </div>
            );
          }

          return (
            <details key={section} className="border-t border-line pt-2">
              <summary className="flex min-h-11 items-center text-[15px] font-semibold">{section}</summary>
              <div className={`${CONTROL_GRID} pt-2`}>{renderControls(sectionControls)}</div>
            </details>
          );
        })}

        <div className="flex flex-col gap-1.5 border-t border-line pt-[18px]">
          <label htmlFor="character-background" className={FIELD_LABEL}>
            Background
          </label>
          <div className="flex max-w-sm gap-2">
            <select
              id="character-background"
              value={character.background.generator}
              onChange={(event) => handleBackgroundChange(event.target.value)}
              className={`${SELECT_INPUT} min-w-0 flex-1`}
            >
              {options.backgrounds.map((background) => (
                <option key={background.value} value={background.value}>
                  {background.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              aria-label="New background variation"
              onClick={handleNewBackgroundClick}
              className="inline-flex min-h-11 w-11 items-center justify-center rounded-lg border border-field bg-surface"
            >
              <RefreshIcon />
            </button>
          </div>
        </div>

        <VoiceSettings
          voice={character.voice}
          voices={options.voices}
          autoVoiceError={autoVoiceError}
          onVoiceChange={(voice) => onCharacterChange({ ...character, voice })}
        />
      </section>

      <section aria-label="Preview" className="flex min-w-0 flex-[1_1_280px] flex-col gap-3.5">
        <CharacterPreview character={character} emotions={options.emotions} />
        <div className="flex gap-2">
          <button type="button" className={`${SECONDARY_BUTTON} flex-1`} onClick={handleRandomizeClick}>
            Randomize
          </button>
          <button type="button" className={`${DARK_BUTTON} flex-1`} disabled={isSaving} onClick={handleSaveClick}>
            {isSaving ? "Saving…" : "Save to library"}
          </button>
        </div>
        {isSavedToLibrary && <p className="m-0 text-sm text-success">Saved to library.</p>}
        <ErrorMessage message={saveError ?? builderError} />
      </section>
    </div>
  );
}
