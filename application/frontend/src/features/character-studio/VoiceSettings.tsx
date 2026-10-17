import { useState } from "react";
import { getErrorMessage, renderVoiceSample, type Voice, type VoiceOption } from "../../api/client";
import { PlayIcon } from "../../components/icons";
import { ErrorMessage } from "../../components/Messages";
import { FIELD_LABEL, RANGE_INPUT, SECONDARY_BUTTON, SELECT_INPUT } from "../../components/styles";
import { capitalize } from "../../lib/format";

type VoiceSettingsProps = {
  voice: Voice;
  voices: VoiceOption[];
  gender: string | null;
  age: string | null;
  onVoiceChange: (voice: Voice) => void;
};

// "Lower" / "Slightly lower" / "Normal" / "Slightly higher" / "Higher" for a -1..1 voice offset.
function getOffsetHint(offset: number, lowerWord: string, higherWord: string) {
  if (offset <= -0.5) return capitalize(lowerWord);
  if (offset < -0.05) return `Slightly ${lowerWord}`;
  if (offset <= 0.05) return "Normal";
  if (offset < 0.5) return `Slightly ${higherWord}`;
  return capitalize(higherWord);
}

// Voice offsets are -1..1 but the sliders show 0..100.
function offsetToSliderValue(offset: number) {
  return Math.round((offset + 1) * 50);
}

function sliderValueToOffset(sliderValue: number) {
  return sliderValue / 50 - 1;
}

// Voices that match the character's gender, always keeping the current one.
function getVoiceChoices(voices: VoiceOption[], gender: string | null, currentVoiceId: string) {
  const matchingVoices = voices.filter((voiceOption) => voiceOption.gender === gender || voiceOption.id === currentVoiceId);
  const hasGenderMatch = matchingVoices.some((voiceOption) => voiceOption.id !== currentVoiceId);
  return gender && hasGenderMatch ? matchingVoices : voices;
}

type OffsetSliderProps = {
  id: string;
  label: string;
  value: number;
  lowerWord: string;
  higherWord: string;
  onValueChange: (value: number) => void;
};

function OffsetSlider({ id, label, value, lowerWord, higherWord, onValueChange }: OffsetSliderProps) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-sm">
        <label htmlFor={id} className="font-medium">
          {label}
        </label>
        <span className="text-muted">{getOffsetHint(value, lowerWord, higherWord)}</span>
      </div>
      <input
        id={id}
        type="range"
        min={0}
        max={100}
        value={offsetToSliderValue(value)}
        onChange={(event) => onValueChange(sliderValueToOffset(Number(event.target.value)))}
        className={RANGE_INPUT}
      />
    </div>
  );
}

export function VoiceSettings({ voice, voices, gender, age, onVoiceChange }: VoiceSettingsProps) {
  const [isLoadingSample, setIsLoadingSample] = useState(false);
  const [sampleError, setSampleError] = useState<string | null>(null);

  const voiceChoices = getVoiceChoices(voices, gender, voice.voice_id);

  const getVoiceLabel = (voiceOption: VoiceOption) => {
    if (voice.auto && voiceOption.id === voice.voice_id) return `${voiceOption.label} (auto)`;
    return voiceOption.label;
  };

  const handlePlaySampleClick = async () => {
    setIsLoadingSample(true);
    setSampleError(null);
    try {
      const sampleBlob = await renderVoiceSample(voice, age);
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
    <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] items-end gap-x-6 gap-y-[18px]">
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
          {voiceChoices.map((voiceOption) => (
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

      <OffsetSlider
        id="voice-pitch"
        label="Pitch"
        value={voice.pitch}
        lowerWord="lower"
        higherWord="higher"
        onValueChange={(pitch) => onVoiceChange({ ...voice, pitch })}
      />
      <OffsetSlider
        id="voice-speed"
        label="Speed"
        value={voice.speed}
        lowerWord="slower"
        higherWord="faster"
        onValueChange={(speed) => onVoiceChange({ ...voice, speed })}
      />

      <ErrorMessage message={sampleError} />
    </div>
  );
}
