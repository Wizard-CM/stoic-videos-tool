import type { Control, ParamValue } from "../../api/client";
import { FIELD_LABEL, RANGE_INPUT, SELECT_INPUT } from "../../components/styles";
import { getSelectOptions, getSliderHint } from "./characterHelpers";

type ControlFieldProps = {
  control: Control;
  value: ParamValue | undefined;
  gender: string;
  onValueChange: (value: ParamValue) => void;
};

function SliderField({ control, value, onValueChange }: ControlFieldProps) {
  const sliderValue = Number(value ?? 0.5);
  const inputId = `control-${control.key}`;

  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-sm">
        <label htmlFor={inputId} className="font-medium">
          {control.label}
        </label>
        <span className="text-muted">{getSliderHint(sliderValue, control)}</span>
      </div>
      <input
        id={inputId}
        type="range"
        min={0}
        max={100}
        value={Math.round(sliderValue * 100)}
        onChange={(event) => onValueChange(Number(event.target.value) / 100)}
        className={RANGE_INPUT}
      />
    </div>
  );
}

function SelectField({ control, value, gender, onValueChange }: ControlFieldProps) {
  const inputId = `control-${control.key}`;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={inputId} className={FIELD_LABEL}>
        {control.label}
      </label>
      <select
        id={inputId}
        value={String(value ?? "")}
        onChange={(event) => onValueChange(event.target.value)}
        className={SELECT_INPUT}
      >
        {getSelectOptions(control, gender).map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function ColorField({ control, value, onValueChange }: ControlFieldProps) {
  const currentColor = String(value ?? "#000000").toLowerCase();

  return (
    <fieldset className="m-0 border-0 p-0">
      <legend className={`mb-1.5 p-0 ${FIELD_LABEL}`}>{control.label}</legend>
      <div className="flex flex-wrap items-center gap-1.5">
        {control.swatches?.map((swatch) => {
          const isSelected = swatch.value.toLowerCase() === currentColor;
          return (
            <button
              key={swatch.value}
              type="button"
              aria-label={swatch.label}
              aria-pressed={isSelected}
              onClick={() => onValueChange(swatch.value)}
              className={`size-11 rounded-full border-2 bg-surface p-[3px] ${isSelected ? "border-accent" : "border-line"}`}
            >
              <span className="block size-full rounded-full" style={{ backgroundColor: swatch.value }} />
            </button>
          );
        })}
        <input
          type="color"
          aria-label={`Custom ${control.label.toLowerCase()}`}
          value={currentColor}
          onChange={(event) => onValueChange(event.target.value.toUpperCase())}
          className="size-11 rounded-lg border border-field bg-surface p-1"
        />
      </div>
    </fieldset>
  );
}

function ToggleField({ control, value, onValueChange }: ControlFieldProps) {
  return (
    <label className="flex min-h-11 items-center justify-between gap-3 text-sm font-medium">
      {control.label}
      <input
        type="checkbox"
        checked={Boolean(value)}
        onChange={(event) => onValueChange(event.target.checked)}
        className="size-5 accent-accent"
      />
    </label>
  );
}

// Renders one builder control from its GET /api/options description.
export function ControlField(props: ControlFieldProps) {
  if (props.control.type === "slider") return <SliderField {...props} />;
  if (props.control.type === "select") return <SelectField {...props} />;
  if (props.control.type === "color") return <ColorField {...props} />;
  return <ToggleField {...props} />;
}
