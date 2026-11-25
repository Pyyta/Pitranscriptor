import pytest

from pitranscriptor.evaluation import normalize_text, score_transcript


def test_case_punctuation_and_unicode_composition_are_normalized():
    assert normalize_text("  ÁRBOL, Docker... ") == "árbol docker"
    result = score_transcript("Árbol, Docker.", "a\u0301rbol docker")
    assert result["wer"]["rate"] == 0
    assert result["cer_with_spaces"]["rate"] == 0


def test_word_errors_include_substitutions_insertions_and_deletions():
    assert score_transcript("hola Docker", "hola Linux")["wer"]["rate"] == 0.5
    assert score_transcript("hola Docker", "hola y Docker")["wer"]["rate"] == 0.5
    assert score_transcript("hola Docker", "hola")["wer"]["rate"] == 0.5


def test_character_error_rate_keeps_spaces_and_accents():
    result = score_transcript("a b", "a c")
    assert result["cer_with_spaces"] == {"errors": 1, "reference_units": 3, "rate": 1 / 3}
    assert score_transcript("sí", "si")["cer_with_spaces"]["errors"] == 1


def test_silence_reports_insertions_without_undefined_percentage():
    result = score_transcript("", "hola")
    assert result["wer"] == {"errors": 1, "reference_units": 0, "rate": None}
    assert result["cer_with_spaces"]["rate"] is None


def test_empty_hypothesis_and_rates_over_one_are_valid():
    assert score_transcript("hola", "")["wer"]["rate"] == 1
    assert score_transcript("hola", "hola otra palabra")["wer"]["rate"] == 2


def test_terms_require_complete_tokens_and_phrases():
    result = score_transcript(
        "Arch Linux y Docker", "Linux y Dockerfile", ["Arch Linux", "Docker", "docker"]
    )
    assert result["terms"] == {"expected": 2, "matched": [], "missing": ["Arch Linux", "Docker"]}
    matched = score_transcript("Arch Linux", "ARCH LINUX", ["Arch Linux"])
    assert matched["terms"]["matched"] == ["Arch Linux"]


def test_terms_not_spoken_in_reference_are_rejected():
    with pytest.raises(ValueError, match="referencia"):
        score_transcript("hola", "hola Docker", ["Docker"])
