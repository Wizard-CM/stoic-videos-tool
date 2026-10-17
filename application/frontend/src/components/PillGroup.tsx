import type { ChoiceOption } from "../api/client";

const SELECTED_PILL = "border-accent bg-accent text-white";
const UNSELECTED_PILL = "border-field bg-surface text-ink";

type PillGroupProps = {
  legend: string;
  options: ChoiceOption[];
  selected: string;
  onSelect: (value: string) => void;
};

// A row of toggle pills where one is selected, e.g. expressions or contact sheets.
export function PillGroup({ legend, options, selected, onSelect }: PillGroupProps) {
  return (
    <fieldset className="m-0 min-w-0 border-0 p-0">
      <legend className="mb-2 p-0 text-sm font-medium">{legend}</legend>
      <div className="flex flex-wrap gap-1.5">
        {options.map((option) => {
          const isSelected = option.value === selected;
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={isSelected}
              onClick={() => onSelect(option.value)}
              className={`min-h-11 rounded-full border px-3 text-[13.5px] ${isSelected ? SELECTED_PILL : UNSELECTED_PILL}`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
