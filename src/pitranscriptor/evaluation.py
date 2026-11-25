"""Métricas textuales para referencias revisadas; no ejecutan reconocimiento."""

import unicodedata
from collections.abc import Sequence

NORMALIZATION_POLICY = "nfc-casefold-punctuation-to-space-v1"


def normalize_text(text: str) -> str:
    """Ignorar caja/puntuación, conservar acentos y colapsar espacios."""
    text = unicodedata.normalize("NFC", text.casefold())
    return " ".join("".join(char if char.isalnum() else " " for char in text).split())


def edit_distance(reference: Sequence, hypothesis: Sequence) -> int:
    """Distancia Levenshtein con memoria proporcional a la secuencia menor."""
    if len(reference) < len(hypothesis):
        reference, hypothesis = hypothesis, reference
    previous = list(range(len(hypothesis) + 1))
    for row, expected in enumerate(reference, start=1):
        current = [row]
        for column, actual in enumerate(hypothesis, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (expected != actual),
                )
            )
        previous = current
    return previous[-1]


def _rate(reference: Sequence, hypothesis: Sequence) -> dict:
    errors = edit_distance(reference, hypothesis)
    units = len(reference)
    return {"errors": errors, "reference_units": units, "rate": errors / units if units else None}


def score_transcript(reference: str, hypothesis: str, terms: Sequence[str] = ()) -> dict:
    """Calcular WER, CER con espacios y cobertura exacta de términos/frases.

    La referencia debe haber sido revisada por una persona. El resultado no
    evalúa tiempos, hablantes, puntuación ni similitud fonética. Los términos
    esperados deben estar realmente presentes en la referencia.
    """
    expected = normalize_text(reference)
    actual = normalize_text(hypothesis)
    expected_terms: dict[str, str] = {}
    for term in terms:
        normalized = normalize_text(term)
        if not normalized or f" {normalized} " not in f" {expected} ":
            raise ValueError("Un término esperado no está presente en la referencia revisada")
        expected_terms.setdefault(normalized, term)
    matched, missing = [], []
    for normalized, label in expected_terms.items():
        (matched if f" {normalized} " in f" {actual} " else missing).append(label)
    return {
        "normalization_policy": NORMALIZATION_POLICY,
        "reference_normalized": expected,
        "hypothesis_normalized": actual,
        "wer": _rate(expected.split(), actual.split()),
        "cer_with_spaces": _rate(expected, actual),
        "terms": {"expected": len(expected_terms), "matched": matched, "missing": missing},
    }
