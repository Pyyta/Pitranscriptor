"""Reducir la pista de audio a un conjunto fijo de picos para la línea de tiempo."""

from pathlib import Path


def audio_peaks(source: Path, duration_ms: int, count: int = 600) -> tuple[float, ...]:
    import av
    import numpy as np

    peaks = np.zeros(count, dtype=np.float32)
    resampler = av.AudioResampler(format="fltp", layout="mono", rate=8000)
    samples_per_bin = max(1, (duration_ms * 8 + count - 1) // count)
    with source.open("rb") as media, av.open(media) as container:
        if not container.streams.audio:
            return tuple(peaks.tolist())
        stream = container.streams.audio[0]
        origin = container.streams.video[0] if container.streams.video else stream
        origin_seconds = float((origin.start_time or 0) * origin.time_base)
        position = 0
        for frame in container.decode(stream):
            for converted in resampler.resample(frame):
                if converted.pts is not None and converted.time_base is not None:
                    position = round(
                        (float(converted.pts * converted.time_base) - origin_seconds) * 8000
                    )
                values = np.abs(converted.to_ndarray().ravel())
                indexes = (np.arange(len(values)) + position) // samples_per_bin
                inside = (indexes >= 0) & (indexes < count)
                np.maximum.at(peaks, indexes[inside], values[inside])
                position += len(values)
    return tuple(float(min(1.0, peak)) for peak in peaks)
