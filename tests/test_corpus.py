import json
import wave
from pathlib import Path

import pytest

from pitranscriptor.cli import main
from pitranscriptor.corpus import validate_corpus


def write_wave(path, *, rate=16000, seconds=0.01):
    with wave.open(str(path), "wb") as audio:
        audio.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        audio.writeframes(b"\0\0" * int(rate * seconds))


@pytest.fixture
def corpus(tmp_path):
    write_wave(tmp_path / "clip.wav")
    data = {
        "schema_version": 1,
        "samples": [
            {
                "id": "clip",
                "audio": "clip.wav",
                "reference_text": "Probamos Docker and Linux.",
                "tags": ["mixed", "tech"],
                "terms": ["Docker", "Linux"],
                "permission_for_local_evaluation": True,
                "reference_reviewed": True,
            }
        ],
    }
    manifest = tmp_path / "manifest.json"

    def save():
        manifest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return manifest

    return data, save


def test_valid_local_corpus(corpus):
    _, save = corpus
    report = validate_corpus(save())
    assert report.ok
    assert report.sample_count == 1
    assert report.duration_seconds == pytest.approx(0.01)


@pytest.mark.parametrize("field", ["permission_for_local_evaluation", "reference_reviewed"])
@pytest.mark.parametrize("value", [False, "true", 1])
def test_requires_explicit_permission_and_review(corpus, field, value):
    data, save = corpus
    data["samples"][0][field] = value
    assert not validate_corpus(save()).ok


@pytest.mark.parametrize("path", ["../outside.wav", "/outside.wav", "C:/outside.wav", "a\\b.wav"])
def test_rejects_nonportable_or_external_paths(corpus, path):
    data, save = corpus
    data["samples"][0]["audio"] = path
    assert not validate_corpus(save()).ok


def test_rejects_symlink_to_external_audio(corpus, tmp_path):
    data, save = corpus
    outside = tmp_path.parent / f"{tmp_path.name}-outside.wav"
    write_wave(outside)
    link = tmp_path / "linked.wav"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("El sistema no permite crear enlaces simbólicos en este entorno")
    data["samples"][0]["audio"] = "linked.wav"
    report = validate_corpus(save())
    assert not report.ok
    assert "carpeta del manifiesto" in report.issues[0]


def test_rejects_duplicate_ids_and_audio(corpus):
    data, save = corpus
    data["samples"].append(dict(data["samples"][0]))
    report = validate_corpus(save())
    assert not report.ok
    assert any("id repetido" in issue for issue in report.issues)
    assert any("audio repetido" in issue for issue in report.issues)


@pytest.mark.parametrize("rate,seconds", [(8000, 0.01), (16000, 0), (16000, 301)])
def test_rejects_invalid_audio_format_or_duration(corpus, rate, seconds):
    _, save = corpus
    manifest = save()
    write_wave(manifest.parent / "clip.wav", rate=rate, seconds=seconds)
    assert not validate_corpus(manifest).ok


def test_rejects_truncated_wave(corpus):
    _, save = corpus
    manifest = save()
    audio = manifest.parent / "clip.wav"
    audio.write_bytes(audio.read_bytes()[:-1])
    assert not validate_corpus(manifest).ok


def test_silence_requires_empty_reference(corpus):
    data, save = corpus
    data["samples"][0]["tags"] = ["silence"]
    assert not validate_corpus(save()).ok
    data["samples"][0]["reference_text"] = ""
    assert validate_corpus(save()).ok


@pytest.mark.parametrize(
    "content", ["{", "[]", '{"schema_version": true}', '{"schema_version": 2}']
)
def test_invalid_manifest_returns_error(tmp_path, content):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(content, encoding="utf-8")
    assert not validate_corpus(manifest).ok


def test_missing_manifest_has_nonzero_cli_exit(tmp_path, capsys):
    assert main(["validate-corpus", str(tmp_path / "missing.json")]) == 1
    assert "JSON" in capsys.readouterr().err


def test_public_scripts_cover_vocabulary_and_require_confirmation():
    root = Path(__file__).resolve().parents[1]
    template = json.loads((root / "data/templates/corpus.example.json").read_text(encoding="utf-8"))
    vocabulary = (root / "docs/vocabulario.md").read_text(encoding="utf-8").splitlines()[4:]
    scripts = " ".join(sample["reference_text"] for sample in template["samples"]).casefold()
    for term in filter(str.strip, vocabulary):
        assert term.casefold() in scripts, f"El guion no cubre {term}"
    for sample in template["samples"]:
        assert sample["permission_for_local_evaluation"] is False
        assert sample["reference_reviewed"] is False
