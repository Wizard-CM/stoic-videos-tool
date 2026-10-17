import { useState } from "react";
import { getErrorMessage, renderVoiceSample, type Voice, type VoiceOption } from "../../api/client";
import { PlayIcon } from "../../components/icons";
import { ErrorMessage } from "../../components/Messages";
import { FIELD_LABEL, RANGE_INPUT, SECONDARY_BUTTON, SELECT_INPUT } from "../../components/styles";
import { getOffsetHint, offsetToSliderValue, sliderValueToOffset } from "./characterHelpers";

type VoiceSettingsProps = {
  voice: Voice;
  voices: VoiceOption[];
  autoVoiceError: string | null;
  onVoiceChange: (voice: Voice) => void;
};

export function VoiceSettings({ voice, voices, autoVoiceError, onVoiceChange }: VoiceSettingsProps) {
  const [isLoadingSample, setIsLoadingSample] = useState(false);
  const [sampleError, setSampleError] = useState<string | null>(null);

  const getVoiceLabel = (voiceOption: VoiceOption) => {
    if (voice.auto && voiceOption.id === voice.voice_id) return `${voiceOption.label} (auto)`;
    return voiceOption.label;
  };

  const handlePlaySampleClick = async () => {
    setIsLoadingSample(true);
    setSampleError(null);
    try {
      const sampleBlob = await renderVoiceSample(voice);
      const sampleUrl = URL.createObjectURL(sampleBlob);
      const sampleAudio = new Audio(sampleUrl);
      sampleAudio.addEventListener("ended", () => URL.revokeObjectURL(sampleUrl));
      await sampleAudio.play();
    } catch (error) {
      setSampleError(getErrorMessage(error));
    } finally {
      setIsLoadingSample(false);
    }
  };

  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] items-end gap-x-6 gap-y-[18px] border-t border-line pt-[18px]">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="voice-select" className={FIELD_LABEL}>
          Voice
        </label>
        <select
          id="voice-select"
          value={voice.voice_id}
          onChange={(event) => onVoiceChange({ ...voice, voice_id: event.target.value, auto: false })}
          className={SELECT_INPUT}
        >
          {voices.map((voiceOption) => (
            <option key={voiceOption.id} value={voiceOption.id}>
              {getVoiceLabel(voiceOption)}
            </option>
          ))}
        </select>
      </div>
      <button type="button" className={SECONDARY_BUTTON} disabled={isLoadingSample} onClick={handlePlaySampleClick}>
        <PlayIcon />
        {isLoadingSample ? "Making sample…" : "Play sample line"}
      </button>

      <div className="flex flex-col gap-1">
        <div className="flex justify-between text-sm">
          <label htmlFor="voice-pitch" className="font-medium">
            Pitch
          </label>
          <span className="text-muted">{getOffsetHint(voice.pitch, "lower", "higher")}</span>
        </div>
        <input
          id="voice-pitch"
          type="range"
          min={0}
          max={100}
          value={offsetToSliderValue(voice.pitch)}
          onChange={(event) => onVoiceChange({ ...voice, pitch: sliderValueToOffset(Number(event.target.value)) })}
          className={RANGE_INPUT}
        />
      </div>
      <div className="flex flex-col gap-1">
        <div className="flex justify-between text-sm">
          <label htmlFor="voice-speed" className="font-medium">
            Speed
          </label>
          <span className="text-muted">{getOffsetHint(voice.speed, "slower", "faster")}</span>
        </div>
        <input
          id="voice-speed"
          type="range"
          min={0}
          max={100}
          value={offsetToSliderValue(voice.speed)}
          onChange={(event) => onVoiceChange({ ...voice, speed: sliderValueToOffset(Number(event.target.value)) })}
          className={RANGE_INPUT}
        />
      </div>

      <ErrorMessage message={sampleError ?? autoVoiceError} />
    </div>
  );
}
