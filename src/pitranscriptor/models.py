"""Instalación explícita de modelos de referencia."""

from dataclasses import dataclass
from pathlib import Path

MODEL_FILES = ("model.bin", "config.json", "tokenizer.json")


@dataclass(frozen=True)
class ModelPreset:
    name: str
    directory: str
    repo: str
    revision: str
    size_mb: int


SMALL_MODEL = ModelPreset(
    "Small",
    "faster-whisper-small",
    "Systran/faster-whisper-small",
    "536b0662742c02347bc0e980a01041f333bce120",
    490,
)
MEDIUM_MODEL = ModelPreset(
    "Medium",
    "medium",
    "Systran/faster-whisper-medium",
    "08e178d48790749d25932bbc082711ddcfdfbc4f",
    1530,
)
TURBO_MODEL = ModelPreset(
    "Large-v3-turbo",
    "turbo",
    "dropbox-dash/faster-whisper-large-v3-turbo",
    "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf",
    1620,
)


def model_ready(path: Path) -> bool:
    return all((path / name).is_file() for name in MODEL_FILES)


def download_model(preset: ModelPreset, destination: Path) -> Path:
    from huggingface_hub import snapshot_download

    path = Path(
        snapshot_download(
            preset.repo,
            revision=preset.revision,
            local_dir=destination,
            token=False,
            allow_patterns=(*MODEL_FILES, "vocabulary.*", "preprocessor_config.json", "README.md"),
        )
    )
    if not model_ready(path):
        raise ValueError("La descarga no contiene los archivos necesarios del modelo")
    return path
