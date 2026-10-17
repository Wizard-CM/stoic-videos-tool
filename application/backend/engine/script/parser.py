"""Tagged script -> validated dialogue lines.

Format, one turn per line:  NAME [emotion, intensity]: dialogue
Blank lines and lines starting with # are notes.
"""

import difflib
import re
from dataclasses import asdict, dataclass, field

from engine.config import load_data_file

MIN_SPEAKERS = 2
MAX_SPEAKERS = 6
WORDS_PER_SECOND = 2.6
AVERAGE_PAUSE_SECONDS = 0.32

LINE_PATTERN = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 _'.\-]*?)\s*(?:\[([^\]]*)\])?\s*:\s*(.*)$")
MID_LINE_TAG_PATTERN = re.compile(r"\[[^\]]*\]")


@dataclass
class ScriptLine:
    line_no: int
    speaker: str
    emotion: str | None
    intensity: float | None
    text: str
    tagged: bool


@dataclass
class ScriptIssue:
    line_no: int | None
    level: str  # "error" or "warning"
    message: str


@dataclass
class ParsedScript:
    lines: list[ScriptLine] = field(default_factory=list)
    issues: list[ScriptIssue] = field(default_factory=list)

    @property
    def speakers(self) -> list[str]:
        speakers = []
        for line in self.lines:
            if line.speaker not in speakers:
                speakers.append(line.speaker)
        return speakers

    @property
    def errors(self) -> list[ScriptIssue]:
        return [issue for issue in self.issues if issue.level == "error"]

    @property
    def warnings(self) -> list[ScriptIssue]:
        return [issue for issue in self.issues if issue.level == "warning"]

    @property
    def estimated_length_s(self) -> float:
        word_count = sum(len(line.text.split()) for line in self.lines)
        pause_count = max(len(self.lines) - 1, 0)
        return round(word_count / WORDS_PER_SECOND + pause_count * AVERAGE_PAUSE_SECONDS, 1)

    def to_dict(self) -> dict:
        return {
            "lines": [asdict(line) for line in self.lines],
            "speakers": self.speakers,
            "issues": [asdict(issue) for issue in self.issues],
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "estimated_length_s": self.estimated_length_s,
        }


def known_emotions() -> dict[str, str]:
    """Every accepted tag word -> the preset it plays as."""
    data = load_data_file("emotions.yaml")
    names = {name: name for name in data["emotions"]}
    return {**data.get("aliases", {}), **names}


def _suggest_emotions(word: str) -> list[str]:
    presets = list(load_data_file("emotions.yaml")["emotions"])
    accepted = known_emotions()
    close_words = difflib.get_close_matches(word, list(accepted), n=3, cutoff=0.6)
    suggestions = []
    for close_word in close_words:
        preset = accepted[close_word]
        if preset not in suggestions:
            suggestions.append(preset)
    for fallback in ("angry", "sad", "neutral"):
        if len(suggestions) >= 2:
            break
        if fallback in presets and fallback not in suggestions:
            suggestions.append(fallback)
    return suggestions


def _join_with_or(words: list[str]) -> str:
    if len(words) == 1:
        return words[0]
    return ", ".join(words[:-1]) + " or " + words[-1]


def _parse_tag(tag: str, line_no: int, issues: list[ScriptIssue]) -> tuple[str, float | None]:
    parts = [part.strip() for part in tag.split(",") if part.strip()]
    if not parts:
        return "neutral", None

    emotion_word = parts[0].lower()
    intensity = None
    if len(parts) > 1:
        try:
            intensity = float(parts[1])
        except ValueError:
            issues.append(ScriptIssue(line_no, "warning", f"“{parts[1]}” isn’t a number, so the default intensity is used."))
        else:
            if not 0.1 <= intensity <= 1.0:
                clamped = min(max(intensity, 0.1), 1.0)
                issues.append(ScriptIssue(line_no, "warning", f"Intensity {intensity:g} is outside 0.1–1.0, so {clamped:g} is used."))
                intensity = clamped

    accepted = known_emotions()
    if emotion_word in accepted:
        return accepted[emotion_word], intensity

    suggestions = _join_with_or(_suggest_emotions(emotion_word))
    issues.append(ScriptIssue(line_no, "warning", f"“{emotion_word}” isn’t a known emotion, so it will play as neutral. Try {suggestions}."))
    return "neutral", intensity


def parse_script(script_text: str) -> ParsedScript:
    result = ParsedScript()

    for line_no, raw_line in enumerate(script_text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        match = LINE_PATTERN.match(stripped)
        if not match:
            result.issues.append(ScriptIssue(line_no, "error", f"Line {line_no} doesn’t follow NAME [emotion]: dialogue."))
            continue

        name, tag, text = match.group(1), match.group(2), match.group(3).strip()
        speaker = " ".join(name.split()).upper()

        if MID_LINE_TAG_PATTERN.search(text):
            result.issues.append(ScriptIssue(line_no, "warning", "Emotion tags in the middle of a line aren’t supported yet, so they are skipped."))
            text = " ".join(MID_LINE_TAG_PATTERN.sub(" ", text).split())

        if not text:
            result.issues.append(ScriptIssue(line_no, "error", f"Line {line_no} has no dialogue after the colon."))
            continue

        emotion, intensity = (None, None)
        if tag is not None:
            emotion, intensity = _parse_tag(tag, line_no, result.issues)

        result.lines.append(ScriptLine(line_no, speaker, emotion, intensity, text, tagged=tag is not None))

    speaker_count = len(result.speakers)
    if not result.lines and not result.errors:
        result.issues.append(ScriptIssue(None, "error", "The script is empty. Add lines like JADE [angry]: You knew!"))
    elif result.lines and not MIN_SPEAKERS <= speaker_count <= MAX_SPEAKERS:
        result.issues.append(ScriptIssue(None, "error", f"Use {MIN_SPEAKERS} to {MAX_SPEAKERS} speakers; this script has {speaker_count}."))

    result.issues.sort(key=lambda issue: (issue.line_no is not None, issue.line_no or 0))
    return result
