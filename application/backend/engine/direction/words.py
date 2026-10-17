"""Word timings estimated from the audio: the words are spread over the voiced part of the clip, weighted by syllables."""

import re

VOICED_SHARE = 0.12  # a frame is voiced when its loudness is above this share of the loudest frame
MIN_WORD_SECONDS = 0.04
VOWEL_GROUPS = re.compile(r"[aeiouy]+")
DIGITS_PER_SYLLABLE = 2


def word_tokens(text: str) -> list[str]:
    """The words of a line as written (punctuation stays attached, like "me?"). Tokens without letters or digits are skipped."""
    return [token for token in text.split() if any(character.isalnum() for character in token)]


def syllable_count(word: str) -> int:
    """A rough syllable count: vowel groups, minus a silent final e. Numbers count one syllable per two digits."""
    letters = "".join(character for character in word.lower() if character.isalpha())
    digits = sum(1 for character in word if character.isdigit())
    count = len(VOWEL_GROUPS.findall(letters))
    if letters.endswith("e") and not letters.endswith(("le", "ee", "ye")) and count > 1:
        count -= 1
    count += (digits + DIGITS_PER_SYLLABLE - 1) // DIGITS_PER_SYLLABLE
    return max(count, 1)


def voiced_spans(envelope: list[float], fps: int, duration: float) -> list[tuple[float, float]]:
    """(start, end) seconds of each run of voiced frames, clipped to the clip. The whole clip when nothing is voiced."""
    loudest = max(envelope, default=0.0)
    if loudest <= 0.0:
        return [(0.0, duration)]

    spans: list[tuple[float, float]] = []
    run_start = None
    for frame, level in enumerate(envelope + [0.0]):
        voiced = level > VOICED_SHARE * loudest and frame < len(envelope)
        if voiced and run_start is None:
            run_start = frame
        elif not voiced and run_start is not None:
            start, end = min(run_start / fps, duration), min(frame / fps, duration)
            if end > start:
                spans.append((start, end))
            run_start = None
    return spans or [(0.0, duration)]


def voiced_to_clip_time(spans: list[tuple[float, float]], voiced_time: float, is_start: bool) -> float:
    """Maps a position along the joined voiced spans back to clip time. A word start on a span edge goes to the next span."""
    elapsed = 0.0
    for position, (start, end) in enumerate(spans):
        length = end - start
        is_last = position == len(spans) - 1
        if voiced_time < elapsed + length or (not is_start and voiced_time <= elapsed + length) or is_last:
            return min(start + max(voiced_time - elapsed, 0.0), end)
        elapsed += length
    return spans[-1][1]


def estimate_words(text: str, envelope: list[float], fps: int, duration: float) -> list[dict]:
    """[{"word", "start", "end"}] in seconds from the line start, in order, inside 0..duration."""
    words = word_tokens(text)
    if not words or duration <= 0:
        return []

    spans = voiced_spans(list(envelope), fps, duration)
    voiced_total = sum(end - start for start, end in spans)
    weights = [syllable_count(word) for word in words]
    weight_total = sum(weights)

    estimates = []
    weight_before = 0
    previous_end = 0.0
    for word, weight in zip(words, weights, strict=True):
        start = voiced_to_clip_time(spans, voiced_total * weight_before / weight_total, is_start=True)
        weight_before += weight
        end = voiced_to_clip_time(spans, voiced_total * weight_before / weight_total, is_start=False)
        start = min(max(start, previous_end), duration)
        end = min(max(end, start + MIN_WORD_SECONDS), duration)
        estimates.append({"word": word, "start": round(start, 3), "end": round(end, 3)})
        previous_end = end
    return estimates
