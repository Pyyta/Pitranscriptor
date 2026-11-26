"""Catálogo integrado de pistas para el reconocedor."""

import json
import re
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from unicodedata import normalize

MAX_TECHNICAL_HINTS = 20


@dataclass(frozen=True)
class TermGroup:
    id: str
    es: str
    en: str
    terms: tuple[str, ...]


@cache
def technical_groups() -> tuple[TermGroup, ...]:
    resource = files("pitranscriptor").joinpath("technical_vocabulary.json")
    data = json.loads(resource.read_text(encoding="utf-8"))
    return tuple(
        TermGroup(entry["id"], entry["es"], entry["en"], tuple(entry["terms"])) for entry in data
    )


@cache
def script_term_patterns() -> tuple[tuple[str, re.Pattern[str]], ...]:
    patterns = []
    for group in technical_groups():
        for term in group.terms:
            # Palabras breves como «vi» y «DoS» también aparecen en prosa ordinaria.
            short_word = len(term) <= 3 and term.isalpha()
            if short_word and term.islower():
                continue
            body = r"\s+".join(re.escape(token) for token in term.split())
            flags = 0 if short_word else re.IGNORECASE
            patterns.append((term, re.compile(rf"(?<!\w){body}(?!\w)", flags)))
    return tuple(patterns)


def suggest_script_terms(script: str) -> tuple[str, ...]:
    """Ofrecer palabras del catálogo presentes en el guion, sin activar ninguna."""
    text = normalize("NFC", script)
    matches = []
    for term, pattern in script_term_patterns():
        matches.extend((hit.start(), -hit.end(), term) for hit in pattern.finditer(text))

    ordered = {}
    end = -1
    for start, negative_end, term in sorted(matches):
        if start >= end:
            ordered[term] = None
            end = -negative_end
    return tuple(ordered)
