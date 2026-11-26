"""Editor de subtítulos de escritorio."""

import argparse
import io
import json
import os
import sys
import wave
from bisect import bisect_right
from contextlib import ExitStack
from dataclasses import asdict, replace
from fractions import Fraction
from pathlib import Path
from threading import Event

from PySide6.QtCore import (
    QItemSelection,
    QItemSelectionModel,
    QPointF,
    QRectF,
    QSettings,
    QSignalBlocker,
    QStandardPaths,
    Qt,
    QThread,
    QUrl,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QKeySequence, QPainter, QPen
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoSink
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFontComboBox,
    QFormLayout,
    QFrame,
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

from pitranscriptor.models import (
    MEDIUM_MODEL,
    SMALL_MODEL,
    TURBO_MODEL,
    ModelPreset,
    download_model,
    model_ready,
)
from pitranscriptor.painting import paint_caption
from pitranscriptor.project import (
    Project,
    edit_cue,
    load_project,
    retime_cue,
    save_project,
    write_text,
)
from pitranscriptor.retro_theme import (
    CLIP,
    GRID,
    INK,
    PLAYHEAD,
    STYLESHEET,
    TIMECODE,
    TRACE,
    WORKSPACE,
    retro_palette,
)
from pitranscriptor.subtitles import Cue, Style, render_subtitles
from pitranscriptor.transcription import DEFAULT_RIGOR, inspect_media
from pitranscriptor.transcription_job import WORKER_FLAG, run_transcription, worker
from pitranscriptor.video_export import export_video
from pitranscriptor.vocabulary import suggest_script_terms
from pitranscriptor.vocabulary_picker import VocabularyPicker
from pitranscriptor.waveform import audio_peaks

FILLERS = {"eh", "em", "mmm", "hmm", "uh", "um", "eee"}
SPEAKER_COLORS = ("#ffffff", "#a9e8ff", "#ffdc86", "#c9f3a7", "#f7b3dc", "#dac4ff")


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
        self.empty_text = ""

    def set_frame(self, frame):
        if frame.isValid():
            self.frame = frame.toImage()
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(WORKSPACE))
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
        elif self.empty_text:
            painter.setPen(QColor(GRID))
            for x in range(0, self.width(), 20):
                painter.drawLine(x, 0, x, self.height())
            for y in range(0, self.height(), 20):
                painter.drawLine(0, y, self.width(), y)
            painter.setPen(QColor(TIMECODE))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.empty_text)
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
    selected = Signal(object, bool)
    selection_started = Signal()
    TRACK_TOP = 52
    TRACK_HEIGHT = 23

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(95)
        self.duration = 1
        self.position = 0
        self.zoom = 1
        self.cues = ()
        self.peaks = ()
        self.selection = frozenset()
        self.drag_start = None
        self.drag_end = None
        self.drag_viewport = None

    def viewport(self):
        if self.drag_viewport is not None:
            return self.drag_viewport
        span = self.duration / self.zoom
        return max(0, min(self.duration - span, self.position - span * 0.35)), span

    def time_at(self, x):
        start, span = self.viewport()
        return start + max(0, min(1, x / max(1, self.width()))) * span

    def rows_in_range(self, x1, x2):
        start, end = sorted((self.time_at(x1), self.time_at(x2)))
        if start == end:
            return tuple(i for i, cue in enumerate(self.cues) if cue.start_ms <= start < cue.end_ms)
        return tuple(
            i for i, cue in enumerate(self.cues) if cue.start_ms < end and start < cue.end_ms
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(WORKSPACE))
        start, span = self.viewport()
        width = self.width()
        painter.setPen(QColor(GRID))
        for x in range(0, width, max(1, width // 10)):
            painter.drawLine(x, 0, x, 77)
        for y in (28, 48, 78):
            painter.drawLine(0, y, width, y)
        for index, peak in enumerate(self.peaks):
            x = round((index * self.duration / len(self.peaks) - start) * width / span)
            if 0 <= x <= width:
                level = round(peak * 18)
                painter.setPen(QColor(TRACE))
                painter.drawLine(x, 28 - level, x, 28 + level)
        band = None
        selection = self.selection
        if self.drag_end is not None:
            left, right = sorted((self.drag_start, self.drag_end))
            selection = frozenset(self.rows_in_range(left, right))
            band = QRectF(left, self.TRACK_TOP - 2, right - left, self.TRACK_HEIGHT + 4)
            painter.fillRect(band, QColor(49, 99, 120, 140))
        for index, cue in enumerate(self.cues):
            left = (cue.start_ms - start) * width / span
            right = (cue.end_ms - start) * width / span
            if right <= 0 or left >= width:
                continue
            box = QRectF(left, self.TRACK_TOP, max(1, right - left - 2), self.TRACK_HEIGHT)
            painter.fillRect(box, QColor(PLAYHEAD if index in selection else CLIP))
            if index in selection:
                painter.setPen(QPen(QColor(INK), 1))
                painter.drawRect(box.adjusted(1, 1, -1, -1))
            if box.width() > 44:
                painter.setPen(QColor(INK))
                painter.drawText(
                    box.adjusted(4, 0, -3, 0),
                    Qt.AlignmentFlag.AlignVCenter,
                    painter.fontMetrics().elidedText(
                        cue.text, Qt.TextElideMode.ElideRight, int(box.width() - 7)
                    ),
                )
        if band is not None:
            painter.setPen(QPen(QColor(TIMECODE), 1, Qt.PenStyle.DashLine))
            painter.drawRect(band)
        painter.setPen(QColor(TIMECODE))
        painter.drawText(5, 90, timestamp(round(start)))
        last = timestamp(round(start + span))
        painter.drawText(width - 5 - painter.fontMetrics().horizontalAdvance(last), 90, last)
        playhead = round((self.position - start) * width / span)
        painter.setPen(QPen(QColor(PLAYHEAD), 2))
        painter.drawLine(playhead, 0, playhead, 78)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        point = event.position()
        if self.TRACK_TOP <= point.y() < self.TRACK_TOP + self.TRACK_HEIGHT:
            self.selection_started.emit()
            self.drag_viewport = self.viewport()
            self.drag_start = point.x()
            self.drag_end = None
        else:
            self.seek.emit(round(self.time_at(point.x())))
        event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_start is None:
            return super().mouseMoveEvent(event)
        x = max(0, min(self.width(), event.position().x()))
        if (
            self.drag_end is not None
            or abs(x - self.drag_start) >= QApplication.startDragDistance()
        ):
            self.drag_end = x
            self.update()
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.drag_start is None:
            return super().mouseReleaseEvent(event)
        x = max(0, min(self.width(), event.position().x()))
        dragged = (
            self.drag_end is not None
            or abs(x - self.drag_start) >= QApplication.startDragDistance()
        )
        rows = self.rows_in_range(self.drag_start, x if dragged else self.drag_start)
        position = round(self.time_at(self.drag_start))
        self.drag_start = self.drag_end = self.drag_viewport = None
        if dragged or rows:
            self.selected.emit(rows, not dragged)
        else:
            self.seek.emit(position)
        self.update()
        event.accept()


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
        self.timeline.selection_started.connect(self.player.pause)
        self.timeline.selected.connect(self.set_caption_selection)
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
        models = file.addMenu(self.t("Modelos locales", "Local models"))
        for preset in (SMALL_MODEL, MEDIUM_MODEL, TURBO_MODEL):
            self._action(
                models,
                self.t(f"Usar o descargar {preset.name}…", f"Use or download {preset.name}…"),
                lambda checked=False, value=preset: self.install_model(value),
            )
        edit = self.menuBar().addMenu(self.t("Editar", "Edit"))
        self._action(edit, self.t("Deshacer", "Undo"), self.undo, QKeySequence.StandardKey.Undo)
        self._action(edit, self.t("Rehacer", "Redo"), self.redo, QKeySequence.StandardKey.Redo)
        self._action(
            edit, self.t("Guardar estilo como preset…", "Save style preset…"), self.save_preset
        )
        self._action(edit, self.t("Aplicar preset…", "Apply preset…"), self.apply_preset)
        self._action(edit, self.t("Revisar muletillas…", "Review fillers…"), self.review_fillers)
        self._action(
            edit,
            self.t("Revisar palabras dudosas…", "Review uncertain words…"),
            self.review_uncertain,
        )
        self._action(edit, self.t("Colorear por hablante", "Color by speaker"), self.color_speakers)
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
        central.setObjectName("desk")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(9, 8, 9, 7)
        layout.setSpacing(7)
        brand = QLabel("PITRANSCRIPTOR")
        brand.setObjectName("brand")
        layout.addWidget(brand)
        tray = QWidget()
        tray.setObjectName("commandTray")
        toolbar = QHBoxLayout(tray)
        toolbar.setContentsMargins(7, 6, 7, 6)
        toolbar.addWidget(self._button(self.t("Abrir video", "Open video"), self.open_video))
        self.model_button = self._button(self.t("Modelo…", "Model…"), self.choose_model)
        toolbar.addWidget(self.model_button)
        self.language_mode = self._combo(
            [("Español", "es"), ("Español + English", "mixed"), ("English", "en"), ("Auto", None)]
        )
        toolbar.addWidget(self.language_mode)
        self.device = self._combo([("CPU", "cpu"), ("NVIDIA CUDA", "cuda")])
        toolbar.addWidget(self.device)
        self.rigor = self._combo(
            [
                (self.t("Rápido", "Fast"), "fast"),
                (self.t("Equilibrado", "Balanced"), DEFAULT_RIGOR),
                (self.t("Minucioso", "Thorough"), "thorough"),
            ]
        )
        preferred = self.rigor.findData(self.settings.value("rigor", DEFAULT_RIGOR))
        self.rigor.setCurrentIndex(
            preferred if preferred >= 0 else self.rigor.findData(DEFAULT_RIGOR)
        )
        self.rigor.currentIndexChanged.connect(
            lambda: self.settings.setValue("rigor", self.rigor.currentData())
        )
        self.rigor.setToolTip(
            self.t(
                "Un mayor rigor explora más alternativas de transcripción y puede tardar más.",
                "Higher rigor explores more transcription alternatives and can take longer.",
            )
        )
        rigor_label = QLabel(self.t("Rigor", "Rigor"))
        rigor_label.setBuddy(self.rigor)
        toolbar.addWidget(rigor_label)
        toolbar.addWidget(self.rigor)
        self.target = QSpinBox()
        self.target.setRange(1, 7)
        self.target.setValue(4)
        self.target.setPrefix(self.t("Objetivo ", "Target "))
        toolbar.addWidget(self.target)
        self.hints_button = self._button(self.t("Pistas…", "Hints…"), self.choose_prompt)
        toolbar.addWidget(self.hints_button)
        self.transcribe_button = self._button(self.t("Transcribir", "Transcribe"), self.transcribe)
        self.transcribe_button.setObjectName("primary")
        toolbar.addWidget(self.transcribe_button)
        self.cancel_button = self._button(self.t("Cancelar", "Cancel"), self.cancel_job)
        self.cancel_button.setEnabled(False)
        toolbar.addWidget(self.cancel_button)
        self.progress = QProgressBar()
        self.progress.setFixedWidth(130)
        self.progress.hide()
        toolbar.addWidget(self.progress)
        toolbar.addStretch()
        layout.addWidget(tray)
        storage = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        )
        self.model_storage = Path(storage) / "models"
        workspace_model = Path("models") / SMALL_MODEL.directory
        default_model = (
            workspace_model.resolve()
            if model_ready(workspace_model)
            else self.model_storage / SMALL_MODEL.directory
        )
        self.model_path = Path(self.settings.value("model", str(default_model)))
        self.model_button.setToolTip(str(self.model_path))
        self.prompt = None
        self.context_hint = ""
        self.technical_terms = tuple(self.settings.value("technicalTerms", [], type=list))
        self.update_hints_button()

        split = QSplitter()
        layout.addWidget(split, 1)
        video = QWidget()
        video.setObjectName("workPanel")
        video_layout = QVBoxLayout(video)
        video_layout.setContentsMargins(7, 7, 7, 7)
        video_layout.setSpacing(5)
        video_layout.addWidget(self.panel_title(self.t("Monitor", "Monitor")))
        self.media_name = QLabel()
        self.media_name.setObjectName("mediaName")
        video_layout.addWidget(self.media_name)
        video_layout.addWidget(self.inset(self.preview, "monitor"), 1)
        playback = QHBoxLayout()
        self.play = self._button(self.t("Reproducir", "Play"), self.toggle_play)
        self.play.setMinimumWidth(100)
        playback.addWidget(self.play)
        self.time_label = QLabel()
        self.time_label.setObjectName("timeCode")
        self.time_label.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
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
        video_layout.addWidget(self.panel_title(self.t("Línea de tiempo", "Timeline")))
        video_layout.addWidget(self.inset(self.timeline, "track"))
        hint = self.t(
            "Arrastra sobre la pista de subtítulos para seleccionar varios fragmentos.",
            "Drag across the caption track to select several captions.",
        )
        timeline_hint = QLabel(hint)
        timeline_hint.setObjectName("selectionHint")
        timeline_hint.setWordWrap(True)
        self.timeline.setAccessibleDescription(hint)
        video_layout.addWidget(timeline_hint)
        split.addWidget(video)

        side = QWidget()
        side.setObjectName("workPanel")
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(7, 7, 7, 7)
        side_layout.setSpacing(5)
        self.caption_title = self.panel_title(self.t("Fragmentos", "Captions"))
        side_layout.addWidget(self.caption_title)
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.itemSelectionChanged.connect(self.select_cue)
        side_layout.addWidget(self.list, 1)
        buttons = QHBoxLayout()
        buttons.addWidget(self._button(self.t("Añadir", "Add"), self.add_cue))
        self.split_button = self._button(self.t("Dividir", "Split"), self.split_cue)
        self.join_button = self._button(self.t("Unir", "Join"), self.join_cue)
        self.duplicate_button = self._button(self.t("Duplicar", "Duplicate"), self.duplicate_cue)
        for button in (self.split_button, self.join_button, self.duplicate_button):
            buttons.addWidget(button)
        self.delete_button = self._button(self.t("Borrar", "Delete"), self.remove_cue)
        buttons.addWidget(self.delete_button)
        side_layout.addLayout(buttons)
        fields = QWidget()
        fields.setObjectName("inspector")
        form = QFormLayout(fields)
        self.property_checks = {}
        self.batch_help = QLabel(
            self.t(
                "Marca los campos que quieres aplicar. Se muestran los valores del primero.",
                "Mark the properties to apply. Fields show the first caption.",
            )
        )
        self.batch_help.setWordWrap(True)
        form.addRow(self.batch_help)
        self.text = QLineEdit()
        self.inspector_row(form, self.t("Texto", "Text"), "text")
        self.start = QDoubleSpinBox()
        self.end = QDoubleSpinBox()
        for spin in (self.start, self.end):
            spin.setRange(0, 300)
            spin.setDecimals(3)
            spin.setSingleStep(0.05)
            spin.setSuffix(" s")
        self.times_label = self.inspector_row(
            form, self.t("Inicio / fin", "Start / end"), "start", "end"
        )
        self.speaker = QLineEdit()
        self.inspector_row(form, self.t("Hablante", "Speaker"), "speaker")
        self.font = QFontComboBox()
        self.font.setMinimumWidth(100)
        self.size = QSpinBox()
        self.size.setRange(12, 200)
        self.inspector_row(form, self.t("Fuente / tamaño", "Font / size"), "font", "size")
        self.x = QDoubleSpinBox()
        self.y = QDoubleSpinBox()
        self.opacity = QDoubleSpinBox()
        for spin in (self.x, self.y, self.opacity):
            spin.setRange(0, 1)
            spin.setSingleStep(0.01)
            spin.setDecimals(3)
        self.inspector_row(form, self.t("Posición X / Y", "Position X / Y"), "x", "y")
        self.color = QLineEdit()
        self.background = QLineEdit()
        self.outline = QLineEdit()
        self.highlight = QLineEdit()
        self.inspector_row(
            form, self.t("Color / fondo", "Text color / fill"), "color", "background"
        )
        self.inspector_row(
            form, self.t("Contorno / resaltado", "Outline / highlight"), "outline", "highlight"
        )
        self.inspector_row(form, self.t("Opacidad de fondo", "Fill opacity"), "opacity")
        self.bold = QCheckBox(self.t("Negrita", "Bold"))
        self.shadow = QCheckBox(self.t("Sombra", "Shadow"))
        self.inspector_row(form, self.t("Grosor / sombra", "Weight / shadow"), "bold", "shadow")
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
        self.inspector_row(form, self.t("Alineación / efecto", "Align / effect"), "align", "effect")
        self.apply_button = self._button(self.t("Aplicar", "Apply"), self.apply_fields)
        self.word_button = self._button(
            self.t("Tiempos de palabras…", "Word times…"), self.edit_word
        )
        self.inspector = QScrollArea()
        self.inspector.setWidgetResizable(True)
        self.inspector.setWidget(fields)
        self.property_title = self.panel_title(
            self.t("Propiedades del fragmento", "Caption properties")
        )
        side_layout.addWidget(self.property_title)
        side_layout.addWidget(self.inspector, 2)
        side_layout.addLayout(self._fields(self.apply_button, self.word_button))
        split.addWidget(side)
        split.setSizes([720, 475])
        self.statusBar().showMessage(self.t("Creado por sudo_pita", "Created by sudo_pita"))

    @staticmethod
    def panel_title(text):
        label = QLabel(text)
        label.setObjectName("panelTitle")
        return label

    @staticmethod
    def inset(widget, name):
        frame = QFrame()
        frame.setObjectName(name)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.addWidget(widget)
        return frame

    def _fields(self, *widgets):
        row = QHBoxLayout()
        for widget in widgets:
            row.addWidget(widget)
        return row

    def inspector_row(self, form, title, *names):
        row = QHBoxLayout()
        for name, label in zip(names, title.split(" / "), strict=True):
            control = getattr(self, name)
            check = QCheckBox()
            check.setAccessibleName(self.t(f"Aplicar {label}", f"Apply {label}"))
            self.property_checks[name] = check
            row.addWidget(check)
            row.addWidget(control, 1)
            if isinstance(control, QFontComboBox):
                changed = control.currentFontChanged
            elif isinstance(control, QComboBox):
                changed = control.currentIndexChanged
            elif isinstance(control, QLineEdit):
                changed = control.textChanged
            elif isinstance(control, QCheckBox):
                changed = control.toggled
            else:
                changed = control.valueChanged
            changed.connect(lambda *_, toggle=check: toggle.setChecked(True))
        label = QLabel(title)
        form.addRow(label, row)
        return label

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
        if self.project and self.project.source != project.source:
            self.context_hint = ""
            self.update_hints_button()
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
            self.use_model(Path(path))
            self.statusBar().showMessage(path)

    def install_model(self, preset: ModelPreset = SMALL_MODEL):
        if self.job is not None:
            return
        destination = self.model_storage / preset.directory
        local_candidates = (destination, self.model_path.parent / preset.directory)
        for candidate in local_candidates:
            if model_ready(candidate):
                self.use_model(candidate)
                return
        answer = QMessageBox.question(
            self,
            "Pitranscriptor",
            self.t(
                f"¿Descargar el modelo multilingüe {preset.name} (aprox. {preset.size_mb} MB)?",
                f"Download the multilingual {preset.name} model (about {preset.size_mb} MB)?",
            ),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.start_job(
            lambda progress, cancelled: download_model(preset, destination),
            self.use_model,
            can_cancel=False,
        )
        self.progress.setRange(0, 0)

    def use_model(self, path):
        self.model_path = path
        self.settings.setValue("model", str(path))
        self.model_button.setToolTip(str(path))
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
            self.t("Vocabulario técnico…", "Technical vocabulary…"),
            self.t("Términos de un guion…", "Terms from a script…"),
            self.t("Contexto breve…", "Short context…"),
            self.t("Cargar archivo de texto", "Load a text file"),
        ]
        choice, ok = QInputDialog.getItem(
            self, "Pitranscriptor", self.t("Pistas del modelo", "Model hints"), options, 1, False
        )
        if not ok:
            return
        if choice == options[0]:
            self.set_hints()
        elif choice == options[1]:
            self.pick_vocabulary()
        elif choice == options[2]:
            script, accepted = QInputDialog.getMultiLineText(
                self, options[2], self.t("Pega el guion de este video", "Paste this video's script")
            )
            if accepted and script.strip():
                suggested = suggest_script_terms(script)
                if not suggested:
                    self.statusBar().showMessage(
                        self.t(
                            "No encontré términos del catálogo en el guion.",
                            "No catalog terms found in the script.",
                        )
                    )
                self.pick_vocabulary(suggested=suggested)
        elif choice == options[3]:
            context, accepted = QInputDialog.getMultiLineText(
                self,
                options[3],
                self.t(
                    "Escribe unas frases con el tema y las palabras difíciles del audio.",
                    "Enter a few phrases with the topic and difficult words in the audio.",
                ),
                self.context_hint,
            )
            if accepted:
                self.context_hint = context.strip()
                self.update_hints_button()
        else:
            path, _ = QFileDialog.getOpenFileName(self, options[4], "", "Text (*.txt *.md)")
            if path:
                try:
                    self.set_hints(prompt=Path(path).read_text(encoding="utf-8-sig"))
                except (OSError, ValueError) as error:
                    self.show_error(error)

    def pick_vocabulary(self, *, suggested=()):
        dialog = VocabularyPicker(self, self.t, self.technical_terms, suggested=suggested)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.set_hints(terms=dialog.selected_terms())

    def set_hints(self, *, terms=(), prompt=None):
        self.technical_terms = terms
        self.prompt = prompt
        self.context_hint = ""
        self.settings.setValue("technicalTerms", list(terms))
        self.update_hints_button()

    def update_hints_button(self):
        if self.context_hint:
            self.hints_button.setText(self.t("Contexto…", "Context…"))
            self.hints_button.setToolTip(self.context_hint)
            return
        count = len(self.technical_terms)
        self.hints_button.setText(
            self.t(f"Pistas ({count})…", f"Hints ({count})…")
            if count
            else self.t("Pistas…", "Hints…")
        )
        self.hints_button.setToolTip(
            ", ".join(self.technical_terms)
            or (self.t("Pistas de archivo", "Hints from file") if self.prompt else "")
        )

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
        rigor = self.rigor.currentData()
        context = self.context_hint or None
        prompt = None if context else self.prompt
        terms = () if context else self.technical_terms
        self.start_job(
            lambda progress, cancelled: run_transcription(
                path,
                model,
                language=language,
                target=target,
                device=device,
                rigor=rigor,
                vocabulary=prompt,
                technical_terms=terms,
                context_hint=context,
                progress=progress,
                cancelled=cancelled,
            ),
            lambda project: self.commit(project, 0),
        )
        self.progress.setRange(0, 0)
        self.statusBar().showMessage(
            self.t("Preparando la transcripción…", "Preparing transcription…")
        )

    def start_job(self, operation, callback, *, waveform=False, can_cancel=True):
        self.job = Job(operation, self)
        self.job_callback = callback
        self.job_waveform = waveform
        self.job.progress.connect(self.update_progress)
        self.job.finished.connect(self.finish_job)
        self.transcribe_button.setEnabled(False)
        self.cancel_button.setEnabled(not waveform and can_cancel)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(not waveform)
        self.job.start()

    def update_progress(self, percent):
        if percent < 0:
            self.progress.setRange(0, 0)
        else:
            if self.progress.maximum() == 0:
                self.statusBar().showMessage(self.t("Transcribiendo…", "Transcribing…"))
            self.progress.setRange(0, 100)
            self.progress.setValue(percent)

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
            if self.statusBar().currentMessage() in (
                self.t("Preparando la transcripción…", "Preparing transcription…"),
                self.t("Transcribiendo…", "Transcribing…"),
            ):
                self.statusBar().showMessage(self.t("Transcripción lista.", "Transcription ready."))
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
        self.set_caption_selection((), False)
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
        rows = self.selected_rows()
        if self.project and rows:
            return self.project.cues[rows[0]]
        return None

    def selected_rows(self):
        return tuple(sorted(index.row() for index in self.list.selectedIndexes()))

    def set_caption_selection(self, rows, seek):
        rows = tuple(row for row in rows if 0 <= row < self.list.count())
        selection = QItemSelection()
        model = self.list.model()
        for row in rows:
            index = model.index(row, 0)
            selection.select(index, index)
        flags = QItemSelectionModel.SelectionFlag
        selection_model = self.list.selectionModel()
        previous = self.list.blockSignals(True)
        selection_model.select(selection, flags.ClearAndSelect)
        selection_model.setCurrentIndex(model.index(rows[0] if rows else -1, 0), flags.NoUpdate)
        self.list.blockSignals(previous)
        if rows:
            self.list.scrollToItem(self.list.item(rows[0]))
        self.select_cue(seek=seek)

    def refresh(self, index=None, *, rows=None):
        if rows is None:
            rows = self.selected_rows()
        self.list.blockSignals(True)
        self.list.clear()
        self.timeline.cues = self.project.cues if self.project else ()
        self.timeline.duration = self.project.duration_ms if self.project else 1
        for cue in self.timeline.cues:
            speaker = f" [{cue.speaker}]" if cue.speaker else ""
            self.list.addItem(f"{timestamp(cue.start_ms)}{speaker}   {cue.text}")
        self.list.blockSignals(False)
        if index is not None:
            rows = (min(index, self.list.count() - 1),)
        self.set_caption_selection(rows, False)
        label = f" · {Path(self.project.source).name}" if self.project else ""
        self.media_name.setText(
            Path(self.project.source).name if self.project else self.t("Sin video", "No video")
        )
        self.preview.empty_text = (
            "" if self.project else self.t("Abre un video para comenzar", "Open a video to begin")
        )
        self.setWindowTitle(
            "Pitranscriptor" + label + (" *" if self.project != self.saved_project else "")
        )
        self.transcribe_button.setEnabled(self.project is not None and self.job is None)

    def select_cue(self, *, seek=True):
        rows = self.selected_rows()
        count = len(rows)
        self.timeline.selection = frozenset(rows)
        self.caption_title.setText(
            self.t(f"Fragmentos ({count} seleccionados)", f"Captions ({count} selected)")
            if count > 1
            else self.t("Fragmentos", "Captions")
        )
        self.inspector.setEnabled(count > 0)
        self.split_button.setEnabled(count > 0)
        self.join_button.setEnabled(count > 0)
        self.duplicate_button.setEnabled(count > 0)
        self.delete_button.setEnabled(count > 0)
        cue = self.current_cue()
        if count == 1 and self.list.currentRow() != rows[0]:
            index = self.list.model().index(rows[0], 0)
            self.list.selectionModel().setCurrentIndex(
                index, QItemSelectionModel.SelectionFlag.NoUpdate
            )
        self.load_inspector(cue, rows)
        if seek and cue:
            self.player.pause()
            self.player.setPosition(cue.start_ms)
        self.update_playhead(self.player.position())

    def load_inspector(self, cue, rows):
        multiple = len(rows) > 1
        self.batch_help.setVisible(multiple)
        self.property_title.setText(
            self.t("Propiedades de la selección", "Selection properties")
            if multiple
            else self.t("Propiedades del fragmento", "Caption properties")
        )
        self.apply_button.setEnabled(bool(rows))
        self.times_label.setText(
            self.t("Ajuste inicio / fin", "Shift start / end")
            if multiple
            else self.t("Inicio / fin", "Start / end")
        )
        selected = tuple(self.project.cues[row] for row in rows)
        for name, check in self.property_checks.items():
            check.setChecked(False)
            check.setVisible(multiple)
            mixed = multiple and len({self.inspector_value(cue, name) for cue in selected}) > 1
            check.setToolTip(
                self.t("Valores distintos en la selección", "Values differ across selection")
                if mixed
                else check.accessibleName()
            )
        self.word_button.setEnabled(bool(selected) and all(item.words for item in selected))
        self.apply_button.setText(
            self.t("Aplicar a selección", "Apply to selection")
            if multiple
            else self.t("Aplicar", "Apply")
        )
        with ExitStack() as blocked:
            for name in self.property_checks:
                blocked.enter_context(QSignalBlocker(getattr(self, name)))
            for spin in (self.start, self.end):
                spin.setMinimum(-300 if multiple else 0)
            self.text.setText(cue.text if cue else "")
            self.speaker.setText(cue.speaker if cue else "")
            self.start.setValue(cue.start_ms / 1000 if cue and not multiple else 0)
            self.end.setValue(cue.end_ms / 1000 if cue and not multiple else 0)
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

    @staticmethod
    def inspector_value(cue, name):
        if name in ("start", "end"):
            return getattr(cue, f"{name}_ms")
        if name in ("text", "speaker"):
            return getattr(cue, name)
        return getattr(cue.style, name)

    def commit(self, project, index=None, *, rows=None):
        if project == self.project:
            return
        self.before.append(self.project)
        self.after.clear()
        self.project = project
        self.refresh(index, rows=rows)

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

    def commit_batch(self, replacements, selection):
        cues = (
            cue
            for index, original in enumerate(self.project.cues)
            for cue in replacements.get(index, (original,))
        )
        project = self.project.with_cues(cues)
        starts = {cue.start_ms for cue in selection}
        rows = tuple(i for i, cue in enumerate(project.cues) if cue.start_ms in starts)
        self.commit(project, rows=rows)

    def edit_selected(self, edit):
        rows = self.selected_rows()
        if not rows or self.job is not None:
            return
        try:
            updates = {row: (edit(self.project.cues[row]),) for row in rows}
            self.commit_batch(updates, (update[0] for update in updates.values()))
        except ValueError as error:
            self.show_error(error)

    def apply_fields(self):
        cue = self.current_cue()
        if cue is None:
            return
        font = self.font.currentFont().family()
        if font == QApplication.font().family() and not cue.style.font:
            font = ""
        styles = dict(
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
        multiple = len(self.selected_rows()) > 1
        marked = {name for name, check in self.property_checks.items() if check.isChecked()}
        if multiple:
            styles = {name: value for name, value in styles.items() if name in marked}
        start = round(self.start.value() * 1000)
        end = round(self.end.value() * 1000)
        text = self.text.text()
        speaker = self.speaker.text()

        def edit(original):
            if multiple:
                if marked & {"start", "end"}:
                    original = retime_cue(
                        original,
                        original.start_ms + (start if "start" in marked else 0),
                        original.end_ms + (end if "end" in marked else 0),
                    )
                changed = (
                    edit_cue(original, text, original.start_ms, original.end_ms)
                    if "text" in marked
                    else original
                )
            else:
                changed = edit_cue(original, text, start, end)
            return replace(
                changed,
                style=replace(changed.style, **styles),
                speaker=speaker if not multiple or "speaker" in marked else changed.speaker,
            )

        self.edit_selected(edit)

    def move_caption(self, x, y):
        self.edit_selected(
            lambda cue: replace(cue, style=replace(cue.style, x=round(x, 3), y=round(y, 3)))
        )

    def edit_word(self):
        rows = self.selected_rows()
        if not rows or self.job is not None:
            return
        cues = tuple(self.project.cues[row] for row in rows)
        count = min(len(cue.words) for cue in cues)
        if count == 0:
            self.statusBar().showMessage(
                self.t(
                    "La edición requiere marcas por palabra en cada fragmento seleccionado.",
                    "Word times are required on every selected caption.",
                )
            )
            return
        multiple = len(rows) > 1
        choices = [
            str(index + 1) if multiple else f"{index + 1} · {cues[0].words[index].text}"
            for index in range(count)
        ]
        chosen, ok = QInputDialog.getItem(
            self,
            "Pitranscriptor",
            self.t("Número de palabra en cada fragmento", "Word number in each caption")
            if multiple
            else self.t("Palabra", "Word"),
            choices,
            0,
            False,
        )
        if not ok:
            return
        index = choices.index(chosen)
        word = cues[0].words[index]
        value, ok = QInputDialog.getText(
            self,
            "Pitranscriptor",
            self.t(
                "Ajustes de inicio y fin en ms, separados por coma",
                "Start and end shifts in ms, separated by a comma",
            )
            if multiple
            else self.t(
                "Inicio y fin en ms, separados por coma",
                "Start and end in ms, separated by a comma",
            ),
            text="0, 0" if multiple else f"{word.start_ms}, {word.end_ms}",
        )
        if not ok:
            return
        try:
            start, end = (int(part.strip()) for part in value.split(","))
        except ValueError:
            self.show_error(
                self.t(
                    "Escribe dos enteros separados por coma.",
                    "Enter two integers separated by a comma.",
                )
            )
            return

        def edit(cue):
            words = list(cue.words)
            original = words[index]
            words[index] = replace(
                original,
                start_ms=start + (original.start_ms if multiple else 0),
                end_ms=end + (original.end_ms if multiple else 0),
            )
            return replace(cue, words=tuple(words))

        self.edit_selected(edit)

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
        rows = self.selected_rows()
        if not rows or self.job is not None:
            return
        cues = tuple(self.project.cues[row] for row in rows)
        shortest = min(len(cue.text.split()) for cue in cues)
        if shortest < 2:
            self.show_error(
                self.t(
                    "Cada fragmento seleccionado necesita al menos dos palabras para dividirlo.",
                    "Each selected caption needs at least two words to split it.",
                )
            )
            return
        number, ok = QInputDialog.getInt(
            self,
            "Pitranscriptor",
            self.t("Dividir después de la palabra indicada", "Split after this word number"),
            shortest // 2,
            1,
            shortest - 1,
        )
        if not ok:
            return
        try:
            replacements = {}
            for row, cue in zip(rows, cues, strict=True):
                tokens = cue.text.split()
                boundary = (
                    cue.words[number].start_ms if cue.words else (cue.start_ms + cue.end_ms) // 2
                )
                left = replace(
                    cue, end_ms=boundary, text=" ".join(tokens[:number]), words=cue.words[:number]
                )
                right = replace(
                    cue, start_ms=boundary, text=" ".join(tokens[number:]), words=cue.words[number:]
                )
                replacements[row] = (left, right)
            selected = (
                piece
                for pair in replacements.values()
                for piece in (pair if len(rows) > 1 else pair[:1])
            )
            self.commit_batch(replacements, selected)
        except ValueError as error:
            self.show_error(error)

    def join_cue(self):
        rows = self.selected_rows()
        if not rows or self.job is not None:
            return
        first = rows[0]
        last = rows[-1] if len(rows) > 1 else first + 1
        if last >= len(self.project.cues):
            return
        if len(rows) > 1 and len(rows) != last - first + 1:
            self.show_error(
                self.t(
                    "Selecciona fragmentos consecutivos para unirlos.",
                    "Select consecutive captions to join them.",
                )
            )
            return
        cues = self.project.cues[first : last + 1]
        try:
            merged = replace(
                cues[0],
                end_ms=cues[-1].end_ms,
                text=" ".join(cue.text for cue in cues),
                words=tuple(word for cue in cues for word in cue.words)
                if all(cue.words for cue in cues)
                else (),
            )
            self.splice(first, len(cues), [merged])
        except ValueError as error:
            self.show_error(error)

    def duplicate_cue(self):
        rows = self.selected_rows()
        if not rows or self.job is not None:
            return
        cues = self.project.cues
        replacements = {}
        try:
            for row in rows:
                cue = cues[row]
                limit = cues[row + 1].start_ms if row + 1 < len(cues) else self.project.duration_ms
                end = cue.end_ms + (cue.end_ms - cue.start_ms)
                if end > limit:
                    raise ValueError(
                        self.t(
                            f"No hay espacio para una copia después del fragmento {row + 1}.",
                            f"There is no room for a copy after caption {row + 1}.",
                        )
                    )
                replacements[row] = (cue, retime_cue(cue, cue.end_ms, end))
            self.commit_batch(replacements, (copy for _, copy in replacements.values()))
        except ValueError as error:
            self.show_error(error)

    def remove_cue(self):
        if self.project is None or self.job is not None:
            return
        rows = self.timeline.selection
        if rows:
            cues = tuple(cue for index, cue in enumerate(self.project.cues) if index not in rows)
            self.commit(self.project.with_cues(cues), min(rows))

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
        presets = json.loads(self.settings.value("presets", "{}"))
        if self.selected_rows() and presets and self.job is None:
            name, ok = QInputDialog.getItem(
                self, "Pitranscriptor", "Preset", sorted(presets), 0, False
            )
            if ok:
                self.edit_selected(lambda cue: replace(cue, style=Style(**presets[name])))

    def review_fillers(self):
        if self.project is None or self.job is not None:
            return
        options = {}
        for index, cue in enumerate(self.project.cues):
            for token in cue.text.split():
                plain = "".join(char for char in token.casefold() if char.isalpha())
                if plain in FILLERS:
                    options[f"{index + 1}. {timestamp(cue.start_ms)} · {token} · {cue.text}"] = (
                        index
                    )
        if not options:
            self.statusBar().showMessage(
                self.t("Sin posibles muletillas en la lista.", "No likely fillers found.")
            )
            return
        selection, ok = QInputDialog.getItem(
            self,
            "Pitranscriptor",
            self.t(
                "Posibles muletillas. Elige un fragmento para revisarlo.",
                "Possible fillers. Select a caption to review.",
            ),
            list(options),
            0,
            False,
        )
        if ok:
            self.list.setCurrentRow(options[selection])
            self.text.setFocus()

    def color_speakers(self):
        if self.project is None or self.job is not None:
            return
        speakers = list(dict.fromkeys(cue.speaker for cue in self.project.cues if cue.speaker))
        if not speakers:
            self.statusBar().showMessage(
                self.t(
                    "Asigna hablantes a los fragmentos primero.",
                    "Assign speakers to captions first.",
                )
            )
            return
        if (
            QMessageBox.question(
                self,
                "Pitranscriptor",
                self.t(
                    "¿Actualizar el color de texto de todos los fragmentos con hablante?",
                    "Update text color for all captions with a speaker?",
                ),
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        colors = {
            speaker: SPEAKER_COLORS[index % len(SPEAKER_COLORS)]
            for index, speaker in enumerate(speakers)
        }
        cues = tuple(
            replace(cue, style=replace(cue.style, color=colors[cue.speaker]))
            if cue.speaker
            else cue
            for cue in self.project.cues
        )
        self.commit(self.project.with_cues(cues), self.list.currentRow())

    def review_uncertain(self):
        if self.project is None or self.job is not None:
            return
        options = {
            f"{index + 1}.{word_index + 1} · {timestamp(word.start_ms)} · "
            f"{word.text} · {word.probability:.0%}": (index, word.start_ms)
            for index, cue in enumerate(self.project.cues)
            for word_index, word in enumerate(cue.words)
            if word.probability is not None and word.probability < 0.5
        }
        if not options:
            self.statusBar().showMessage(
                self.t("Sin palabras marcadas como dudosas.", "No words flagged as uncertain.")
            )
            return
        selected, ok = QInputDialog.getItem(
            self,
            "Pitranscriptor",
            self.t(
                "Palabras con confianza del modelo inferior al 50 %",
                "Words with model confidence below 50%",
            ),
            list(options),
            0,
            False,
        )
        if ok:
            index, position = options[selected]
            self.player.pause()
            self.list.setCurrentRow(index)
            self.player.setPosition(position)
            self.text.setFocus()


def configure_application(app):
    app.setStyle("Windows")
    if os.name == "nt" and app.platformName() == "offscreen":
        fonts = Path(os.environ["SystemRoot"]) / "Fonts"
        for filename in ("segoeui.ttf", "segoeuib.ttf"):
            QFontDatabase.addApplicationFont(str(fonts / filename))
        app.setFont(QFont("Segoe UI", 9))
    font = app.font()
    if 0 < font.pointSizeF() < 10:
        font.setPointSize(10)
        app.setFont(font)
    app.setPalette(retro_palette())
    app.setStyleSheet(STYLESHEET)


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) == 2 and arguments[0] == WORKER_FLAG:
        return worker(Path(arguments[1]))
    parser = argparse.ArgumentParser(prog="pitranscriptor-desktop")
    parser.add_argument("project", type=Path, nargs="?")
    parser.add_argument("--language", choices=("es", "en"))
    parser.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(arguments)
    if args.self_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication([sys.argv[0]])
    app.setOrganizationName("sudo_pita")
    app.setApplicationName("Pitranscriptor")
    configure_application(app)
    settings = QSettings("sudo_pita", "Pitranscriptor")
    editor = Editor(args.language or settings.value("language", "es"))
    if args.self_test:
        import av
        import ctranslate2
        import faster_whisper.audio

        from pitranscriptor.vocabulary import technical_groups

        if not technical_groups():
            return 1
        if not ctranslate2.get_supported_compute_types("cpu"):
            return 1
        av.Codec("libx264", "w")
        av.Codec("aac", "w")
        clip = io.BytesIO()
        with wave.open(clip, "wb") as audio:
            audio.setparams((1, 2, 16_000, 0, "NONE", "not compressed"))
            audio.writeframes(bytes(3200))
        clip.seek(0)
        decoded = faster_whisper.audio.decode_audio(clip)
        return 0 if not editor.grab().isNull() and len(decoded) == 1600 else 1
    editor.show()
    if args.project:
        editor.load_path(args.project)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
