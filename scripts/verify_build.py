"""Construye dos veces y exige los mismos hashes; no publica artefactos."""

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


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
            results.append(hashes)
        if results[0] != results[1]:
            raise SystemExit("Las dos compilaciones no son idénticas")
        for name, digest in results[0].items():
            print(f"SHA256 {name}: {digest}")
    print("Dos compilaciones idénticas. No equivale a un instalador de escritorio.")


if __name__ == "__main__":
    main()
