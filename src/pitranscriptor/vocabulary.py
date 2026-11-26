"""Catálogo integrado de pistas para el reconocedor."""

import json
from dataclasses import dataclass
from functools import cache
from importlib.resources import files

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
