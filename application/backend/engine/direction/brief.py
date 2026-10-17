"""The brief: what the director reads (the script with exact voice timings and the cast). Format in docs/DIRECTION.md."""

from engine.puppet.kit import kit_summary


def speakers_in_order(lines: list[dict]) -> list[str]:
    speakers = []
    for line in lines:
        if line["speaker"] not in speakers:
            speakers.append(line["speaker"])
    return speakers


def cast_entry(character: dict, has_background: bool) -> dict:
    summary = kit_summary(character["kit"])
    return {
        "name": character.get("name") or "",
        "description": character.get("description") or "",
        "expressions": list(summary["expressions"]),
        "gestures": list(summary["gestures"]),
        "has_background": has_background,
    }


def make_brief(title: str, aspect: str, fps: int, lines: list[dict], cast: dict, backgrounds: dict) -> dict:
    """lines: [{"index", "speaker", "text", "emotion", "intensity", "duration", "words"}]; backgrounds: {SPEAKER: art or None}."""
    speakers = speakers_in_order(lines)
    return {
        "title": title or "",
        "aspect": aspect,
        "fps": fps,
        "speakers": speakers,
        "lines": [
            {
                "index": line["index"],
                "speaker": line["speaker"],
                "text": line["text"],
                "emotion": line["emotion"],
                "intensity": round(float(line["intensity"]), 2),
                "duration": round(float(line["duration"]), 3),
                "words": [{"word": word["word"], "start": word["start"], "end": word["end"]} for word in line["words"]],
            }
            for line in lines
        ],
        "cast": {speaker: cast_entry(cast[speaker], backgrounds.get(speaker) is not None) for speaker in speakers},
    }
