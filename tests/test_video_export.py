import os
from dataclasses import replace
from fractions import Fraction

import pytest

from pitranscriptor.project import Project
from pitranscriptor.subtitles import Cue, Style

av = pytest.importorskip("av")
np = pytest.importorskip("numpy")
qt = pytest.importorskip("PySide6.QtWidgets")
desktop = pytest.importorskip("pitranscriptor.desktop")


@pytest.fixture(scope="module")
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = qt.QApplication.instance() or qt.QApplication([])
    desktop.configure_application(app)
    return app


def make_clip(path, width, height, *, audio_codec, rotation=0):
    with av.open(str(path), "w") as out:
        art = out.add_stream("libx264", rate=24)
        art.width = width
        art.height = height
        art.pix_fmt = "yuv420p"
        art.set_display_rotation(rotation)
        audio = out.add_stream(audio_codec, rate=48000)
        audio.layout = "mono"
        pixels = np.full((height, width, 3), 32, dtype=np.uint8)
        for index in range(24):
            for packet in art.encode(av.VideoFrame.from_ndarray(pixels, format="rgb24")):
                out.mux(packet)
            frame = av.AudioFrame.from_ndarray(
                np.zeros((1, 2000), dtype=np.int16), format="s16", layout="mono"
            )
            frame.sample_rate = 48000
            frame.pts = index * 2000
            frame.time_base = Fraction(1, 48000)
            for packet in audio.encode(frame):
                out.mux(packet)
        for stream in (art, audio):
            for packet in stream.encode():
                out.mux(packet)


@pytest.mark.parametrize(
    "size, rotation, output, audio_codec, fps, height, expected",
    [
        ((160, 96), 90, "mp4", "aac", Fraction(30), 120, (72, 120, 30, "copy")),
        ((160, 96), 0, "mov", "pcm_s16le", None, None, (160, 96, 24, "aac")),
    ],
)
def test_export_preserves_audio_timing_and_burns_captions(
    tmp_path, qt_app, size, rotation, output, audio_codec, fps, height, expected
):
    from pitranscriptor.video_export import export_video

    source = tmp_path / "source.mov"
    make_clip(source, *size, audio_codec=audio_codec, rotation=rotation)
    original = source.read_bytes()
    out = tmp_path / f"export.{output}"
    cue = Cue(30, 450, "Texto", style=Style(size=75, background="#b00000"))
    project = Project(str(source), 1000, (cue,))
    result = export_video(project, out, fps=fps, height_limit=height)
    assert source.read_bytes() == original
    assert (result.width, result.height, result.audio_mode) == (*expected[:2], expected[3])
    with av.open(str(out)) as clip:
        video = clip.streams.video[0]
        assert (video.width, video.height, video.average_rate) == expected[:3]
        frames = list(clip.decode(video))
        assert len(frames) == expected[2]
        on = frames[expected[2] // 4].to_ndarray(format="rgb24")
        off = frames[-1].to_ndarray(format="rgb24")
        assert int(on[:, :, 0].max()) > int(off[:, :, 0].max()) + 20
    with av.open(str(out)) as clip:
        assert clip.streams.audio[0].codec_context.name == "aac"
        assert 48000 <= sum(frame.samples for frame in clip.decode(audio=0)) <= 49024
    with pytest.raises(FileExistsError):
        export_video(replace(project, cues=()), out)


def test_cancelled_export_leaves_no_output(tmp_path, qt_app):
    from pitranscriptor.video_export import export_video

    source = tmp_path / "source.mov"
    make_clip(source, 160, 96, audio_codec="aac")
    target = tmp_path / "export.mp4"
    with pytest.raises(InterruptedError):
        export_video(Project(str(source), 1000), target, cancelled=lambda: True)
    assert list(tmp_path.iterdir()) == [source]
