import { useState } from "react";
import { getCharacterPreviewUrl, type Character, type Options } from "../../api/client";
import { PillGroup } from "../../components/PillGroup";
import { PreviewImage } from "../../components/PreviewImage";
import { getPoseNames, pickDefaultName, toChoiceOptions } from "./poseNames";

const PREVIEW_WIDTH = 480;
const PREVIEW_HEIGHT = 600;

type CharacterPoseViewerProps = {
  character: Character;
  options: Options;
};

// Big engine preview with an expression and a gesture switcher.
export function CharacterPoseViewer({ character, options }: CharacterPoseViewerProps) {
  const poseNames = getPoseNames(character, options);
  const [selectedExpression, setExpression] = useState("neutral");
  const [selectedGesture, setGesture] = useState("rest");

  // A revision can rename poses, so fall back to the default when the choice is gone.
  const expression = poseNames.expressions.includes(selectedExpression)
    ? selectedExpression
    : pickDefaultName(poseNames.expressions, "neutral");
  const gesture = poseNames.gestures.includes(selectedGesture)
    ? selectedGesture
    : pickDefaultName(poseNames.gestures, "rest");

  const previewUrl = getCharacterPreviewUrl(character.id, {
    expression,
    gesture,
    width: PREVIEW_WIDTH,
    height: PREVIEW_HEIGHT,
    version: character.updated_at,
  });

  return (
    <section aria-label="Preview" className="flex flex-col gap-4">
      <PreviewImage
        src={previewUrl}
        alt={`${character.name}, ${expression} expression, ${gesture} gesture`}
        className="aspect-[4/5] border border-line"
      />
      <PillGroup
        legend="Expression"
        options={toChoiceOptions(poseNames.expressions, options.emotions)}
        selected={expression}
        onSelect={setExpression}
      />
      <PillGroup
        legend="Gesture"
        options={toChoiceOptions(poseNames.gestures, options.gestures)}
        selected={gesture}
        onSelect={setGesture}
      />
    </section>
  );
}
