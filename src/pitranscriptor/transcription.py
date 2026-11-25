"""Reconocimiento con un modelo ya instalado y marcas por palabra."""

from collections.abc import Callable
from pathlib import Path

from pitranscriptor.models import model_ready
from pitranscriptor.project import Project
from pitranscriptor.subtitles import MAX_MEDIA_MS, Word, fragment_words


def inspect_media(source: Path, *, require_video: bool = False) -> tuple[int, int]:
    """Devuelve duración en ms y desfase inicial del audio respecto al video."""
    import av

    source = source.resolve(strict=True)
    if not source.is_file():
        raise ValueError("Selecciona un archivo local")
    try:
        with source.open("rb") as media, av.open(media) as container:
            if require_video and not container.streams.video:
                raise ValueError("El archivo no contiene una pista de video")
            if not container.streams.audio and not require_video:
                raise ValueError("El archivo no contiene una pista de audio")
            if container.duration is None:
                raise ValueError("No se pudo determinar la duración del archivo")
            duration = (container.duration + 999) // 1000
            if not 0 < duration <= MAX_MEDIA_MS:
                raise ValueError("El medio debe durar entre 0 y 300 segundos")
            if not container.streams.video or not container.streams.audio:
                return duration, 0
            audio = container.streams.audio[0]
            video = container.streams.video[0]
            offset = 0
            if all(stream.start_time is not None and stream.time_base for stream in (audio, video)):
                offset = round(
                    (audio.start_time * audio.time_base - video.start_time * video.time_base) * 1000
                )
            return duration, offset
    except av.FFmpegError as error:
        raise ValueError("No se pudo abrir el medio con los códecs disponibles") from error


def transcribe_project(
    source: Path,
    model_dir: Path,
    *,
    language: str | None = "es",
    vocabulary: str | None = None,
    target: int = 4,
    device: str = "cpu",
    progress: Callable[[int], None] = lambda percent: None,
    cancelled: Callable[[], bool] = lambda: False,
) -> Project:
    try:
        import av
        from faster_whisper import WhisperModel
        from faster_whisper.audio import decode_audio
        from faster_whisper.vad import VadOptions, get_speech_timestamps
    except ImportError as error:
        raise ValueError("Instala el extra research para transcribir") from error

    source = source.resolve(strict=True)
    duration, offset = inspect_media(source)
    if not model_ready(model_dir):
        raise ValueError("Selecciona una carpeta con un modelo CTranslate2 completo")
    if device not in ("cpu", "cuda"):
        raise ValueError("Dispositivo de reconocimiento inválido")
    if cancelled():
        raise InterruptedError("Transcripción cancelada")
    progress(0)
    model = WhisperModel(
        str(model_dir.resolve()),
        device=device,
        compute_type="int8" if device == "cpu" else "int8_float16",
        local_files_only=True,
    )
    if cancelled():
        raise InterruptedError("Transcripción cancelada")
    words = []
    last_end = 0
    try:
        with source.open("rb") as audio:
            input_audio = audio
            clips = "0"
            mixed = language == "mixed"
            if mixed:
                if not model.model.is_multilingual:
                    raise ValueError("El modo mixto requiere un modelo multilingüe")
                rate = model.feature_extractor.sampling_rate
                input_audio = decode_audio(audio, sampling_rate=rate)
                speech = get_speech_timestamps(
                    input_audio, VadOptions(min_silence_duration_ms=180, speech_pad_ms=80), rate
                )
                if cancelled():
                    raise InterruptedError("Transcripción cancelada")
                if not speech:
                    progress(100)
                    return Project(str(source), duration)
                clips = [
                    tick / rate
                    for interval in speech
                    for tick in (interval["start"], interval["end"])
                ]
            segments, _ = model.transcribe(
                input_audio,
                language=None if mixed else language,
                task="transcribe",
                word_timestamps=True,
                multilingual=mixed,
                vad_filter=not mixed,
                clip_timestamps=clips,
                beam_size=5,
                temperature=0,
                condition_on_previous_text=False,
                initial_prompt=vocabulary,
            )
            for segment in segments:
                if cancelled():
                    raise InterruptedError("Transcripción cancelada")
                for word in segment.words or ():
                    tokens = word.word.split()
                    if not tokens:
                        continue
                    start = min(
                        max(last_end, round(word.start * 1000) + offset), duration - len(tokens)
                    )
                    if start < last_end:
                        raise ValueError("No hay tiempo suficiente para las palabras finales")
                    end = min(duration, max(start + len(tokens), round(word.end * 1000) + offset))
                    for index, token in enumerate(tokens):
                        first = start + (end - start) * index // len(tokens)
                        last = start + (end - start) * (index + 1) // len(tokens)
                        words.append(Word(token, first, last, word.probability))
                    last_end = end
                progress(min(99, last_end * 100 // duration))
    except av.FFmpegError as error:
        raise ValueError("No se pudo decodificar el audio") from error
    if cancelled():
        raise InterruptedError("Transcripción cancelada")
    project = Project(str(source), duration, fragment_words(words, target=target))
    progress(100)
    return project
