"""Preparación de copias locales para el corpus, sin modificar el original."""

import hashlib
import wave
from dataclasses import dataclass
from pathlib import Path

from pitranscriptor.corpus import MAX_DURATION_SECONDS

SAMPLE_RATE = 16000


@dataclass(frozen=True)
class PreparedAudio:
    duration_seconds: float
    source_sha256: str
    output_sha256: str


def file_sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def prepare_audio(source: Path, destination: Path) -> PreparedAudio:
    """Crear un WAV PCM16 mono a 16 kHz, sin sobrescribir ni recortar audio."""
    try:
        import av
    except ImportError as error:
        raise ValueError("Instala el extra research: uv sync --locked --extra research") from error

    source = source.resolve(strict=True)
    destination = destination.absolute()
    if not source.is_file():
        raise ValueError("El origen debe ser un archivo local")
    if source == destination.resolve():
        raise ValueError("La copia debe tener una ruta diferente del original")
    if destination.suffix.lower() != ".wav":
        raise ValueError("La copia de salida debe tener extensión .wav")
    if destination.exists():
        raise FileExistsError("La salida ya existe; elige otro nombre para conservarla")
    source_hash = file_sha256(source)
    created = False
    complete = False
    samples = 0
    try:
        with av.open(str(source)) as container:
            if len(container.streams.audio) != 1:
                raise ValueError("Se requiere exactamente una pista de audio")
            stream = container.streams.audio[0]
            if (
                stream.duration is not None
                and stream.time_base is not None
                and stream.duration * stream.time_base > MAX_DURATION_SECONDS
            ):
                raise ValueError("El audio supera los cinco minutos; no se recorta automáticamente")
            resampler = av.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as output:
                created = True
                with wave.open(output, "wb") as writer:
                    writer.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))

                    def write(frames):
                        nonlocal samples
                        for frame in frames:
                            samples += frame.samples
                            if samples > SAMPLE_RATE * MAX_DURATION_SECONDS:
                                raise ValueError("El audio supera los cinco minutos")
                            writer.writeframesraw(
                                frame.to_ndarray().astype("<i2", copy=False).tobytes()
                            )

                    for frame in container.decode(stream):
                        # Los WAV de evaluación utilizan tiempos continuos desde cero.
                        frame.pts = None
                        write(resampler.resample(frame))
                    write(resampler.resample(None))
                    if samples == 0:
                        raise ValueError("El archivo no contiene muestras de audio")
            if file_sha256(source) != source_hash:
                raise ValueError(
                    "El origen cambió durante la preparación; repite con un archivo estable"
                )
            complete = True
    except av.FFmpegError as error:
        raise ValueError("No se pudo decodificar el audio con los códecs disponibles") from error
    finally:
        if created and not complete:
            destination.unlink(missing_ok=True)
    return PreparedAudio(samples / SAMPLE_RATE, source_hash, file_sha256(destination))
