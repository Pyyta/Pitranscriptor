import math
import struct
import wave

import pytest

from pitranscriptor.audio import file_sha256, prepare_audio

pytest.importorskip("av")


def make_wave(path, *, seconds=0.1, channels=1):
    samples = [
        int(10000 * math.sin(2 * math.pi * 440 * index / 44100))
        for index in range(int(44100 * seconds))
    ]
    with wave.open(str(path), "wb") as audio:
        audio.setparams((channels, 2, 44100, 0, "NONE", "not compressed"))
        audio.writeframes(b"".join(struct.pack("<h", value) * channels for value in samples))


@pytest.mark.parametrize("channels", [1, 2])
def test_resampling_preserves_original_and_duration(tmp_path, channels):
    source = tmp_path / "original.wav"
    destination = tmp_path / "corpus" / "copy.wav"
    make_wave(source, channels=channels)
    before = source.read_bytes()
    result = prepare_audio(source, destination)
    assert source.read_bytes() == before
    assert result.source_sha256 == file_sha256(source)
    assert result.output_sha256 == file_sha256(destination)
    assert result.duration_seconds == pytest.approx(0.1, abs=1 / 16000)
    with wave.open(str(destination), "rb") as audio:
        assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) == (1, 2, 16000)
        assert any(audio.readframes(audio.getnframes()))


def test_refuses_to_replace_existing_output(tmp_path):
    source = tmp_path / "original.wav"
    make_wave(source)
    destination = tmp_path / "existing.wav"
    destination.write_bytes(b"existing work")
    with pytest.raises(FileExistsError):
        prepare_audio(source, destination)
    assert destination.read_bytes() == b"existing work"


def test_refuses_original_as_destination(tmp_path):
    source = tmp_path / "original.wav"
    make_wave(source)
    original = source.read_bytes()
    with pytest.raises(ValueError):
        prepare_audio(source, source)
    assert source.read_bytes() == original


def test_failed_decode_does_not_leave_output(tmp_path):
    source = tmp_path / "broken.wav"
    source.write_bytes(b"not audio")
    destination = tmp_path / "copy.wav"
    with pytest.raises(ValueError, match="decodificar"):
        prepare_audio(source, destination)
    assert not destination.exists()


def test_oversized_audio_is_not_silently_trimmed(tmp_path, monkeypatch):
    source = tmp_path / "long.wav"
    make_wave(source)
    destination = tmp_path / "copy.wav"
    monkeypatch.setattr("pitranscriptor.audio.MAX_DURATION_SECONDS", 0.05)
    with pytest.raises(ValueError, match="cinco minutos"):
        prepare_audio(source, destination)
    assert not destination.exists()


def test_recognizer_can_decode_prepared_audio(tmp_path):
    # Importar el motor no detecta incompatibilidades en su decodificador PyAV.
    decoder = pytest.importorskip("faster_whisper.audio")
    source = tmp_path / "original.wav"
    destination = tmp_path / "prepared.wav"
    make_wave(source)
    prepare_audio(source, destination)
    decoded = decoder.decode_audio(str(destination), sampling_rate=16000)
    assert len(decoded) == 1600
    assert decoded.dtype.name == "float32"
    assert abs(decoded).max() > 0
