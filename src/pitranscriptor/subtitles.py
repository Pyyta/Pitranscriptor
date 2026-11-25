"""Palabras temporizadas, fragmentos editables y formatos de texto."""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from math import isfinite
from xml.sax.saxutils import escape

MAX_WORDS = 7
MAX_MEDIA_MS = 300_000


def check_times(start_ms: int, end_ms: int) -> None:
    if (
        type(start_ms) is not int
        or type(end_ms) is not int
        or not 0 <= start_ms < end_ms <= MAX_MEDIA_MS
    ):
        raise ValueError("El intervalo debe estar entre 0 y 300 segundos y tener duración positiva")


@dataclass(frozen=True)
class Word:
    text: str
    start_ms: int
    end_ms: int

    def __post_init__(self):
        check_times(self.start_ms, self.end_ms)
        if len(self.text.split()) != 1 or self.text != self.text.strip():
            raise ValueError("Cada palabra temporizada debe contener un solo elemento")


@dataclass(frozen=True)
class Style:
    x: float = 0.5
    y: float = 0.85
    size: int = 48
    color: str = "#ffffff"
    background: str = "#111111"
    opacity: float = 0.75
    bold: bool = True
    font: str = ""
    outline: str = "#000000"
    shadow: bool = False
    align: str = "center"
    highlight: str = "#ffdc68"
    effect: str = "none"

    def __post_init__(self):
        for number in (self.x, self.y, self.opacity):
            if type(number) not in (float, int) or not isfinite(number) or not 0 <= number <= 1:
                raise ValueError("Posición y opacidad deben estar entre 0 y 1")
        if type(self.size) is not int or not 12 <= self.size <= 200:
            raise ValueError("El tamaño debe estar entre 12 y 200")
        for color in (self.color, self.background, self.outline, self.highlight):
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
                raise ValueError("Usa colores hexadecimales de seis dígitos")
        if type(self.bold) is not bool or type(self.shadow) is not bool:
            raise ValueError("Negrita y sombra deben ser valores booleanos")
        if not isinstance(self.font, str):
            raise ValueError("La tipografía debe ser texto")
        if self.align not in ("left", "center", "right"):
            raise ValueError("Alineación desconocida")
        if self.effect not in ("none", "highlight", "appear", "fade"):
            raise ValueError("Efecto desconocido")


@dataclass(frozen=True)
class Cue:
    start_ms: int
    end_ms: int
    text: str
    words: tuple[Word, ...] = ()
    style: Style = field(default_factory=Style)
    speaker: str = ""

    def __post_init__(self):
        check_times(self.start_ms, self.end_ms)
        if not 1 <= len(self.text.split()) <= MAX_WORDS:
            raise ValueError("Cada fragmento debe contener entre una y siete palabras")
        if self.words and tuple(self.text.split()) != tuple(word.text for word in self.words):
            raise ValueError("El texto y las palabras temporizadas del fragmento deben coincidir")
        if any(
            word.start_ms < self.start_ms or word.end_ms > self.end_ms for word in self.words
        ) or any(a.end_ms > b.start_ms for a, b in zip(self.words, self.words[1:], strict=False)):
            raise ValueError("Las palabras deben estar ordenadas dentro del fragmento")
        if not isinstance(self.speaker, str):
            raise ValueError("El hablante debe ser texto")


def fragment_words(words: Iterable[Word], target: int = 4, pause_ms: int = 380) -> tuple[Cue, ...]:
    """Cerrar en pausa o final de frase, con un objetivo flexible y un máximo de siete."""
    if type(target) is not int or not 1 <= target <= MAX_WORDS or pause_ms < 0:
        raise ValueError("Objetivo o umbral de pausa inválido")
    items = tuple(words)
    if any(a.end_ms > b.start_ms for a, b in zip(items, items[1:], strict=False)):
        raise ValueError("Las palabras deben estar ordenadas y no solaparse")
    cues = []
    start = 0
    while start < len(items):
        limit = min(start + MAX_WORDS, len(items))
        stop = min(start + target, limit)
        for index in range(start, limit):
            at_end = index + 1 == len(items)
            pause = not at_end and items[index + 1].start_ms - items[index].end_ms >= pause_ms
            ends_phrase = items[index].text.rstrip('”"’»)]').endswith((".", "?", "!", ";"))
            if at_end or pause or ends_phrase:
                stop = index + 1
                break
        chunk = items[start:stop]
        cues.append(
            Cue(chunk[0].start_ms, chunk[-1].end_ms, " ".join(w.text for w in chunk), chunk)
        )
        start = stop
    return tuple(cues)


def _timestamp(ms: int, separator: str) -> str:
    seconds, milliseconds = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}{separator}{milliseconds:03}"


def render_subtitles(cues: Sequence[Cue], *, webvtt: bool) -> str:
    blocks = []
    for index, cue in enumerate(cues, 1):
        separator = "." if webvtt else ","
        time = f"{_timestamp(cue.start_ms, separator)} --> {_timestamp(cue.end_ms, separator)}"
        text = " ".join(cue.text.split())
        # Ambos formatos admiten marcado. El texto de edición debe verse literalmente.
        blocks.append(f"{index}\n{time}\n{escape(text)}")
    prefix = "WEBVTT\n\n" if webvtt else ""
    return prefix + ("\n\n".join(blocks) + "\n" if blocks else "")
