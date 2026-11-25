"""Editor de subtítulos de escritorio."""

import argparse
import json
import os
import sys
from bisect import bisect_right
from dataclasses import asdict, replace
from fractions import Fraction
from pathlib import Path
from threading import Event

from PySide6.QtCore import QPointF, QRectF, QSettings, QStandardPaths, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QKeySequence, QPainter, QPen
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoSink
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFontComboBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from pitranscriptor.models import download_small, model_ready
from pitranscriptor.painting import paint_caption
from pitranscriptor.project import Project, edit_cue, load_project, save_project, write_text
from pitranscriptor.subtitles import Cue, Style, Word, render_subtitles
from pitranscriptor.transcription import inspect_media, transcribe_project
from pitranscriptor.video_export import export_video
from pitranscriptor.waveform import audio_peaks


def timestamp(ms: int) -> str:
    minutes, rest = divmod(ms, 60_000)
    return f"{minutes:02}:{rest / 1000:06.3f}"


class Job(QThread):
    progress = Signal(int)

    def __init__(self, operation, parent):
        super().__init__(parent)
        self.operation = operation
        self.cancel = Event()
        self.result = None
        self.error = None

    def run(self):
        try:
            self.result = self.operation(self.progress.emit, self.cancel.is_set)
        except Exception as error:
            self.error = error


class Preview(QWidget):
    moved = Signal(float, float)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(350, 250)
        self.frame = QImage()
        self.bounds = QRectF()
        self.cue = None
        self.position = 0
        self.drag = None
        self.editable = False

    def set_frame(self, frame):
        if frame.isValid():
            self.frame = frame.toImage()
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#131921"))
        self.bounds = QRectF(self.rect())
        if not self.frame.isNull():
            size = self.frame.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
            self.bounds = QRectF(
                (self.width() - size.width()) / 2,
                (self.height() - size.height()) / 2,
                size.width(),
                size.height(),
            )
            painter.drawImage(self.bounds, self.frame)
        if self.cue is not None:
            cue = self.cue
            if self.drag is not None:
                cue = replace(cue, style=replace(cue.style, x=self.drag.x(), y=self.drag.y()))
            paint_caption(painter, self.bounds, cue, self.position)

    def _normalized(self, point):
        x = (point.x() - self.bounds.left()) / max(1, self.bounds.width())
        y = (point.y() - self.bounds.top()) / max(1, self.bounds.height())
        return QPointF(max(0, min(1, x)), max(0, min(1, y)))

    def mousePressEvent(self, event):
        if self.editable and self.cue and self.bounds.contains(event.position()):
            self.drag = self._normalized(event.position())
            self.update()

    def mouseMoveEvent(self, event):
        if self.drag is not None:
            self.drag = self._normalized(event.position())
            self.update()

    def mouseReleaseEvent(self, event):
        if self.drag is not None:
            point = self.drag
            self.drag = None
            self.moved.emit(point.x(), point.y())


class Timeline(QWidget):
    seek = Signal(int)
    selected = Signal(int)

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(95)
        self.duration = 1
        self.position = 0
        self.zoom = 1
        self.cues = ()
        self.peaks = ()
        self.selection = -1

    def viewport(self):
        span = self.duration / self.zoom
        return max(0, min(self.duration - span, self.position - span * 0.35)), span

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#26323d"))
        start, span = self.viewport()
        width = self.width()
        for index, peak in enumerate(self.peaks):
            x = round((index * self.duration / len(self.peaks) - start) * width / span)
            if 0 <= x <= width:
                level = round(peak * 18)
                painter.setPen(QColor("#70b4aa"))
                painter.drawLine(x, 28 - level, x, 28 + level)
        for index, cue in enumerate(self.cues):
            left = (cue.start_ms - start) * width / span
            right = (cue.end_ms - start) * width / span
            if right <= 0 or left >= width:
                continue
            box = QRectF(left, 52, max(1, right - left - 1), 23)
            painter.fillRect(box, QColor("#ffd178" if index == self.selection else "#618cad"))
            if box.width() > 44:
                painter.setPen(QColor("#111820"))
                painter.drawText(
                    box.adjusted(4, 0, -3, 0),
                    Qt.AlignmentFlag.AlignVCenter,
                    painter.fontMetrics().elidedText(
                        cue.text, Qt.TextElideMode.ElideRight, int(box.width() - 7)
                    ),
                )
        painter.setPen(QColor("#c8d6df"))
        painter.drawText(5, 90, timestamp(round(start)))
        last = timestamp(round(start + span))
        painter.drawText(width - 5 - painter.fontMetrics().horizontalAdvance(last), 90, last)
        playhead = round((self.position - start) * width / span)
        painter.setPen(QPen(QColor("#f9f1ce"), 2))
        painter.drawLine(playhead, 0, playhead, 78)

    def mousePressEvent(self, event):
        start, span = self.viewport()
        ms = round(start + event.position().x() * span / max(1, self.width()))
        if 52 <= event.position().y() <= 75:
            for index, cue in enumerate(self.cues):
                if cue.start_ms <= ms < cue.end_ms:
                    self.selected.emit(index)
                    return
        self.seek.emit(ms)


