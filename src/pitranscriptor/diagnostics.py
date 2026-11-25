"""Inspección local sin cargar motores, descargar modelos ni acceder a la red."""

import platform
import shutil
from importlib.metadata import PackageNotFoundError, version

from pitranscriptor import __version__


def environment_report() -> dict:
    packages = {}
    for name in ("PySide6-Essentials", "faster-whisper", "ctranslate2"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {
        "application": "Pitranscriptor",
        "version": __version__,
        "stage": "preparacion",
        "system": platform.system(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "python_baseline": "3.12",
        "packages": packages,
        "executables_on_path": {
            name: shutil.which(name) is not None for name in ("ffmpeg", "ffprobe")
        },
        "note": "Presencia de dependencias; no certifica reconocimiento, GPU ni códecs.",
    }
