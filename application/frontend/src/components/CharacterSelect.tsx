import type { CharacterSummary } from "../api/client";
import { FIELD_LABEL, SELECT_INPUT } from "./styles";

type CharacterSelectProps = {
  id: string;
  label: string;
  characters: CharacterSummary[] | null;
  // "" means no character.
  value: string;
  onValueChange: (characterId: string) => void;
};

// Picks an optional library character, e.g. to show in a background preview.
export function CharacterSelect({ id, label, characters, value, onValueChange }: CharacterSelectProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className={FIELD_LABEL}>
        {label} <span className="font-normal text-muted">(optional)</span>
      </label>
      <select id={id} value={value} onChange={(event) => onValueChange(event.target.value)} className={SELECT_INPUT}>
        <option value="">No character</option>
        {characters?.map((character) => (
          <option key={character.id} value={character.id}>
            {character.name}
          </option>
        ))}
      </select>
    </div>
  );
}
