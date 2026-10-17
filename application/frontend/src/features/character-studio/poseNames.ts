import type { Character, ChoiceOption, Options } from "../../api/client";
import { humanizeName } from "../../lib/format";

// Names of a section of Claude's kit (`kit.expressions` / `kit.gestures` are maps keyed by name).
function readKitNames(kit: unknown, section: "expressions" | "gestures") {
  if (typeof kit !== "object" || kit === null) return [];
  const sectionValue = (kit as Record<string, unknown>)[section];
  if (typeof sectionValue !== "object" || sectionValue === null || Array.isArray(sectionValue)) return [];
  return Object.keys(sectionValue);
}

// The expressions and gestures this character can show. GET /api/characters/{id} doesn't promise the name
// lists that summaries carry, so they are read from the kit, with the standard names as a last resort.
export function getPoseNames(character: Character, options: Options) {
  const expressions = character.expressions ?? readKitNames(character.kit, "expressions");
  const gestures = character.gestures ?? readKitNames(character.kit, "gestures");
  return {
    expressions: expressions.length > 0 ? expressions : options.emotions.map((emotion) => emotion.value),
    gestures: gestures.length > 0 ? gestures : options.gestures.map((gesture) => gesture.value),
  };
}

// Pill options with the friendly label from GET /api/options when there is one.
export function toChoiceOptions(names: string[], knownChoices: ChoiceOption[]): ChoiceOption[] {
  return names.map((name) => ({
    value: name,
    label: knownChoices.find((choice) => choice.value === name)?.label ?? humanizeName(name),
  }));
}

export function pickDefaultName(names: string[], preferredName: string) {
  return names.includes(preferredName) ? preferredName : (names[0] ?? preferredName);
}
