"""Construye dos veces y exige los mismos hashes; no publica artefactos."""

import hashlib
import os
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path


def check_archive(path: Path) -> None:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    else:
        with tarfile.open(path) as archive:
            names = archive.getnames()
    forbidden = {".cache", ".tools", ".venv", "models", "local"}
    media = {".wav", ".mp3", ".mp4", ".mov", ".mkv", ".webm", ".flac", ".m4a", ".ogg"}
    if any(
        forbidden.intersection(Path(name).parts) or Path(name).suffix.lower() in media
        for name in names
    ):
        raise SystemExit("El paquete contiene medios o directorios reservados a datos locales")
    if not all(
        any(name.endswith(f"/{notice}") for name in names) for notice in ("LICENSE", "NOTICE")
    ):
        raise SystemExit("Faltan LICENSE o NOTICE en el paquete")


def main() -> None:
    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit("uv no está en PATH. Ejecuta: uv run python scripts/verify_build.py")
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, SOURCE_DATE_EPOCH="1704067200")
    (root / ".cache").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="build-", dir=root / ".cache") as directory:
        results = []
        for name in ("first", "second"):
            output = Path(directory) / name
            subprocess.run(
                [uv, "build", "--no-build-isolation", "--out-dir", str(output)],
                cwd=root,
                env=env,
                check=True,
            )
            hashes = {
                file.name: hashlib.sha256(file.read_bytes()).hexdigest()
                for file in sorted(output.iterdir())
                if file.name.endswith((".whl", ".tar.gz"))
            }
            if len(hashes) != 2:
                raise SystemExit("Se esperaba un wheel y un sdist")
            for name in hashes:
                check_archive(output / name)
            results.append(hashes)
        if results[0] != results[1]:
            raise SystemExit("Las dos compilaciones no son idénticas")
        for name, digest in results[0].items():
            print(f"SHA256 {name}: {digest}")
    print("Dos compilaciones idénticas. No equivale a un instalador de escritorio.")


if __name__ == "__main__":
    main()
