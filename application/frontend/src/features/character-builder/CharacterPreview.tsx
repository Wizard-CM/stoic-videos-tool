import { useState } from "react";
import type { Character, ChoiceOption } from "../../api/client";
import { ErrorMessage } from "../../components/Messages";
import { useCharacterPreview } from "./useCharacterPreview";

const SELECTED_PILL = "border-accent bg-accent text-white";
const UNSELECTED_PILL = "border-field bg-surface text-ink";

type CharacterPreviewProps = {
  character: Character;
  emotions: ChoiceOption[];
};

export function CharacterPreview({ character, emotions }: CharacterPreviewProps) {
  const [selectedEmotion, setSelectedEmotion] = useState(() => emotions[0]?.value ?? "neutral");
  const { previewImageUrl, previewError } = useCharacterPreview(character, selectedEmotion);

  return (
    <>
      <div className="aspect-[4/5] overflow-hidden rounded-xl bg-placeholder">
        {previewImageUrl && (
          <img
            src={previewImageUrl}
            alt={`${character.name} preview, ${selectedEmotion} expression`}
            className="size-full object-cover"
          />
        )}
      </div>
      <ErrorMessage message={previewError} />
      <fieldset className="m-0 border-0 p-0">
        <legend className="mb-2 p-0 text-sm font-medium">Try an expression</legend>
        <div className="flex flex-wrap gap-1.5">
          {emotions.map((emotion) => {
            const isSelected = emotion.value === selectedEmotion;
            return (
              <button
                key={emotion.value}
                type="button"
                aria-pressed={isSelected}
                onClick={() => setSelectedEmotion(emotion.value)}
                className={`min-h-11 rounded-full border px-3 text-[13.5px] ${isSelected ? SELECTED_PILL : UNSELECTED_PILL}`}
              >
                {emotion.label}
              </button>
            );
          })}
        </div>
      </fieldset>
    </>
  );
}
