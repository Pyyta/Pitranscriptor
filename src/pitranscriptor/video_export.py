"""Exportar subtítulos seleccionables o renderizados sobre el video."""

import os
from bisect import bisect_right
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from tempfile import NamedTemporaryFile
from xml.sax.saxutils import escape

from pitranscriptor.project import Project

QUALITY = {"original": 16, "high": 19, "medium": 23, "low": 28}
VIDEO_TIME_BASE = Fraction(1, 90_000)
SUBTITLE_TIME_BASE = Fraction(1, 1_000)
SUBTITLE_CODECS = {".mkv": "subrip", ".mp4": "mov_text", ".mov": "mov_text"}


@dataclass(frozen=True)
class ExportResult:
    width: int
    height: int
    audio_mode: str
    subtitle_codec: str | None = None


def export_subtitle_track(
    project: Project,
    destination: Path,
    *,
    overwrite: bool = False,
    progress: Callable[[int], None] = lambda percent: None,
    cancelled: Callable[[], bool] = lambda: False,
) -> ExportResult:
    """Multiplexar subtítulos de texto y copiar los paquetes de video y audio."""
    import av

    source = Path(project.source).resolve(strict=True)
    destination = destination.resolve()
    suffix = destination.suffix.lower()
    if destination == source or suffix not in SUBTITLE_CODECS:
        raise ValueError("Selecciona un archivo MKV, MP4 o MOV diferente del original")
    if destination.exists() and not overwrite:
        raise FileExistsError(destination)
    if cancelled():
        raise InterruptedError("Exportación cancelada")
    if not project.cues:
        raise ValueError("Añade al menos un fragmento para exportar una pista de subtítulos")

    codec = SUBTITLE_CODECS[suffix]
    options = {"default_mode": "passthrough"} if suffix == ".mkv" else None
    with NamedTemporaryFile(dir=destination.parent, suffix=suffix, delete=False) as temporary:
        temp_path = Path(temporary.name)
    try:
        with (
            source.open("rb") as media,
            av.open(media) as incoming,
            av.open(str(temp_path), "w", options=options) as output,
        ):
            if not incoming.streams.video:
                raise ValueError("El proyecto requiere un medio con video")
            video = incoming.streams.video[0]
            origin = (video.start_time or 0) * video.time_base
            streams = (*incoming.streams.video, *incoming.streams.audio)
            copies = {stream.index: output.add_stream_from_template(stream) for stream in streams}
            output.metadata.update(incoming.metadata)
            subtitle = output.add_mux_stream(codec, time_base=SUBTITLE_TIME_BASE)
            subtitle.metadata["title"] = "Pitranscriptor"
            subtitle.metadata["handler_name"] = "Pitranscriptor"
            output.start_encoding()

            cues = iter(project.cues)
            cue = next(cues, None)
            base_ms = round(origin / SUBTITLE_TIME_BASE)

            def write_subtitle(cue):
                text = " ".join(cue.text.split())
                payload = (escape(text) if codec == "subrip" else text).encode("utf-8")
                if codec == "mov_text":
                    # Cada muestra tx3g empieza por el tamaño del texto UTF-8 en 16 bits.
                    if len(payload) > 65535:
                        raise ValueError("Un subtítulo supera el tamaño admitido en MP4 y MOV")
                    payload = len(payload).to_bytes(2, "big") + payload
                packet = av.Packet(payload)
                packet.pts = packet.dts = base_ms + cue.start_ms
                packet.duration = cue.end_ms - cue.start_ms
                packet.time_base = SUBTITLE_TIME_BASE
                packet.stream = subtitle
                output.mux(packet)

            last_progress = -1
            for packet in incoming.demux(*streams):
                if cancelled():
                    raise InterruptedError("Exportación cancelada")
                if packet.dts is None:
                    continue
                time = packet.dts * packet.time_base - origin
                while cue is not None and cue.start_ms * SUBTITLE_TIME_BASE <= time:
                    write_subtitle(cue)
                    cue = next(cues, None)
                packet.stream = copies[packet.stream.index]
                output.mux(packet)
                percent = min(99, int(time * 100_000 / project.duration_ms))
                if percent > last_progress:
                    last_progress = percent
                    progress(percent)
            while cue is not None:
                if cancelled():
                    raise InterruptedError("Exportación cancelada")
                write_subtitle(cue)
                cue = next(cues, None)
            result = ExportResult(
                video.width, video.height, "copy" if incoming.streams.audio else "none", codec
            )

        if cancelled():
            raise InterruptedError("Exportación cancelada")
        if overwrite:
            os.replace(temp_path, destination)
        else:
            os.link(temp_path, destination)
        progress(100)
        return result
    except av.FFmpegError as error:
        if suffix in {".mp4", ".mov"}:
            raise ValueError(
                "No se pudieron copiar las pistas originales a este contenedor. Prueba MKV."
            ) from error
        raise ValueError("No se pudo exportar las pistas originales a MKV") from error
    finally:
        temp_path.unlink(missing_ok=True)


