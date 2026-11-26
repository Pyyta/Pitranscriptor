import os
from dataclasses import replace
from types import SimpleNamespace

import pytest

from pitranscriptor.models import MODEL_FILES, SMALL_MODEL, TURBO_MODEL
from pitranscriptor.project import Project
from pitranscriptor.subtitles import Cue, Style, Word
from pitranscriptor.vocabulary import MAX_TECHNICAL_HINTS

desktop = pytest.importorskip("pitranscriptor.desktop")
qt_core = pytest.importorskip("PySide6.QtCore")
qt_test = pytest.importorskip("PySide6.QtTest")


@pytest.fixture(scope="module")
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = desktop.QApplication.instance() or desktop.QApplication([])
    desktop.configure_application(app)
    return app


def test_drag_selects_multiple_fragments_and_uses_one_undo_step(qt_app):
    editor = desktop.Editor("es")
    cues = (Cue(1000, 2000, "Uno"), Cue(3000, 4000, "Dos"), Cue(7000, 8000, "Tres"))
    original = Project("test.mp4", 10_000, cues)
    editor.project = editor.saved_project = original
    editor.refresh()
    editor.show()
    qt_app.processEvents()
    track = editor.timeline
    mouse = desktop.Qt.MouseButton.LeftButton

    def point(ms, y=62):
        start, duration = track.viewport()
        return desktop.QPointF(round((ms - start) * track.width() / duration), y).toPoint()

    # De derecha a izquierda, empezando en un hueco, sin tocar el tercer bloque.
    qt_test.QTest.mousePress(track, mouse, pos=point(4800))
    qt_test.QTest.mouseMove(track, point(1600))
    assert track.drag_end is not None
    qt_test.QTest.mouseRelease(track, mouse, pos=point(1600))
    assert editor.selected_rows() == (0, 1)
    assert track.selection == {0, 1}
    assert editor.project == original
    assert editor.delete_button.isEnabled()
    assert editor.inspector.isEnabled()

    editor.delete_button.click()
    assert editor.project.cues == (cues[2],)
    editor.undo()
    assert editor.project == original

    # A otro zoom, un clic selecciona un solo bloque y el área de onda limpia la selección.
    editor.set_zoom(2)
    qt_test.QTest.mouseClick(track, mouse, pos=point(3500))
    assert editor.current_cue() == cues[1]
    assert editor.inspector.isEnabled()
    qt_test.QTest.mouseClick(track, mouse, pos=point(2500, 20))
    assert editor.selected_rows() == ()
    assert track.selection == set()
    editor.close()
    editor.deleteLater()
    qt_app.sendPostedEvents(None, qt_core.QEvent.Type.DeferredDelete)


@pytest.fixture
def caption_editor(qt_app, monkeypatch, tmp_path):
    editor = desktop.Editor("es")
    editor.settings = desktop.QSettings(
        str(tmp_path / "test.ini"), desktop.QSettings.Format.IniFormat
    )
    errors = []
    monkeypatch.setattr(editor, "show_error", errors.append)
    cues = tuple(
        Cue(
            start,
            start + 1000,
            "Dos palabras",
            (Word("Dos", start + 100, start + 250), Word("palabras", start + 400, start + 700)),
            Style(size=size, color=color, bold=bold, font=f"Prueba {size}"),
        )
        for start, size, color, bold in (
            (1000, 40, "#dc0000", True),
            (3000, 55, "#00dc00", False),
            (6500, 63, "#0000dc", False),
        )
    )
    editor.project = editor.saved_project = Project("test.mp4", 10_000, cues)
    editor.refresh()
    yield editor, errors
    editor.saved_project = editor.project
    editor.close()
    editor.deleteLater()
    qt_app.sendPostedEvents(None, qt_core.QEvent.Type.DeferredDelete)


