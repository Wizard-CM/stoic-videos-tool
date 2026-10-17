import type { CastEntry } from "../../api/client";
import { LINK_BUTTON } from "../../components/styles";

const ACTIVE_SPEAKER = "border-[1.5px] border-accent bg-accent-tint";
const INACTIVE_SPEAKER = "border border-line bg-surface";

type SpeakerListProps = {
  speakers: string[];
  cast: Record<string, CastEntry>;
  activeSpeaker: string;
  onSpeakerSelect: (speaker: string) => void;
  onPickFromLibraryClick: () => void;
};

function getSpeakerNote(castEntry: CastEntry | undefined, isActive: boolean) {
  if (!castEntry) return { text: "No character yet", className: "text-muted" };

  let noteText = "New character";
  if (castEntry.library_id) noteText = `${castEntry.character.name}, from library`;

  if (isActive) return { text: `${noteText}, editing`, className: "text-accent-dark" };
  if (castEntry.library_id) return { text: noteText, className: "text-success" };
  return { text: noteText, className: "text-muted" };
}

export function SpeakerList({ speakers, cast, activeSpeaker, onSpeakerSelect, onPickFromLibraryClick }: SpeakerListProps) {
  const hasActiveCharacter = Boolean(cast[activeSpeaker]);

  return (
    <section aria-label="Speakers" className="flex max-w-60 flex-[1_1_200px] flex-col gap-2.5">
      <h2 className="m-0 text-[15px] font-semibold">Speakers in script</h2>
      {speakers.map((speaker) => {
        const isActive = speaker === activeSpeaker;
        const speakerNote = getSpeakerNote(cast[speaker], isActive);
        return (
          <button
            key={speaker}
            type="button"
            aria-pressed={isActive}
            onClick={() => onSpeakerSelect(speaker)}
            className={`flex min-h-14 items-center gap-2.5 rounded-[10px] px-3 py-2 text-left ${isActive ? ACTIVE_SPEAKER : INACTIVE_SPEAKER}`}
          >
            <span className="inline-flex size-9 flex-none items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent-dark">
              {speaker.charAt(0)}
            </span>
            <span className="flex flex-col">
              <span className="text-[14.5px] font-semibold text-ink">{speaker}</span>
              <span className={`text-[13px] ${speakerNote.className}`}>{speakerNote.text}</span>
            </span>
          </button>
        );
      })}
      {hasActiveCharacter && (
        <button type="button" className={LINK_BUTTON} onClick={onPickFromLibraryClick}>
          Pick from library instead
        </button>
      )}
    </section>
  );
}
