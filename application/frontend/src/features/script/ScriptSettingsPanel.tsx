import type { Options, ProjectSettings } from "../../api/client";
import { ErrorMessage } from "../../components/Messages";
import { FIELD_LABEL, PRIMARY_BUTTON, SELECT_INPUT, TEXT_INPUT } from "../../components/styles";
import { formatDuration } from "../../lib/format";

const SELECTED_CHOICE = "border-[1.5px] border-accent bg-accent-tint";
const UNSELECTED_CHOICE = "border border-field";

type ScriptSettingsPanelProps = {
  options: Options;
  title: string;
  settings: ProjectSettings;
  estimatedLengthSeconds: number;
  isContinueDisabled: boolean;
  continueError: string | null;
  onTitleChange: (title: string) => void;
  onSettingsChange: (settings: ProjectSettings) => void;
  onContinueClick: () => void;
};

export function ScriptSettingsPanel({
  options,
  title,
  settings,
  estimatedLengthSeconds,
  isContinueDisabled,
  continueError,
  onTitleChange,
  onSettingsChange,
  onContinueClick,
}: ScriptSettingsPanelProps) {
  const lengthLimitMinutes = Math.round(options.max_length_s / 60);
  const isOverLengthLimit = estimatedLengthSeconds > options.max_length_s;

  return (
    <aside
      aria-label="Video settings"
      className="flex min-w-0 flex-[1_1_300px] flex-col gap-5 rounded-xl border border-line bg-surface p-5"
    >
      <h2 className="m-0 text-[17px] font-semibold">Video settings</h2>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="project-title" className={FIELD_LABEL}>
          Title
        </label>
        <input
          id="project-title"
          type="text"
          value={title}
          onChange={(event) => onTitleChange(event.target.value)}
          className={TEXT_INPUT}
        />
      </div>

      <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
        <legend className={`mb-2 p-0 ${FIELD_LABEL}`}>Aspect ratio</legend>
        <div className="grid grid-cols-2 gap-2">
          {options.aspects.map((aspect) => (
            <label
              key={aspect.value}
              className={`flex min-h-11 items-center gap-2 rounded-lg px-3 text-[14.5px] ${settings.aspect === aspect.value ? SELECTED_CHOICE : UNSELECTED_CHOICE}`}
            >
              <input
                type="radio"
                name="aspect"
                value={aspect.value}
                checked={settings.aspect === aspect.value}
                onChange={() => onSettingsChange({ ...settings, aspect: aspect.value })}
                className="accent-accent"
              />
              {aspect.label}
            </label>
          ))}
        </div>
      </fieldset>

      <label className="flex min-h-11 items-center justify-between gap-3 text-[14.5px] font-medium">
        Background music
        <input
          type="checkbox"
          checked={settings.music}
          onChange={(event) => onSettingsChange({ ...settings, music: event.target.checked })}
          className="size-5 accent-accent"
        />
      </label>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="project-quality" className={FIELD_LABEL}>
          Quality
        </label>
        <select
          id="project-quality"
          value={settings.quality}
          onChange={(event) => onSettingsChange({ ...settings, quality: event.target.value })}
          className={SELECT_INPUT}
        >
          {options.qualities.map((quality) => (
            <option key={quality.value} value={quality.value}>
              {quality.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1 rounded-lg bg-page p-3.5">
        <p className="m-0 text-sm text-muted">Estimated length</p>
        <p className="m-0 text-2xl font-semibold">About {formatDuration(estimatedLengthSeconds)}</p>
        <p className="m-0 text-[13px] text-muted">
          Exact length is set once voices are made. Limit {lengthLimitMinutes} min.
        </p>
        {isOverLengthLimit && (
          <p className="m-0 text-[13px] text-danger">
            This is over the {lengthLimitMinutes} min limit. Shorten the script before rendering.
          </p>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <button
          type="button"
          className={`${PRIMARY_BUTTON} min-h-[46px]`}
          disabled={isContinueDisabled}
          onClick={onContinueClick}
        >
          Continue to cast
        </button>
        <ErrorMessage message={continueError} />
      </div>
    </aside>
  );
}
