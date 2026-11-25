"""Instalación explícita de modelos de referencia."""

from pathlib import Path

SMALL_REPO = "Systran/faster-whisper-small"
SMALL_REVISION = "536b0662742c02347bc0e980a01041f333bce120"
MODEL_FILES = ("model.bin", "config.json", "tokenizer.json")


def model_ready(path: Path) -> bool:
    return all((path / name).is_file() for name in MODEL_FILES)


def download_small(destination: Path) -> Path:
    from huggingface_hub import snapshot_download

    path = Path(
        snapshot_download(
            SMALL_REPO,
            revision=SMALL_REVISION,
            local_dir=destination,
            token=False,
            allow_patterns=(*MODEL_FILES, "vocabulary.*", "preprocessor_config.json", "README.md"),
        )
    )
    if not model_ready(path):
        raise ValueError("La descarga no contiene los archivos necesarios del modelo")
    return path
