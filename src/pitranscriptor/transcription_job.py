"""Aislar la inferencia nativa para que un fallo no bloquee el siguiente intento."""

import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic

from pitranscriptor.project import load_project, save_project
from pitranscriptor.transcription import transcribe_project

WORKER_FLAG = "--transcription-worker"
STALL_SECONDS = 180


def worker(folder: Path) -> int:
    def report(value):
        with (folder / "progress").open("a", encoding="utf-8") as progress:
            print(value, file=progress)

    try:
        request = json.loads((folder / "request.json").read_text(encoding="utf-8"))
        source = Path(request.pop("source"))
        model = Path(request.pop("model"))
        project = transcribe_project(source, model, progress=report, **request)
        save_project(folder / "project.pitranscriptor", project)
    except Exception as error:
        (folder / "error").write_text(str(error), encoding="utf-8")
        return 1
    return 0


def run_transcription(source, model, *, progress, cancelled, **options):
    if cancelled():
        raise InterruptedError("Transcripción cancelada")
    command = [sys.executable]
    if not getattr(sys, "frozen", False):
        command.extend(["-m", "pitranscriptor.transcription_job"])
    command.append(WORKER_FLAG)
    env = dict(os.environ, HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    # Windows puede retener un archivo recién cerrado durante un análisis en segundo plano.
    with TemporaryDirectory(
        prefix="pitranscriptor-transcription-", ignore_cleanup_errors=True
    ) as directory:
        folder = Path(directory)
        (folder / "request.json").write_text(
            json.dumps(dict(source=str(source.resolve()), model=str(model.resolve()), **options)),
            encoding="utf-8",
        )
        progress(-1)
        with subprocess.Popen(
            [*command, directory],
            env=env,
            stdin=subprocess.DEVNULL,
            creationflags=flags,
        ) as process:
            last_activity = monotonic()
            previous = ""
            try:
                while True:
                    if cancelled():
                        raise InterruptedError("Transcripción cancelada")
                    try:
                        updates = (folder / "progress").read_text(encoding="utf-8")
                    except (FileNotFoundError, PermissionError):
                        updates = ""
                    if updates != previous and updates.endswith("\n"):
                        previous = updates
                        last_activity = monotonic()
                        value = int(updates.splitlines()[-1])
                        if 0 < value < 100:
                            progress(value)
                    if monotonic() - last_activity >= STALL_SECONDS:
                        raise TimeoutError(
                            "La transcripción no avanzó durante tres minutos. "
                            "Puedes reintentar o seleccionar CPU si estabas usando CUDA."
                        )
                    try:
                        status = process.wait(timeout=0.15)
                        break
                    except subprocess.TimeoutExpired:
                        pass
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
        if cancelled():
            raise InterruptedError("Transcripción cancelada")
        error = folder / "error"
        if status:
            if error.exists():
                raise RuntimeError(error.read_text(encoding="utf-8"))
            raise RuntimeError(
                f"El proceso de transcripción terminó inesperadamente ({status}). "
                "Puedes reintentar."
            )
        project = load_project(folder / "project.pitranscriptor")
        progress(100)
        return project


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == WORKER_FLAG:
    raise SystemExit(worker(Path(sys.argv[2])))