def test_batch_properties_preserve_unmarked_fields_and_word_positions(caption_editor):
    editor, errors = caption_editor
    original = editor.project
    editor.set_caption_selection((0, 2), False)
    editor.apply_button.click()
    assert not editor.before
    assert editor.preview.editable
    editor.font.setCurrentFont(desktop.QFont("Courier New"))
    editor.property_checks["font"].setChecked(True)
    font = editor.font.currentFont().family()
    editor.size.setValue(84)
    editor.x.setValue(0.31)
    editor.align.setCurrentIndex(editor.align.findData("left"))
    editor.effect.setCurrentIndex(editor.effect.findData("appear"))
    editor.property_checks["bold"].setChecked(True)
    editor.apply_button.click()
    expected = tuple(
        replace(
            cue,
            style=replace(
                cue.style, font=font, size=84, x=0.31, align="left", effect="appear", bold=True
            ),
        )
        if index in (0, 2)
        else cue
        for index, cue in enumerate(original.cues)
    )
    assert editor.project.cues == expected
    assert editor.selected_rows() == (0, 2)
    assert len(editor.before) == 1
    editor.undo()
    assert editor.project == original
    editor.redo()
    assert editor.project.cues == expected

    editor.preview.moved.emit(0.42, 0.76)
    assert [
        (editor.project.cues[index].style.x, editor.project.cues[index].style.y) for index in (0, 2)
    ] == [(0.42, 0.76)] * 2
    editor.start.setValue(0.2)
    editor.end.setValue(0.2)
    editor.speaker.setText("Voz A")
    editor.text.setText("Dos nuevas")
    editor.apply_button.click()
    for index in (0, 2):
        before, after = original.cues[index], editor.project.cues[index]
        assert (after.start_ms, after.end_ms) == (before.start_ms + 200, before.end_ms + 200)
        assert (after.text, after.speaker) == ("Dos nuevas", "Voz A")
        assert [word.start_ms for word in after.words] == [
            word.start_ms + 200 for word in before.words
        ]
    assert editor.project.cues[1] == original.cues[1]

    before = editor.project
    editor.start.setValue(-2)
    editor.end.setValue(-1.5)
    editor.apply_button.click()
    assert len(errors) == 1 and editor.project == before


def test_batch_word_edits_presets_and_structural_operations(caption_editor, monkeypatch):
    editor, errors = caption_editor
    original = editor.project
    editor.set_caption_selection((0, 1), False)
    monkeypatch.setattr(desktop.QInputDialog, "getItem", lambda *args: (args[3][0], True))
    monkeypatch.setattr(desktop.QInputDialog, "getText", lambda *args, **kwargs: ("10, 10", True))
    editor.word_button.click()
    assert [cue.words[0].start_ms for cue in editor.project.cues] == [1110, 3110, 6600]
    editor.settings.setValue("presets", '{"Simple": {"size": 78}}')
    editor.apply_preset()
    assert [cue.style.size for cue in editor.project.cues] == [78, 78, 63]
    editor.undo()
    editor.undo()
    assert editor.project == original

    editor.duplicate_button.click()
    assert editor.selected_rows() == (1, 3)
    assert [cue.start_ms for cue in editor.project.cues] == [1000, 2000, 3000, 4000, 6500]
    editor.undo()
    editor.set_caption_selection((0, 1), False)
    monkeypatch.setattr(desktop.QInputDialog, "getInt", lambda *args: (1, True))
    editor.split_button.click()
    assert editor.selected_rows() == (0, 1, 2, 3)
    assert [cue.text for cue in editor.project.cues] == [
        "Dos",
        "palabras",
        "Dos",
        "palabras",
        "Dos palabras",
    ]
    split = editor.project
    editor.duplicate_button.click()
    assert len(errors) == 1 and editor.project == split
    editor.join_button.click()
    assert editor.selected_rows() == (0,)
    assert editor.project.cues[0].text == "Dos palabras Dos palabras"
    editor.undo()
    assert editor.project == split
    editor.set_caption_selection((0, 2), False)
    editor.join_button.click()
    assert len(errors) == 2 and editor.project == split


def test_custom_hint_uses_same_list_and_limit_as_catalog(qt_app):
    picker = desktop.VocabularyPicker(None, lambda es, en: es, ("Zypper",))
    picker.search.setText("zypper")
    assert picker.available.count() == 0
    picker.custom.setText("zypper")
    picker.custom_button.click()
    assert picker.selected_terms() == ("Zypper",)
    picker.custom.setText("  solito  ")
    picker.custom_button.click()
    assert picker.selected_terms() == ("Zypper", "solito")
    assert not picker.custom.text()
    assert picker.add_terms([f"pista {index}" for index in range(MAX_TECHNICAL_HINTS - 2)])
    picker.custom.setText("Una más")
    picker.custom.returnPressed.emit()
    assert len(picker.selected_terms()) == MAX_TECHNICAL_HINTS
    picker.deleteLater()
    qt_app.sendPostedEvents(None, qt_core.QEvent.Type.DeferredDelete)


def test_local_model_selection_reuses_a_model_next_to_the_current_one(tmp_path):
    local_turbo = tmp_path / TURBO_MODEL.directory
    local_turbo.mkdir()
    for name in MODEL_FILES:
        (local_turbo / name).touch()
    selected = []
    editor = SimpleNamespace(
        job=None,
        model_path=tmp_path / SMALL_MODEL.directory,
        model_storage=tmp_path / "downloads",
        use_model=selected.append,
    )
    desktop.Editor.install_model(editor, TURBO_MODEL)
    assert selected == [local_turbo]
