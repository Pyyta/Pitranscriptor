"""Construir la aplicación local y su instalador para el sistema anfitrión."""

import os
import platform
import shutil
import subprocess
import sys
from importlib.metadata import distributions
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]


def collect_notices(directory: Path) -> None:
    """Conservar textos de licencia y versiones del entorno usado para construir."""
    directory.mkdir(parents=True)
    inventory = []
    for distribution in sorted(distributions(), key=lambda item: item.metadata["Name"].lower()):
        name = distribution.metadata["Name"]
        inventory.append(f"{name}=={distribution.version}")
        for entry in distribution.files or ():
            if not any(part.endswith(".dist-info") for part in entry.parts):
                continue
            if not any(
                key in entry.name.lower() for key in ("license", "copying", "notice", "copyright")
            ):
                continue
            source = Path(distribution.locate_file(entry))
            if source.is_file():
                # Los componentes pueden tener varios archivos LICENSE en subdirectorios.
                target = directory / name / entry
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    (directory / "environment.txt").write_text("\n".join(inventory) + "\n", encoding="utf-8")
    shutil.copy2(ROOT / "LICENSE", directory)
    shutil.copy2(ROOT / "NOTICE", directory)
    shutil.copy2(ROOT / "docs" / "licencias.md", directory)


def bundle(entry: str, name: str, *options: str) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--name",
            name,
            "--specpath",
            str(ROOT / "build" / "pyinstaller"),
            "--workpath",
            str(ROOT / "build" / "pyinstaller-work"),
            "--distpath",
            str(ROOT / "dist" / "desktop"),
            *options,
            str(ROOT / "packaging" / entry),
        ],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    if sys.platform not in {"win32", "linux"} or platform.machine().lower() not in {
        "amd64",
        "x86_64",
    }:
        raise SystemExit("La distribución se construye en Windows o Linux x86-64")
    destination = ROOT / "dist" / "desktop"
    bundle(
        "launch.py",
        "Pitranscriptor",
        "--onedir",
        "--windowed",
        "--noupx",
        "--collect-data",
        "faster_whisper",
        "--collect-data",
        "certifi",
        "--copy-metadata",
        "httpx2",
        "--copy-metadata",
        "httpcore2",
        "--hidden-import",
        "PySide6.QtMultimedia",
        "--add-data",
        f"{ROOT / 'LICENSE'}:.",
        "--add-data",
        f"{ROOT / 'NOTICE'}:.",
    )
    with TemporaryDirectory(dir=destination) as directory:
        staging = Path(directory)
        collect_notices(destination / "Pitranscriptor" / "licenses")
        if os.name == "nt":
            archive = shutil.make_archive(
                str(staging / "Pitranscriptor"), "zip", destination / "Pitranscriptor"
            )
            bundle(
                "install_windows.py",
                "Pitranscriptor-Setup",
                "--onefile",
                "--windowed",
                "--noupx",
                "--add-data",
                f"{archive}:.",
            )
        else:
            shutil.copytree(destination / "Pitranscriptor", staging / "Pitranscriptor")
            shutil.copy2(ROOT / "packaging" / "install-linux.sh", staging)
            shutil.make_archive(str(destination / "Pitranscriptor-linux-x86_64"), "gztar", staging)


if __name__ == "__main__":
    main()
