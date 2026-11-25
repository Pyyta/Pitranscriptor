from dataclasses import replace

import pytest

from pitranscriptor.project import Project, edit_cue, load_project, save_project, write_text
from pitranscriptor.subtitles import Cue, Style, Word, fragment_words, render_subtitles


def test_fragmentation_preserves_words_and_honors_pauses_and_seven_word_limit():
    text = "uno dos tres cuatro cinco seis siete. ocho nueve diez once doce trece catorce quince"
    words = tuple(
        Word(token, index * 200 + gap, index * 200 + gap + 150)
        for index, token in enumerate(text.split())
        for gap in [600 if index >= 9 else 0]
    )
    cues = fragment_words(words)
    assert [len(cue.words) for cue in cues] == [7, 2, 6]
    assert tuple(word for cue in cues for word in cue.words) == words
    with pytest.raises(ValueError, match="siete"):
        Cue(0, 1000, "uno dos tres cuatro cinco seis siete ocho")


def test_word_timing_for_text_changes():
    cue = Cue(20, 400, "Hola mundo", (Word("Hola", 20, 180, 0.7), Word("mundo", 200, 400, 0.2)))
    edited = edit_cue(cue, "Hola Linux", 20, 400)
    assert edited.words[1] == Word("Linux", 200, 400)
    assert edited.words[0].probability == 0.7
    assert not edit_cue(cue, "Hola nuevo mundo", 20, 400).words
    assert not edit_cue(cue, "Hola mundo", 50, 300).words


def test_project_round_trip_keeps_fragment_style_and_protects_media(tmp_path):
    source = tmp_path / "audio.wav"
    source.write_bytes(b"original")
    cue = Cue(20, 400, "Hola", (Word("Hola", 20, 400),))
    other = Cue(500, 700, "Mundo", style=Style(x=0.8, size=82, effect="fade"))
    project = Project(str(source), 700, (cue, other))
    destination = tmp_path / "demo.pitranscriptor"
    save_project(destination, project)
    assert load_project(destination) == project
    with pytest.raises(FileExistsError):
        save_project(destination, project)
    with pytest.raises(ValueError):
        save_project(source, project, overwrite=True)
    assert source.read_bytes() == b"original"
    edited = project.with_cues((replace(cue, style=Style(x=0.3)), other))
    save_project(destination, edited, overwrite=True)
    assert load_project(destination).cues[1] == other


def test_subtitle_timestamps_escaping_and_no_overwrite(tmp_path):
    cues = (Cue(1030, 4000, "A < B & C"),)
    srt = render_subtitles(cues, webvtt=False)
    vtt = render_subtitles(cues, webvtt=True)
    assert srt == "1\n00:00:01,030 --> 00:00:04,000\nA &lt; B &amp; C\n"
    assert vtt == "WEBVTT\n\n1\n00:00:01.030 --> 00:00:04.000\nA &lt; B &amp; C\n"
    path = tmp_path / "demo.srt"
    write_text(path, srt)
    with pytest.raises(FileExistsError):
        write_text(path, vtt)
    assert path.read_text() == srt
