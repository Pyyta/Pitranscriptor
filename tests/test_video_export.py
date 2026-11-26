import os
from dataclasses import replace
from fractions import Fraction
from xml.sax.saxutils import unescape

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


@pytest.mark.parametrize("ext, codec", [("mkv", "srt"), ("mp4", "mov_text"), ("mov", "mov_text")])
def test_selectable_track_preserves_video_audio_and_cue_times(tmp_path, ext, codec):
    from pitranscriptor.video_export import export_subtitle_track

    source = tmp_path / "source.mp4"
    make_clip(source, 160, 96, audio_codec="aac")
    original = source.read_bytes()
    target = tmp_path / f"with-track.{ext}"
    cues = (
        Cue(30, 140, "¡Qué tal <Linux>!"),
        Cue(140, 300, "A & B"),
        Cue(455, 780, "Siguiente fragmento"),
    )
    project = Project(str(source), 1000, cues)
    progress = []
    result = export_subtitle_track(project, target, progress=progress.append)
    assert (result.width, result.height, result.audio_mode) == (160, 96, "copy")
    assert result.subtitle_codec == ("subrip" if codec == "srt" else "mov_text")
    assert progress[-1] == 100 and progress == sorted(set(progress))
    assert source.read_bytes() == original

    with av.open(str(source)) as before, av.open(str(target)) as after:
        for media in (before, after):
            assert media.streams.video[0].codec_context.name == "h264"
            assert media.streams.audio[0].codec_context.name == "aac"
        original_packets = [bytes(packet) for packet in before.demux(video=0) if packet.size]
        exported_packets = [bytes(packet) for packet in after.demux(video=0) if packet.size]
        assert original_packets == exported_packets
    with av.open(str(source)) as before, av.open(str(target)) as after:
        original_packets = [bytes(packet) for packet in before.demux(audio=0) if packet.size]
        exported_packets = [bytes(packet) for packet in after.demux(audio=0) if packet.size]
        assert original_packets == exported_packets
    with av.open(str(target)) as after:
        (track,) = after.streams.subtitles
        assert track.codec_context.name == codec
        video = after.streams.video[0]
        origin = video.start_time * video.time_base
        packets = [packet for packet in after.demux(track) if packet.size > 2]
        for packet, cue in zip(packets, cues, strict=True):
            text = bytes(packet)
            if codec == "mov_text":
                length = int.from_bytes(text[:2], "big")
                assert length == len(text) - 2
                visible = text[2:].decode()
            else:
                visible = unescape(text.decode())
            assert visible == cue.text
            assert abs((packet.pts * packet.time_base - origin) * 1000 - cue.start_ms) <= 1
            assert packet.duration * packet.time_base * 1000 == cue.end_ms - cue.start_ms


def test_cancelled_selectable_export_preserves_existing_file(tmp_path):
    from pitranscriptor.video_export import export_subtitle_track

    source = tmp_path / "source.mp4"
    make_clip(source, 160, 96, audio_codec="aac")
    target = tmp_path / "export.mkv"
    target.write_bytes(b"existing")
    project = Project(str(source), 1000, (Cue(0, 1000, "Texto"),))
    progress = []
    with pytest.raises(InterruptedError):
        export_subtitle_track(
            project,
            target,
            overwrite=True,
            progress=progress.append,
            cancelled=lambda: bool(progress),
        )
    assert target.read_bytes() == b"existing"
    assert set(tmp_path.iterdir()) == {source, target}
