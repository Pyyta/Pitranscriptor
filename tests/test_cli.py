import json
import os
import subprocess
import sys

from pitranscriptor import __version__


def test_version_entrypoint():
    result = subprocess.run(
        [sys.executable, "-m", "pitranscriptor", "--version"],
        check=True,
        text=True,
        capture_output=True,
    )
    assert result.stdout.strip() == f"Pitranscriptor {__version__}"


def test_doctor_works_without_optional_dependencies():
    # El entorno base no necesita Qt, motores ni FFmpeg para arrancar.
    result = subprocess.run(
        [sys.executable, "-m", "pitranscriptor", "doctor", "--json"],
        check=True,
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=os.environ | {"PYTHONIOENCODING": "utf-8"},
    )
    report = json.loads(result.stdout)
    assert report["stage"] == "preparacion"
    assert "ffprobe" in report["executables_on_path"]
    assert "faster-whisper" in report["packages"]