class Editor(QMainWindow):
    def __init__(self, language: str):
        super().__init__()
        self.language = language
        self.settings = QSettings("sudo_pita", "Pitranscriptor")
        self.project = None
        self.saved_project = None
        self.project_path = None
        self.before = []
        self.after = []
        self.job = None
        self.preview = Preview()
        self.timeline = Timeline()
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.sink = QVideoSink(self)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoSink(self.sink)
        self.sink.videoFrameChanged.connect(self.preview.set_frame)
        self.player.positionChanged.connect(self.update_playhead)
        self.player.errorOccurred.connect(
            lambda error, detail: self.statusBar().showMessage(detail)
        )
        self.player.playbackStateChanged.connect(self.play_state_changed)
        self.timeline.seek.connect(self.seek_to)
        self.timeline.selected.connect(lambda index: self.list.setCurrentRow(index))
        self.preview.moved.connect(self.move_caption)
        self.setWindowTitle("Pitranscriptor")
        self.resize(1220, 790)
        self._build_menu()
        self._build_ui()
        self.refresh()

    def t(self, es, en):
        return en if self.language == "en" else es

    def _action(self, menu, text, callback, shortcut=None):
        action = menu.addAction(text)
        action.triggered.connect(callback)
        if shortcut is not None:
            action.setShortcut(shortcut)

    def _build_menu(self):
        file = self.menuBar().addMenu(self.t("Archivo", "File"))
        self._action(
            file,
            self.t("Abrir video…", "Open video…"),
            self.open_video,
            QKeySequence.StandardKey.Open,
        )
        self._action(file, self.t("Abrir proyecto…", "Open project…"), self.open_project)
        self._action(
            file,
            self.t("Guardar proyecto", "Save project"),
            self.save,
            QKeySequence.StandardKey.Save,
        )
        self._action(
            file, self.t("Guardar proyecto como…", "Save project as…"), lambda: self.save(True)
        )
        self._action(file, self.t("Exportar SRT…", "Export SRT…"), lambda: self.export_text("srt"))
        self._action(
            file, self.t("Exportar WebVTT…", "Export WebVTT…"), lambda: self.export_text("vtt")
        )
        self._action(file, self.t("Exportar video…", "Export video…"), self.export_movie)
        self._action(
            file, self.t("Descargar modelo Small…", "Download Small model…"), self.install_model
        )
        edit = self.menuBar().addMenu(self.t("Editar", "Edit"))
        self._action(edit, self.t("Deshacer", "Undo"), self.undo, QKeySequence.StandardKey.Undo)
        self._action(edit, self.t("Rehacer", "Redo"), self.redo, QKeySequence.StandardKey.Redo)
        self._action(
            edit, self.t("Guardar estilo como preset…", "Save style preset…"), self.save_preset
        )
        self._action(edit, self.t("Aplicar preset…", "Apply preset…"), self.apply_preset)
        help_menu = self.menuBar().addMenu(self.t("Ayuda", "Help"))
        self._action(help_menu, self.t("Acerca de", "About"), self.about)
        language = self.menuBar().addMenu(self.t("Idioma", "Language"))
        for code, name in (("es", "Español"), ("en", "English")):
            self._action(
                language, name, lambda checked=False, value=code: self.change_language(value)
            )

    def _combo(self, values):
        combo = QComboBox()
        for name, value in values:
            combo.addItem(name, value)
        return combo

    def _button(self, label, callback):
        button = QPushButton(label)
        button.clicked.connect(callback)
        return button

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        toolbar = QHBoxLayout()
        toolbar.addWidget(self._button(self.t("Abrir video", "Open video"), self.open_video))
        toolbar.addWidget(self._button(self.t("Modelo…", "Model…"), self.choose_model))
        self.language_mode = self._combo([("Español", "es"), ("English", "en"), ("Auto", None)])
        toolbar.addWidget(self.language_mode)
        self.device = self._combo([("CPU", "cpu"), ("NVIDIA CUDA", "cuda")])
        toolbar.addWidget(self.device)
        self.target = QSpinBox()
        self.target.setRange(1, 7)
        self.target.setValue(4)
        self.target.setPrefix(self.t("Objetivo ", "Target "))
        toolbar.addWidget(self.target)
        toolbar.addWidget(self._button(self.t("Pistas…", "Hints…"), self.choose_prompt))
        self.transcribe_button = self._button(self.t("Transcribir", "Transcribe"), self.transcribe)
        toolbar.addWidget(self.transcribe_button)
        self.cancel_button = self._button(self.t("Cancelar", "Cancel"), self.cancel_job)
        self.cancel_button.setEnabled(False)
        toolbar.addWidget(self.cancel_button)
        self.progress = QProgressBar()
        self.progress.setFixedWidth(130)
        self.progress.hide()
        toolbar.addWidget(self.progress)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        storage = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        )
        self.download_path = Path(storage) / "models" / "faster-whisper-small"
        workspace_model = Path("models/faster-whisper-small")
        default_model = (
            workspace_model.resolve() if model_ready(workspace_model) else self.download_path
        )
        self.model_path = Path(self.settings.value("model", str(default_model)))
        self.prompt = None

        split = QSplitter()
        layout.addWidget(split, 1)
        video = QWidget()
        video_layout = QVBoxLayout(video)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.addWidget(self.preview, 1)
        playback = QHBoxLayout()
        self.play = self._button(self.t("Reproducir", "Play"), self.toggle_play)
        self.play.setMinimumWidth(100)
        playback.addWidget(self.play)
        self.time_label = QLabel()
        playback.addWidget(self.time_label)
        speed = self._combo([(f"{rate:g}×", rate) for rate in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)])
        speed.setCurrentIndex(2)
        speed.currentIndexChanged.connect(lambda: self.player.setPlaybackRate(speed.currentData()))
        playback.addWidget(speed)
        playback.addStretch()
        zoom = self._combo([(f"{rate}×", rate) for rate in (1, 2, 4, 8)])
        zoom.currentIndexChanged.connect(lambda: self.set_zoom(zoom.currentData()))
        playback.addWidget(QLabel("Zoom"))
        playback.addWidget(zoom)
        video_layout.addLayout(playback)
        video_layout.addWidget(self.timeline)
        split.addWidget(video)

        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.addWidget(QLabel(self.t("Fragmentos", "Captions")))
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.select_cue)
        side_layout.addWidget(self.list, 1)
        buttons = QHBoxLayout()
        for label, action in (
            (self.t("Añadir", "Add"), self.add_cue),
            (self.t("Dividir", "Split"), self.split_cue),
            (self.t("Unir", "Join"), self.join_cue),
            (self.t("Duplicar", "Duplicate"), self.duplicate_cue),
            (self.t("Borrar", "Delete"), self.remove_cue),
        ):
            buttons.addWidget(self._button(label, action))
        side_layout.addLayout(buttons)
        fields = QWidget()
        form = QFormLayout(fields)
        self.text = QLineEdit()
        form.addRow(self.t("Texto", "Text"), self.text)
        self.start = QDoubleSpinBox()
        self.end = QDoubleSpinBox()
        for spin in (self.start, self.end):
            spin.setRange(0, 300)
            spin.setDecimals(3)
            spin.setSingleStep(0.05)
            spin.setSuffix(" s")
        times = QHBoxLayout()
        times.addWidget(self.start)
        times.addWidget(self.end)
        form.addRow(self.t("Inicio / fin", "Start / end"), times)
        self.speaker = QLineEdit()
        form.addRow(self.t("Hablante", "Speaker"), self.speaker)
        self.font = QFontComboBox()
        self.font.setMinimumWidth(100)
        self.size = QSpinBox()
        self.size.setRange(12, 200)
        fonts = QHBoxLayout()
        fonts.addWidget(self.font, 1)
        fonts.addWidget(self.size)
        form.addRow(self.t("Fuente / tamaño", "Font / size"), fonts)
        self.x = QDoubleSpinBox()
        self.y = QDoubleSpinBox()
        self.opacity = QDoubleSpinBox()
        for spin in (self.x, self.y, self.opacity):
            spin.setRange(0, 1)
            spin.setSingleStep(0.01)
            spin.setDecimals(3)
        position = QHBoxLayout()
        position.addWidget(self.x)
        position.addWidget(self.y)
        form.addRow(self.t("Posición X / Y", "Position X / Y"), position)
        self.color = QLineEdit()
        self.background = QLineEdit()
        self.outline = QLineEdit()
        self.highlight = QLineEdit()
        form.addRow(
            self.t("Texto / fondo", "Text / fill"), self._fields(self.color, self.background)
        )
        form.addRow(
            self.t("Contorno / resaltado", "Outline / highlight"),
            self._fields(self.outline, self.highlight),
        )
        form.addRow(self.t("Opacidad de fondo", "Fill opacity"), self.opacity)
        self.bold = QCheckBox(self.t("Negrita", "Bold"))
        self.shadow = QCheckBox(self.t("Sombra", "Shadow"))
        form.addRow(self._fields(self.bold, self.shadow))
        self.align = self._combo(
            [
                (self.t(es, en), key)
                for es, en, key in (
                    ("Izquierda", "Left", "left"),
                    ("Centro", "Center", "center"),
                    ("Derecha", "Right", "right"),
                )
            ]
        )
        self.effect = self._combo(
            [
                (self.t(es, en), key)
                for es, en, key in (
                    ("Sin efecto", "No effect", "none"),
                    ("Resaltar palabra", "Highlight word", "highlight"),
                    ("Aparición por palabra", "Word reveal", "appear"),
                    ("Fundido", "Fade", "fade"),
                )
            ]
        )
        form.addRow(
            self.t("Alineación / efecto", "Align / effect"), self._fields(self.align, self.effect)
        )
        form.addRow(
            self._fields(
                self._button(self.t("Aplicar", "Apply"), self.apply_fields),
                self._button(self.t("Tiempos de palabras…", "Word times…"), self.edit_word),
            )
        )
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(fields)
        side_layout.addWidget(scroll, 2)
        split.addWidget(side)
        split.setSizes([720, 475])
        self.statusBar().showMessage(self.t("Creado por sudo_pita", "Created by sudo_pita"))

    def _fields(self, *widgets):
        row = QHBoxLayout()
        for widget in widgets:
            row.addWidget(widget)
        return row

    def about(self):
        QMessageBox.about(
            self,
            "Pitranscriptor",
            self.t("Creado por sudo_pita", "Created by sudo_pita")
            + '<p><a href="https://www.instagram.com/sudo_pita/">Instagram</a> · '
            '<a href="https://www.tiktok.com/@sudo_pita">TikTok</a> · '
            '<a href="https://www.youtube.com/@sudo_pita">YouTube</a> · '
            '<a href="https://www.facebook.com/profile.php?id=61589854056244">Facebook</a></p>',
        )

    def change_language(self, language):
        self.settings.setValue("language", language)
        self.statusBar().showMessage(
            self.t(
                "El idioma cambiará al volver a abrir Pitranscriptor.",
                "The language will change next time you open Pitranscriptor.",
            )
        )

    def show_error(self, error):
        QMessageBox.warning(self, "Pitranscriptor", str(error))

    def confirm_discard(self):
        if self.job is not None:
            self.statusBar().showMessage(self.t("Hay un proceso en curso.", "A task is running."))
            return False
        if self.project == self.saved_project:
            return True
        answer = QMessageBox.question(
            self,
            "Pitranscriptor",
            self.t("¿Guardar cambios?", "Save your changes?"),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save()
        return answer == QMessageBox.StandardButton.Discard

    def closeEvent(self, event):
        if self.confirm_discard():
            self.player.stop()
            event.accept()
        else:
            event.ignore()

    def open_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.t("Abrir video", "Open video"),
            "",
            "Video (*.mp4 *.mov *.mkv *.webm *.avi);;*",
        )
        if path and self.confirm_discard():
            try:
                source = Path(path).resolve()
                duration, _ = inspect_media(source, require_video=True)
                self.set_project(Project(str(source), duration))
            except (ValueError, OSError, ImportError) as error:
                self.show_error(error)

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.t("Abrir proyecto", "Open project"), "", "Pitranscriptor (*.pitranscriptor)"
        )
        if path and self.confirm_discard():
            self.load_path(Path(path))

    def load_path(self, path):
        try:
            project = load_project(path)
            if not Path(project.source).is_file():
                self.show_error(
                    self.t(
                        "No se encuentra el medio. Selecciona su nueva ubicación.",
                        "The media is missing. Select its new location.",
                    )
                )
                source, _ = QFileDialog.getOpenFileName(
                    self, self.t("Localizar medio", "Locate media")
                )
                if not source:
                    return
                duration, _ = inspect_media(Path(source))
                saved = project
                project = replace(project, source=source, duration_ms=duration)
                self.set_project(project, path)
                self.saved_project = saved
                self.refresh()
                return
            self.set_project(project, path)
        except (OSError, ValueError, ImportError) as error:
            self.show_error(error)

    def set_project(self, project, path=None):
        self.player.stop()
        self.preview.frame = QImage()
        self.preview.position = 0
        self.project = project
        self.saved_project = project
        self.project_path = path
        self.before.clear()
        self.after.clear()
        self.timeline.peaks = ()
        self.timeline.position = 0
        self.player.setSource(QUrl.fromLocalFile(project.source))
        self.refresh(0 if project.cues else -1)
        self.start_job(
            lambda progress, cancelled: audio_peaks(Path(project.source), project.duration_ms),
            self.set_waveform,
            waveform=True,
        )

    def set_waveform(self, peaks):
        self.timeline.peaks = peaks
        self.timeline.update()

    def save(self, choose_path=False):
        if self.project is None:
            return False
        path = self.project_path
        if path is None or choose_path:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                self.t("Guardar proyecto", "Save project"),
                str(Path(self.project.source).with_suffix(".pitranscriptor")),
                "Pitranscriptor (*.pitranscriptor)",
            )
            if not filename:
                return False
            path = Path(filename)
            if path.suffix.lower() != ".pitranscriptor":
                path = path.with_name(path.name + ".pitranscriptor")
        try:
            overwrite = self.confirm_output(path)
            save_project(path, self.project, overwrite=overwrite)
        except InterruptedError:
            return False
        except (OSError, ValueError) as error:
            self.show_error(error)
            return False
        self.project_path = path
        self.saved_project = self.project
        self.refresh()
        return True

    def confirm_output(self, path):
        if path.resolve() == Path(self.project.source).resolve():
            raise ValueError(
                self.t("Elige una ruta distinta del medio.", "Choose a path other than the media.")
            )
        exists = path.exists()
        if exists and (self.project_path is None or path.resolve() != self.project_path.resolve()):
            answer = QMessageBox.question(
                self, "Pitranscriptor", self.t("¿Reemplazar el archivo?", "Replace the file?")
            )
            if answer != QMessageBox.StandardButton.Yes:
                raise InterruptedError
        return exists

    def export_text(self, extension):
        if self.project is None:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            self.t("Exportar", "Export"),
            str(Path(self.project.source).with_suffix(f".{extension}")),
            f"*.{extension}",
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.lower() != f".{extension}":
            path = path.with_name(path.name + f".{extension}")
        try:
            overwrite = self.confirm_output(path)
            text = render_subtitles(self.project.cues, webvtt=extension == "vtt")
            write_text(path, text, overwrite=overwrite)
            self.statusBar().showMessage(str(path))
        except InterruptedError:
            pass
        except (OSError, ValueError) as error:
            self.show_error(error)

    def choose_model(self):
        path = QFileDialog.getExistingDirectory(
            self, self.t("Carpeta del modelo local", "Local model folder")
        )
        if path:
            self.model_path = Path(path)
            self.settings.setValue("model", path)
            self.statusBar().showMessage(path)

    def install_model(self):
        if self.job is not None:
            return
        if model_ready(self.download_path):
            self.use_model(self.download_path)
            return
        answer = QMessageBox.question(
            self,
            "Pitranscriptor",
            self.t(
                "¿Descargar el modelo multilingüe Small (aprox. 490 MB)?",
                "Download the multilingual Small model (about 490 MB)?",
            ),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.start_job(
            lambda progress, cancelled: download_small(self.download_path),
            self.use_model,
            can_cancel=False,
        )
        self.progress.setRange(0, 0)

    def use_model(self, path):
        self.model_path = path
        self.settings.setValue("model", str(path))
        self.statusBar().showMessage(self.t("Modelo local disponible.", "Local model is ready."))

    def export_movie(self):
        if self.project is None or self.job is not None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(self.t("Exportar video", "Export video"))
        form = QFormLayout(dialog)
        file_format = self._combo([("MP4", "mp4"), ("MOV", "mov")])
        quality = self._combo(
            [
                (self.t(es, en), code)
                for es, en, code in (
                    ("Muy alta", "Very high", "original"),
                    ("Alta", "High", "high"),
                    ("Media", "Medium", "medium"),
                    ("Baja", "Low", "low"),
                )
            ]
        )
        quality.setCurrentIndex(1)
        height = QSpinBox()
        height.setRange(0, 4320)
        height.setSpecialValueText(self.t("Original", "Source"))
        fps = self._combo(
            [(self.t("Original", "Source"), None)]
            + [(str(rate), Fraction(rate)) for rate in (24, 25, 30, 50, 60)]
        )
        form.addRow(self.t("Formato", "Format"), file_format)
        form.addRow(self.t("Calidad H.264", "H.264 quality"), quality)
        form.addRow(self.t("Altura máxima (px)", "Maximum height (px)"), height)
        form.addRow(self.t("Cuadros por segundo", "Frames per second"), fps)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        extension = file_format.currentData()
        source = Path(self.project.source)
        default = source.with_name(f"{source.stem}-subtitulado.{extension}")
        filename, _ = QFileDialog.getSaveFileName(
            self, dialog.windowTitle(), str(default), f"*.{extension}"
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.lower() != f".{extension}":
            path = path.with_name(path.name + f".{extension}")
        if self.project_path and path.resolve() == self.project_path.resolve():
            self.show_error(
                self.t(
                    "Elige una ruta distinta del proyecto.", "Choose a path other than the project."
                )
            )
            return
        try:
            overwrite = self.confirm_output(path)
        except InterruptedError:
            return
        except (OSError, ValueError) as error:
            self.show_error(error)
            return
        project = self.project
        options = {
            "quality": quality.currentData(),
            "height_limit": height.value() or None,
            "fps": fps.currentData(),
            "overwrite": overwrite,
        }
        self.player.pause()
        self.start_job(
            lambda progress, cancelled: export_video(
                project, path, **options, progress=progress, cancelled=cancelled
            ),
            lambda result: self.video_exported(path, result),
        )

    def video_exported(self, path, result):
        audio = {
            "copy": self.t("Audio AAC original", "Original AAC audio"),
            "aac": self.t("Audio convertido a AAC", "Audio converted to AAC"),
            "none": self.t("Sin pista de audio", "No audio track"),
        }[result.audio_mode]
        self.statusBar().showMessage(f"{result.width} × {result.height} · {audio} · {path}")

    def choose_prompt(self):
        options = [
            self.t("Sin pistas", "No hints"),
            self.t("Cargar archivo de texto", "Load a text file"),
        ]
        choice, ok = QInputDialog.getItem(
            self, "Pitranscriptor", self.t("Pistas del modelo", "Model hints"), options, 0, False
        )
        if ok and choice == options[0]:
            self.prompt = None
        elif ok:
            path, _ = QFileDialog.getOpenFileName(self, options[1], "", "Text (*.txt *.md)")
            if path:
                try:
                    self.prompt = Path(path).read_text(encoding="utf-8-sig")
                except (OSError, ValueError) as error:
                    self.show_error(error)

    def transcribe(self):
        if self.project is None or self.job is not None:
            return
        if not model_ready(self.model_path):
            self.install_model()
            return
        if (
            self.project.cues
            and QMessageBox.question(
                self,
                "Pitranscriptor",
                self.t(
                    "¿Reemplazar los fragmentos con una nueva transcripción?",
                    "Replace the captions with a new transcription?",
                ),
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.player.pause()
        path = Path(self.project.source)
        language = self.language_mode.currentData()
        model = self.model_path
        target = self.target.value()
        device = self.device.currentData()
        prompt = self.prompt
        self.start_job(
            lambda progress, cancelled: transcribe_project(
                path,
                model,
                language=language,
                target=target,
                device=device,
                vocabulary=prompt,
                progress=progress,
                cancelled=cancelled,
            ),
            lambda project: self.commit(project, 0),
        )

    def start_job(self, operation, callback, *, waveform=False, can_cancel=True):
        self.job = Job(operation, self)
        self.job_callback = callback
        self.job_waveform = waveform
        self.job.progress.connect(self.progress.setValue)
        self.job.finished.connect(self.finish_job)
        self.transcribe_button.setEnabled(False)
        self.cancel_button.setEnabled(not waveform and can_cancel)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(not waveform)
        self.job.start()

    def finish_job(self):
        job = self.job
        self.job = None
        self.progress.hide()
        self.transcribe_button.setEnabled(self.project is not None)
        self.cancel_button.setEnabled(False)
        if isinstance(job.error, InterruptedError) or job.cancel.is_set():
            self.statusBar().showMessage(self.t("Proceso cancelado.", "Task canceled."))
        elif job.error is not None:
            if self.job_waveform:
                self.statusBar().showMessage(str(job.error))
            else:
                self.show_error(job.error)
        else:
            self.job_callback(job.result)
        job.deleteLater()

    def cancel_job(self):
        if self.job is not None:
            self.job.cancel.set()
            self.cancel_button.setEnabled(False)
            self.statusBar().showMessage(self.t("Cancelando…", "Canceling…"))

    def toggle_play(self):
        if self.project is not None:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
            else:
                self.player.play()

    def play_state_changed(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.play.setText(self.t("Pausar", "Pause") if playing else self.t("Reproducir", "Play"))
        self.update_playhead(self.player.position())

    def set_zoom(self, zoom):
        self.timeline.zoom = zoom
        self.timeline.update()

    def seek_to(self, position):
        self.list.setCurrentRow(-1)
        self.player.setPosition(position)

    def update_playhead(self, position):
        duration = self.project.duration_ms if self.project else 0
        self.time_label.setText(f"{timestamp(position)}  /  {timestamp(duration)}")
        self.timeline.position = position
        self.timeline.update()
        selected = self.current_cue()
        playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        cues = self.project.cues if self.project else ()
        index = bisect_right(cues, position, key=lambda cue: cue.start_ms) - 1
        active = cues[index] if index >= 0 and position < cues[index].end_ms else None
        self.preview.cue = selected if selected and not playing else active
        self.preview.position = position
        if (
            selected
            and self.preview.cue is selected
            and not selected.start_ms <= position < selected.end_ms
        ):
            self.preview.position = (selected.start_ms + selected.end_ms) // 2
        self.preview.editable = selected is not None and not playing
        self.preview.update()

    def current_cue(self):
        index = self.list.currentRow()
        if self.project and 0 <= index < len(self.project.cues):
            return self.project.cues[index]
        return None

    def refresh(self, index=None):
        if index is None:
            index = self.list.currentRow()
        self.list.blockSignals(True)
        self.list.clear()
        self.timeline.cues = self.project.cues if self.project else ()
        self.timeline.duration = self.project.duration_ms if self.project else 1
        for cue in self.timeline.cues:
            speaker = f" [{cue.speaker}]" if cue.speaker else ""
            self.list.addItem(f"{timestamp(cue.start_ms)}{speaker}   {cue.text}")
        self.list.setCurrentRow(min(index, len(self.timeline.cues) - 1))
        self.list.blockSignals(False)
        self.select_cue(self.list.currentRow(), seek=False)
        label = f" · {Path(self.project.source).name}" if self.project else ""
        self.setWindowTitle(
            "Pitranscriptor" + label + (" *" if self.project != self.saved_project else "")
        )
        self.transcribe_button.setEnabled(self.project is not None and self.job is None)

    def select_cue(self, index, *, seek=True):
        cue = self.current_cue()
        self.timeline.selection = index
        self.text.setText(cue.text if cue else "")
        self.speaker.setText(cue.speaker if cue else "")
        self.start.setValue(cue.start_ms / 1000 if cue else 0)
        self.end.setValue(cue.end_ms / 1000 if cue else 0)
        style = cue.style if cue else Style()
        self.font.setCurrentFont(QFont(style.font) if style.font else QApplication.font())
        self.size.setValue(style.size)
        self.opacity.setValue(style.opacity)
        self.x.setValue(style.x)
        self.y.setValue(style.y)
        self.color.setText(style.color)
        self.background.setText(style.background)
        self.outline.setText(style.outline)
        self.highlight.setText(style.highlight)
        self.bold.setChecked(style.bold)
        self.shadow.setChecked(style.shadow)
        self.align.setCurrentIndex(self.align.findData(style.align))
        self.effect.setCurrentIndex(self.effect.findData(style.effect))
        if seek and cue:
            self.player.pause()
            self.player.setPosition(cue.start_ms)
        self.update_playhead(self.player.position())

    def commit(self, project, index):
        if project == self.project:
            return
        self.before.append(self.project)
        self.after.clear()
        self.project = project
        self.refresh(index)

    def undo(self):
        if self.before and self.job is None:
            self.after.append(self.project)
            self.project = self.before.pop()
            self.refresh()

    def redo(self):
        if self.after and self.job is None:
            self.before.append(self.project)
            self.project = self.after.pop()
            self.refresh()

    def splice(self, index, count, cues):
        if self.project is None or self.job is not None:
            return
        try:
            all_cues = (*self.project.cues[:index], *cues, *self.project.cues[index + count :])
            project = self.project.with_cues(all_cues)
            self.commit(project, project.cues.index(cues[0]) if cues else index)
        except ValueError as error:
            self.show_error(error)

    def apply_fields(self):
        cue = self.current_cue()
        if cue is None:
            return
        try:
            font = self.font.currentFont().family()
            if font == QApplication.font().family() and not cue.style.font:
                font = ""
            style = Style(
                x=self.x.value(),
                y=self.y.value(),
                size=self.size.value(),
                color=self.color.text(),
                background=self.background.text(),
                opacity=self.opacity.value(),
                bold=self.bold.isChecked(),
                font=font,
                outline=self.outline.text(),
                shadow=self.shadow.isChecked(),
                align=self.align.currentData(),
                highlight=self.highlight.text(),
                effect=self.effect.currentData(),
            )
            new = edit_cue(
                cue,
                self.text.text(),
                round(self.start.value() * 1000),
                round(self.end.value() * 1000),
            )
            self.splice(
                self.list.currentRow(), 1, [replace(new, style=style, speaker=self.speaker.text())]
            )
        except ValueError as error:
            self.show_error(error)

    def move_caption(self, x, y):
        cue = self.current_cue()
        if cue:
            new = replace(cue, style=replace(cue.style, x=round(x, 3), y=round(y, 3)))
            self.splice(self.list.currentRow(), 1, [new])

    def edit_word(self):
        cue = self.current_cue()
        if not cue or not cue.words:
            self.statusBar().showMessage(
                self.t(
                    "Este fragmento no tiene marcas por palabra.", "This caption has no word times."
                )
            )
            return
        choices = [f"{i + 1} · {word.text}" for i, word in enumerate(cue.words)]
        chosen, ok = QInputDialog.getItem(
            self, "Pitranscriptor", self.t("Palabra", "Word"), choices, 0, False
        )
        if not ok:
            return
        index = choices.index(chosen)
        word = cue.words[index]
        value, ok = QInputDialog.getText(
            self,
            "Pitranscriptor",
            self.t(
                "Inicio y fin en ms, separados por coma",
                "Start and end in ms, separated by a comma",
            ),
            text=f"{word.start_ms}, {word.end_ms}",
        )
        if ok:
            try:
                start, end = (int(part.strip()) for part in value.split(","))
                words = list(cue.words)
                words[index] = Word(word.text, start, end)
                self.splice(self.list.currentRow(), 1, [replace(cue, words=tuple(words))])
            except ValueError as error:
                self.show_error(error)

    def add_cue(self):
        if self.project is None:
            return
        position = self.player.position()
        cues = self.project.cues
        index = bisect_right(cues, position, key=lambda cue: cue.start_ms)
        start = max(position, cues[index - 1].end_ms) if index else position
        limit = cues[index].start_ms if index < len(cues) else self.project.duration_ms
        end = min(limit, start + 1500)
        if end <= start:
            self.show_error(
                self.t(
                    "Coloca el cursor en un espacio libre.",
                    "Place the playhead in an empty interval.",
                )
            )
            return
        value, ok = QInputDialog.getText(
            self, "Pitranscriptor", self.t("Texto del fragmento", "Caption text")
        )
        if ok:
            try:
                self.splice(index, 0, [Cue(start, end, " ".join(value.split()))])
            except ValueError as error:
                self.show_error(error)

    def split_cue(self):
        cue = self.current_cue()
        if not cue or len(cue.text.split()) < 2:
            return
        tokens = cue.text.split()
        number, ok = QInputDialog.getInt(
            self,
            "Pitranscriptor",
            self.t("Dividir después de la palabra", "Split after word"),
            len(tokens) // 2,
            1,
            len(tokens) - 1,
        )
        if not ok:
            return
        boundary = cue.words[number].start_ms if cue.words else (cue.start_ms + cue.end_ms) // 2
        try:
            left = replace(
                cue, end_ms=boundary, text=" ".join(tokens[:number]), words=cue.words[:number]
            )
            right = replace(
                cue, start_ms=boundary, text=" ".join(tokens[number:]), words=cue.words[number:]
            )
            self.splice(self.list.currentRow(), 1, [left, right])
        except ValueError as error:
            self.show_error(error)

    def join_cue(self):
        cue = self.current_cue()
        index = self.list.currentRow()
        if not cue or index + 1 >= len(self.project.cues):
            return
        other = self.project.cues[index + 1]
        try:
            merged = replace(
                cue,
                end_ms=other.end_ms,
                text=f"{cue.text} {other.text}",
                words=cue.words + other.words if cue.words and other.words else (),
            )
            self.splice(index, 2, [merged])
        except ValueError as error:
            self.show_error(error)

    def duplicate_cue(self):
        cue = self.current_cue()
        if not cue:
            return
        index = self.list.currentRow()
        limit = (
            self.project.cues[index + 1].start_ms
            if index + 1 < len(self.project.cues)
            else self.project.duration_ms
        )
        duration = cue.end_ms - cue.start_ms
        if cue.end_ms + duration > limit:
            self.show_error(
                self.t(
                    "No hay espacio para una copia después del fragmento.",
                    "There is no room for a copy after this caption.",
                )
            )
            return
        words = tuple(
            replace(word, start_ms=word.start_ms + duration, end_ms=word.end_ms + duration)
            for word in cue.words
        )
        self.splice(
            index + 1,
            0,
            [replace(cue, start_ms=cue.end_ms, end_ms=cue.end_ms + duration, words=words)],
        )

    def remove_cue(self):
        if self.current_cue():
            self.splice(self.list.currentRow(), 1, [])

    def save_preset(self):
        cue = self.current_cue()
        if not cue:
            return
        name, ok = QInputDialog.getText(
            self, "Pitranscriptor", self.t("Nombre del preset", "Preset name")
        )
        if ok and name.strip():
            presets = json.loads(self.settings.value("presets", "{}"))
            if (
                name in presets
                and QMessageBox.question(
                    self, "Pitranscriptor", self.t("¿Reemplazar el preset?", "Replace this preset?")
                )
                != QMessageBox.StandardButton.Yes
            ):
                return
            presets[name] = asdict(cue.style)
            self.settings.setValue("presets", json.dumps(presets, ensure_ascii=False))

    def apply_preset(self):
        cue = self.current_cue()
        presets = json.loads(self.settings.value("presets", "{}"))
        if cue and presets:
            name, ok = QInputDialog.getItem(
                self, "Pitranscriptor", "Preset", sorted(presets), 0, False
            )
            if ok:
                self.splice(self.list.currentRow(), 1, [replace(cue, style=Style(**presets[name]))])


def configure_application(app):
    app.setStyle("Fusion")
    if os.name == "nt" and app.platformName() == "offscreen":
        fonts = Path(os.environ["SystemRoot"]) / "Fonts"
        for filename in ("segoeui.ttf", "segoeuib.ttf"):
            QFontDatabase.addApplicationFont(str(fonts / filename))
        app.setFont(QFont("Segoe UI", 9))
    app.setStyleSheet("""
        QMainWindow, QDialog { background: #d7e0e6; }
        QMenuBar { background: #d7e0e6; }
        QPushButton { padding: 5px 9px; }
        QToolTip { background: #fff3ce; color: #172635; }
    """)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pitranscriptor-desktop")
    parser.add_argument("project", type=Path, nargs="?")
    parser.add_argument("--language", choices=("es", "en"))
    args = parser.parse_args(argv)
    app = QApplication([sys.argv[0]])
    app.setOrganizationName("sudo_pita")
    app.setApplicationName("Pitranscriptor")
    configure_application(app)
    settings = QSettings("sudo_pita", "Pitranscriptor")
    editor = Editor(args.language or settings.value("language", "es"))
    editor.show()
    if args.project:
        editor.load_path(args.project)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
