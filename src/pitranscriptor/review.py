"""Comparar dos lecturas del mismo audio antes de sugerir un cambio."""

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from string import punctuation
from unicodedata import normalize

from pitranscriptor.project import Project
from pitranscriptor.subtitles import Word

EDGE_PUNCTUATION = punctuation.replace("+", "").replace("#", "") + "¿¡«»“”‘’…—"
MAX_TIME_DRIFT_MS = 450


def comparison_word(text: str) -> str:
    return normalize("NFC", text.strip(EDGE_PUNCTUATION)).casefold()


def with_original_punctuation(original: str, alternative: str) -> str:
    core = original.strip(EDGE_PUNCTUATION)
    prefix_length = len(original) - len(original.lstrip(EDGE_PUNCTUATION))
    new_word = alternative.strip(EDGE_PUNCTUATION)
    if core[0].isupper() and new_word[0].islower():
        new_word = new_word[0].upper() + new_word[1:]
    return original[:prefix_length] + new_word + original[prefix_length + len(core) :]


@dataclass(frozen=True)
class ReviewSuggestion:
    row: int
    word_index: int
    original: Word
    alternative: str
    before: str
    after: str
    listen_start: int
    listen_end: int


def nearby(left: Word, right: Word) -> bool:
    return abs(left.start_ms + left.end_ms - right.start_ms - right.end_ms) <= 2 * MAX_TIME_DRIFT_MS


def compare_readings(original: Project, second: Project) -> tuple[ReviewSuggestion, ...]:
    """Usar coincidencias a ambos lados y los tiempos para alinear una palabra distinta."""
    first = [
        (row, word_index, word)
        for row, cue in enumerate(original.cues)
        for word_index, word in enumerate(cue.words)
    ]
    alternate = [word for cue in second.cues for word in cue.words]
    first_keys = [comparison_word(word.text) for _, _, word in first]
    alternate_keys = [comparison_word(word.text) for word in alternate]
    alternate_times = [word.start_ms + word.end_ms for word in alternate]
    suggestions = []
    for start in range(1, len(first) - 1):
        row, index, word = first[start]
        if not first_keys[start]:
            continue
        stop = start + 1
        center = word.start_ms + word.end_ms
        lower = max(1, bisect_left(alternate_times, center - 2 * MAX_TIME_DRIFT_MS))
        upper = min(
            len(alternate) - 1, bisect_right(alternate_times, center + 2 * MAX_TIME_DRIFT_MS)
        )
        matching = [
            i
            for i in range(lower, upper)
            if (
                first_keys[start - 1] == alternate_keys[i - 1]
                and first_keys[stop] == alternate_keys[i + 1]
                and nearby(first[start - 1][2], alternate[i - 1])
                and nearby(first[stop][2], alternate[i + 1])
            )
        ]
        if len(matching) != 1:
            continue
        match = matching[0]
        candidate = alternate[match]
        if not alternate_keys[match] or alternate_keys[match] == first_keys[start]:
            continue
        if candidate.probability is None or candidate.probability < 0.4:
            continue
        left = max(0, start - 7)
        right = min(len(first), stop + 7)
        suggestions.append(
            ReviewSuggestion(
                row,
                index,
                word,
                with_original_punctuation(word.text, candidate.text),
                " ".join(item[2].text for item in first[left:start]),
                " ".join(item[2].text for item in first[stop:right]),
                first[left][2].start_ms,
                min(original.duration_ms, first[right - 1][2].end_ms + 150),
            )
        )
    return tuple(suggestions)
