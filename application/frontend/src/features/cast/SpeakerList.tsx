import { useSyncExternalStore } from "react";
import type { CastEntry } from "../../api/client";
import { CharacterAvatar } from "../../components/CharacterAvatar";
import { ActiveIcon } from "../../components/icons";
import { getTaskSlotsVersion, readTaskSlot, SLOT_KEYS, subscribeToTaskSlots } from "../../lib/taskSlots";

const ACTIVE_SPEAKER = "border-[1.5px] border-accent bg-accent-tint";
const INACTIVE_SPEAKER = "border border-line bg-surface";

type SpeakerListProps = {
  projectId: string;
  speakers: string[];
  cast: Record<string, CastEntry>;
  activeSpeaker: string;
  onSpeakerSelect: (speaker: string) => void;
};

function getCharacterNote(castEntry: CastEntry | undefined) {
  if (!castEntry) return { text: "No character yet", className: "text-muted" };
  return { text: castEntry.character.name, className: "text-success" };
}

function getBackgroundNote(castEntry: CastEntry | undefined) {
  if (!castEntry) return null;
  if (castEntry.background_library_id) return `Set: ${castEntry.background?.name ?? "from library"}`;
  if (castEntry.background) return "Set designed by Claude";
  return "Claude designs the set";
}

export function SpeakerList({ projectId, speakers, cast, activeSpeaker, onSpeakerSelect }: SpeakerListProps) {
  // Re-render when a cast task starts or ends, to show "Claude is designing…".
  useSyncExternalStore(subscribeToTaskSlots, getTaskSlotsVersion);

  return (
    <section aria-label="Speakers" className="flex max-w-60 flex-[1_1_200px] flex-col gap-2.5">
      <h2 className="m-0 text-[15px] font-semibold">Speakers in script</h2>
      {speakers.map((speaker) => {
        const castEntry = cast[speaker];
        const isActive = speaker === activeSpeaker;
        const characterNote = getCharacterNote(castEntry);
        const backgroundNote = getBackgroundNote(castEntry);
        const taskSlots = [
          readTaskSlot(SLOT_KEYS.castCharacter(projectId, speaker)),
          readTaskSlot(SLOT_KEYS.castBackground(projectId, speaker)),
        ];
        const isClaudeWorking = taskSlots.some((slot) => slot !== null && !slot.stopped);
        const hasStoppedTask = taskSlots.some((slot) => slot?.stopped);

        return (
          <button
            key={speaker}
            type="button"
            aria-pressed={isActive}
            onClick={() => onSpeakerSelect(speaker)}
            className={`flex min-h-14 items-center gap-2.5 rounded-[10px] px-3 py-2 text-left ${isActive ? ACTIVE_SPEAKER : INACTIVE_SPEAKER}`}
          >
            <CharacterAvatar
              characterId={castEntry?.library_id ?? null}
              name={speaker}
              version={castEntry?.character.updated_at}
            />
            <span className="flex min-w-0 flex-col">
              <span className="text-[14.5px] font-semibold text-ink">{speaker}</span>
              <span className={`text-[13px] ${characterNote.className}`}>{characterNote.text}</span>
              {backgroundNote && <span className="text-[12.5px] text-muted">{backgroundNote}</span>}
              {isClaudeWorking && (
                <span className="flex items-center gap-1.5 text-[12.5px] text-accent-dark">
                  <ActiveIcon isSpinning size={13} />
                  Claude is working
                </span>
              )}
              {!isClaudeWorking && hasStoppedTask && (
                <span className="text-[12.5px] text-danger">Claude couldn’t finish</span>
              )}
            </span>
          </button>
        );
      })}
    </section>
  );
}
