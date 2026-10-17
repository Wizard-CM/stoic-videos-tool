import { useState } from "react";
import { getCharacterSheetUrl, type Character, type CharacterSheet } from "../../api/client";
import { PillGroup } from "../../components/PillGroup";
import { PreviewImage } from "../../components/PreviewImage";
import { SURFACE_CARD } from "../../components/styles";

const SHEETS: { value: CharacterSheet; label: string }[] = [
  { value: "expressions", label: "Expressions" },
  { value: "mouths", label: "Mouths" },
  { value: "gestures", label: "Gestures" },
  { value: "eyes", label: "Eyes" },
  { value: "hands", label: "Hands" },
];

// Every part of the kit at a glance, one contact sheet per tab.
export function ContactSheets({ character }: { character: Character }) {
  const [sheet, setSheet] = useState<CharacterSheet>("expressions");
  const sheetUrl = getCharacterSheetUrl(character.id, sheet, character.updated_at);

  return (
    <section aria-label="Contact sheets" className={`${SURFACE_CARD} flex flex-col gap-4 p-5`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="m-0 text-[17px] font-semibold">Contact sheets</h2>
        <a href={sheetUrl} target="_blank" rel="noreferrer" className="text-sm">
          Open full size
        </a>
      </div>
      <PillGroup
        legend="Sheet"
        options={SHEETS}
        selected={sheet}
        onSelect={(value) => setSheet(value as CharacterSheet)}
      />
      <PreviewImage src={sheetUrl} alt={`${character.name}, ${sheet} contact sheet`} className="min-h-48" />
    </section>
  );
}
