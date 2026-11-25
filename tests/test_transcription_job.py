import sys
from pathlib import Path
from time import monotonic

import pytest

from pitranscriptor import transcription_job
from pitranscriptor.transcription import recognition_confidence


def test_engine_scalar_is_serializable_and_invalid_scores_are_optional():
    numpy = pytest.importorskip("numpy")
    confidence = recognition_confidence(numpy.float64(0.75))
    assert type(confidence) is float and confidence == 0.75
    assert recognition_confidence(numpy.float32(1.0000001)) == 1.0
    assert recognition_confidence(numpy.float64("nan")) is None
    assert recognition_confidence(1.2) is None


@pytest.mark.parametrize("cancel", [True, False])
def test_unresponsive_worker_is_killed(tmp_path, monkeypatch, cancel):
    popen = transcription_job.subprocess.Popen
    children = []

    def start_sleeper(command, **kwargs):
        child = popen([sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)
        children.append((child, Path(command[-1])))
        return child

    monkeypatch.setattr(transcription_job.subprocess, "Popen", start_sleeper)
    monkeypatch.setattr(transcription_job, "STALL_SECONDS", 0.3 if not cancel else 5)
    start = monotonic()
    with pytest.raises(InterruptedError if cancel else TimeoutError):
        transcription_job.run_transcription(
            tmp_path / "audio.wav",
            tmp_path / "model",
            progress=lambda value: None,
            cancelled=lambda: cancel and monotonic() - start > 0.3,
        )
    assert len(children) == 1
    child, folder = children[0]
    assert child.poll() is not None
    assert not folder.exists()
