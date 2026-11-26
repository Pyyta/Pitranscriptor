import os
from types import SimpleNamespace

import pytest

from pitranscriptor.models import MODEL_FILES, SMALL_MODEL, TURBO_MODEL
from pitranscriptor.project import Project
from pitranscriptor.subtitles import Cue
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
    assert not editor.inspector.isEnabled()

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
