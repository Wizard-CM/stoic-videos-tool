import type { Character, ChoiceOption, Control, ParamValue } from "../../api/client";
import { capitalize } from "../../lib/format";

// These two keys are part of the API contract: auto-voice is picked from gender and age.
export const GENDER_KEY = "gender";
export const AGE_KEY = "age";

// "Narrow" / "Medium" / "Wide" for a 0..1 slider.
export function getSliderHint(value: number, control: Control) {
  if (!control.low || !control.high) return String(Math.round(value * 100));
  if (value < 0.45) return control.low;
  if (value > 0.55) return control.high;
  return "Medium";
}

// "Lower" / "Slightly lower" / "Normal" / "Slightly higher" / "Higher" for a -1..1 voice offset.
export function getOffsetHint(offset: number, lowerWord: string, higherWord: string) {
  if (offset <= -0.5) return capitalize(lowerWord);
  if (offset < -0.05) return `Slightly ${lowerWord}`;
  if (offset <= 0.05) return "Normal";
  if (offset < 0.5) return `Slightly ${higherWord}`;
  return capitalize(higherWord);
}

// Voice offsets are -1..1 but the sliders show 0..100.
export function offsetToSliderValue(offset: number) {
  return Math.round((offset + 1) * 50);
}

export function sliderValueToOffset(sliderValue: number) {
  return sliderValue / 50 - 1;
}

export function getSelectOptions(control: Control, gender: string): ChoiceOption[] {
  if (control.options) return control.options;
  return control.options_by_gender?.[gender] ?? [];
}

// Sets one param. When gender changes, any gender-specific choice that no longer exists
// (e.g. a hair style) is replaced by the first option for the new gender.
export function setCharacterParam(character: Character, key: string, value: ParamValue, controls: Control[]) {
  const params = { ...character.params, [key]: value };

  if (key === GENDER_KEY) {
    for (const control of controls) {
      const genderOptions = control.options_by_gender?.[String(value)];
      if (!genderOptions || genderOptions.length === 0) continue;
      const isCurrentValueValid = genderOptions.some((option) => option.value === params[control.key]);
      if (!isCurrentValueValid) params[control.key] = genderOptions[0].value;
    }
  }

  return { ...character, params };
}