def export_video(
    project: Project,
    destination: Path,
    *,
    quality: str = "high",
    height_limit: int | None = None,
    fps: Fraction | None = None,
    overwrite: bool = False,
    progress: Callable[[int], None] = lambda percent: None,
    cancelled: Callable[[], bool] = lambda: False,
) -> ExportResult:
    import av
    import numpy as np
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QImage, QPainter, QTransform

    from pitranscriptor.painting import paint_caption

    source = Path(project.source).resolve(strict=True)
    destination = destination.resolve()
    if destination == source or destination.suffix.lower() not in {".mp4", ".mov"}:
        raise ValueError("Selecciona un archivo MP4 o MOV diferente del original")
    if destination.exists() and not overwrite:
        raise FileExistsError(destination)
    if quality not in QUALITY or fps is not None and not 1 <= fps <= 120:
        raise ValueError("Perfil de calidad o cuadros por segundo inválidos")
    if height_limit is not None and height_limit < 2:
        raise ValueError("La altura debe ser de al menos dos píxeles")

    with NamedTemporaryFile(
        dir=destination.parent, suffix=destination.suffix, delete=False
    ) as temporary:
        temp_path = Path(temporary.name)
    try:
        with (
            source.open("rb") as media,
            av.open(media) as incoming,
            av.open(str(temp_path), "w") as output,
        ):
            if not incoming.streams.video:
                raise ValueError("El proyecto requiere un medio con video")
            video = incoming.streams.video[0]
            audio = incoming.streams.audio[0] if incoming.streams.audio else None
            origin = (video.start_time or 0) * video.time_base
            rate = fps or video.average_rate or video.guessed_rate or Fraction(30)
            video_out = None
            audio_out = None
            audio_mode = "none"
            resampler = None
            width = height = 0
            last_frame = None
            last_video_time = None
            last_video_pts = -1
            next_frame = 0

            if audio is not None:
                if audio.codec_context.name == "aac":
                    audio_out = output.add_stream_from_template(audio)
                    audio_mode = "copy"
                else:
                    audio_out = output.add_stream("aac", rate=48000)
                    audio_out.layout = "mono" if audio.codec_context.channels == 1 else "stereo"
                    audio_out.bit_rate = 160_000
                    resampler = av.AudioResampler(
                        format="fltp", layout=audio_out.layout, rate=48000
                    )
                    audio_mode = "aac"

            def encode_audio(frames):
                for frame in frames:
                    if frame.pts is not None:
                        frame.pts -= round(origin / frame.time_base)
                    for packet in audio_out.encode(frame):
                        output.mux(packet)

            def encode_video(frame, time):
                nonlocal last_video_pts
                pixels = np.ascontiguousarray(frame.to_ndarray(format="rgb24"))
                image = QImage(
                    pixels.data,
                    frame.width,
                    frame.height,
                    frame.width * 3,
                    QImage.Format.Format_RGB888,
                )
                if frame.rotation:
                    image = image.transformed(QTransform().rotate(-frame.rotation))
                image = image.scaled(
                    width,
                    height,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                position = round(time * 1000)
                index = bisect_right(project.cues, position, key=lambda cue: cue.start_ms) - 1
                if index >= 0 and position < project.cues[index].end_ms:
                    painter = QPainter(image)
                    try:
                        paint_caption(
                            painter, QRectF(0, 0, width, height), project.cues[index], position
                        )
                    finally:
                        painter.end()
                view = np.frombuffer(image.bits(), dtype=np.uint8).reshape(
                    height, image.bytesPerLine()
                )
                rgb = np.ascontiguousarray(view[:, : width * 3].reshape(height, width, 3))
                composed = av.VideoFrame.from_ndarray(rgb, format="rgb24")
                composed.time_base = VIDEO_TIME_BASE
                composed.pts = max(last_video_pts + 1, round(time / VIDEO_TIME_BASE))
                last_video_pts = composed.pts
                for packet in video_out.encode(composed):
                    output.mux(packet)
                progress(min(99, position * 100 // project.duration_ms))

            # Las pistas de salida deben existir antes de que el primer mux escriba la cabecera.
            stream_args = (video, audio) if audio is not None else (video,)
            pending_audio = []
            for packet in incoming.demux(*stream_args):
                if cancelled():
                    raise InterruptedError("Exportación cancelada")
                if packet.stream == audio:
                    if video_out is None:
                        pending_audio.append(packet)
                    elif resampler is not None:
                        for frame in packet.decode():
                            encode_audio(resampler.resample(frame))
                    elif packet.dts is not None:
                        shift = round(origin / packet.time_base)
                        packet.dts -= shift
                        if packet.pts is not None:
                            packet.pts -= shift
                        packet.stream = audio_out
                        output.mux(packet)
                    continue
                for frame in packet.decode():
                    if video_out is None:
                        base_width, base_height = frame.width, frame.height
                        if frame.rotation % 180:
                            base_width, base_height = base_height, base_width
                        scale = min(1, height_limit / base_height) if height_limit else 1
                        width = int(base_width * scale) // 2 * 2
                        height = int(base_height * scale) // 2 * 2
                        if min(width, height) < 2:
                            raise ValueError("La resolución resultante es demasiado pequeña")
                        video_out = output.add_stream("libx264", rate=rate)
                        video_out.width = width
                        video_out.height = height
                        video_out.pix_fmt = "yuv420p"
                        video_out.time_base = VIDEO_TIME_BASE
                        video_out.codec_context.time_base = VIDEO_TIME_BASE
                        video_out.options = {
                            "crf": str(QUALITY[quality]),
                            "preset": "fast",
                            "bf": "0",
                        }
                        if video.sample_aspect_ratio and video.sample_aspect_ratio != 1:
                            ratio = video.sample_aspect_ratio
                            video_out.codec_context.sample_aspect_ratio = (
                                1 / ratio if frame.rotation % 180 else ratio
                            )
                        for waiting in pending_audio:
                            if resampler is not None:
                                for audio_frame in waiting.decode():
                                    encode_audio(resampler.resample(audio_frame))
                            elif waiting.dts is not None:
                                shift = round(origin / waiting.time_base)
                                waiting.dts -= shift
                                if waiting.pts is not None:
                                    waiting.pts -= shift
                                waiting.stream = audio_out
                                output.mux(waiting)
                        pending_audio.clear()
                    if frame.pts is None or frame.time_base is None:
                        frame_time = (
                            last_video_time + 1 / rate
                            if last_video_time is not None
                            else Fraction(0)
                        )
                    else:
                        frame_time = max(Fraction(0), frame.pts * frame.time_base - origin)
                    if fps is None:
                        encode_video(frame, frame_time)
                    else:
                        while last_frame is not None and next_frame / rate < frame_time:
                            if cancelled():
                                raise InterruptedError("Exportación cancelada")
                            encode_video(last_frame, next_frame / rate)
                            next_frame += 1
                        last_frame = frame
                    last_video_time = frame_time
            if video_out is None:
                raise ValueError("No se pudo decodificar ningún cuadro de video")
            if fps is not None:
                end = (
                    video.duration * video.time_base
                    if video.duration is not None
                    else last_video_time + 1 / rate
                )
                while next_frame / rate < min(Fraction(project.duration_ms, 1000), end):
                    if cancelled():
                        raise InterruptedError("Exportación cancelada")
                    encode_video(last_frame, next_frame / rate)
                    next_frame += 1
            for packet in video_out.encode():
                output.mux(packet)
            if resampler is not None:
                encode_audio(resampler.resample(None))
                for packet in audio_out.encode():
                    output.mux(packet)
        if cancelled():
            raise InterruptedError("Exportación cancelada")
        if overwrite:
            os.replace(temp_path, destination)
        else:
            os.link(temp_path, destination)
        progress(100)
        return ExportResult(width, height, audio_mode)
    except av.FFmpegError as error:
        raise ValueError("No se pudo exportar con los códecs disponibles") from error
    finally:
        temp_path.unlink(missing_ok=True)
