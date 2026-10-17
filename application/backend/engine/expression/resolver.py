"""Script lines -> the emotion, intensity and question brow raise each line is played with."""

import re

from engine.config import load_data_file
from engine.script.parser import ScriptLine

MIN_INTENSITY = 0.1
MAX_INTENSITY = 1.0


def find_rule_emotion(text: str, rule_words: dict[str, str]) -> str | None:
    """The emotion of the rule word that appears first in the text, or None."""
    lower_text = text.lower()
    best_position = None
    best_emotion = None
    for word, emotion in rule_words.items():
        # Unquoted yes/no keys load from YAML as booleans; skip them rather than crash.
        if not isinstance(word, str):
            continue
        # Whole words only, so "miss" does not match "mission".
        match = re.search(r"(?<![a-z'])" + re.escape(word.lower()) + r"(?![a-z'])", lower_text)
        if match and (best_position is None or match.start() < best_position):
            best_position = match.start()
            best_emotion = emotion
    return best_emotion


def resolve_emotions(lines: list[ScriptLine]) -> list[dict]:
    """[{emotion, intensity, brow_raise}] per line: the tag, else the word rules, else the speaker's previous emotion."""
    data = load_data_file("emotions.yaml")
    rules = data["rules"]
    tag_default_intensity = float(data["default_intensity"])
    rule_default_intensity = float(rules["default_intensity"])

    previous_by_speaker = {}
    resolved = []
    for line in lines:
        brow_raise = 0.0

        if line.tagged:
            emotion = line.emotion or "neutral"
            intensity = line.intensity if line.intensity is not None else tag_default_intensity
            carried_intensity = intensity
        else:
            rule_emotion = find_rule_emotion(line.text, rules["words"])
            if rule_emotion:
                emotion, intensity = rule_emotion, rule_default_intensity
            elif line.speaker in previous_by_speaker:
                emotion, intensity = previous_by_speaker[line.speaker]
            else:
                emotion, intensity = "neutral", rule_default_intensity

            # Carry the intensity from before the "!" boost, so a run of "!" lines does not keep climbing.
            carried_intensity = intensity
            if "!" in line.text:
                intensity += float(rules["exclamation_boost"])
            if "?" in line.text:
                brow_raise = float(rules["question_brow_raise"])

        intensity = min(max(intensity, MIN_INTENSITY), MAX_INTENSITY)
        previous_by_speaker[line.speaker] = (emotion, min(max(carried_intensity, MIN_INTENSITY), MAX_INTENSITY))
        resolved.append({"emotion": emotion, "intensity": round(intensity, 3), "brow_raise": brow_raise})

    return resolved
