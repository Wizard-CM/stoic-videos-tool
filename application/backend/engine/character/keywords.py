"""Keyword auto-fill: description text -> character params, using data/keywords.yaml (no AI)."""

import re
from copy import deepcopy

from engine.character.params import normalize_character
from engine.config import load_data_file

CHUNK_SPLIT_PATTERN = re.compile(r"[,;.\n]|\band\b|\bwith\b")
WORD_PATTERN = re.compile(r"[a-z0-9][a-z0-9'\-]*")


def _find_in_order(phrase_words: list[str], chunk_words: list[str]) -> list[int] | None:
    """Indexes of the phrase words inside the chunk, in order, allowing one extra word between them."""
    for start, word in enumerate(chunk_words):
        if word != phrase_words[0]:
            continue
        positions = [start]
        for phrase_word in phrase_words[1:]:
            last = positions[-1]
            window = chunk_words[last + 1:last + 3]
            if phrase_word not in window:
                break
            positions.append(last + 1 + window.index(phrase_word))
        if len(positions) == len(phrase_words):
            return positions
    return None


def _apply_settings(character: dict, settings: dict) -> None:
    for key, value in settings.items():
        if "." in key:
            group, field = key.split(".", 1)
            character.setdefault(group, {})[field] = value
        else:
            character["params"][key] = value


def autofill_character(description: str, character: dict) -> tuple[dict, list[str], list[str]]:
    """Returns (updated character, applied labels, words that were not understood)."""
    data = load_data_file("keywords.yaml")
    result = deepcopy(character)
    result["description"] = description

    chunks = [WORD_PATTERN.findall(chunk) for chunk in CHUNK_SPLIT_PATTERN.split(description.lower())]
    chunks = [chunk for chunk in chunks if chunk]
    used_positions = [set() for _ in chunks]
    matched_labels: list[str] = []
    later_entries: list[dict] = []

    def add_label(label: str) -> None:
        if label not in matched_labels:
            matched_labels.append(label)

    phrase_entries = sorted(data["phrases"], key=lambda entry: not entry.get("first", False))
    for entry in phrase_entries:
        alternatives = sorted(entry["words"], key=lambda phrase: -len(phrase.split()))
        for chunk_index, chunk_words in enumerate(chunks):
            for phrase in alternatives:
                positions = _find_in_order(phrase.split(), chunk_words)
                if positions is None:
                    continue
                used_positions[chunk_index].update(positions)
                add_label(entry.get("label") or phrase.capitalize())
                if entry.get("first"):
                    _apply_settings(result, entry.get("set", {}))
                else:
                    later_entries.append(entry)
                break

    # Gender is settled now, so gender-dependent choices can be applied.
    for entry in later_entries:
        _apply_settings(result, entry.get("set", {}))
        gender_settings = entry.get("set_by_gender", {}).get(result["params"]["gender"], {})
        _apply_settings(result, gender_settings)

    palettes = data["colors"]
    for target in data["color_targets"]:
        palette = palettes[target["palette"]]
        for chunk_index, chunk_words in enumerate(chunks):
            for noun_index, word in enumerate(chunk_words):
                if word not in target["nouns"]:
                    continue
                color_name = None
                for color_words in (chunk_words[max(noun_index - 2, 0):noun_index], chunk_words[noun_index - 1:noun_index]):
                    candidate = " ".join(color_words)
                    if candidate in palette:
                        color_name = candidate
                        color_positions = range(noun_index - len(color_words), noun_index)
                        break
                if color_name is None:
                    # Allow one word in between: "grey bushy eyebrows" -> grey
                    if noun_index >= 2 and chunk_words[noun_index - 2] in palette:
                        color_name = chunk_words[noun_index - 2]
                        color_positions = [noun_index - 2]
                    else:
                        continue
                result["params"][target["param"]] = palette[color_name]
                _apply_settings(result, target.get("also", {}))
                used_positions[chunk_index].update(color_positions)
                used_positions[chunk_index].add(noun_index)
                add_label(f"{color_name.capitalize()} {word}")

    stopwords = set(data.get("stopwords", []))
    unmatched = []
    for chunk_index, chunk_words in enumerate(chunks):
        leftover = [
            word for position, word in enumerate(chunk_words)
            if position not in used_positions[chunk_index] and word not in stopwords
        ]
        if leftover:
            unmatched.append(" ".join(leftover))

    return normalize_character(result), matched_labels, unmatched
