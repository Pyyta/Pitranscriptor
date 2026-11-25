"""Estilo de los editores de escritorio de los noventa."""

from PySide6.QtGui import QColor, QPalette

INK = "#131c29"
PAPER = "#fffdf5"
DESK = "#ede8d8"
NAVY = "#183358"
WHITE = "#ffffff"
DISABLED_INK = "#3f3c46"
DISABLED_PAPER = "#e0d9c7"
WORKSPACE = "#111c26"
GRID = "#365365"
TRACE = "#87dfc0"
TIMECODE = "#f2fff8"
PLAYHEAD = "#ffe18e"
CLIP = "#c0d9ed"


def retro_palette() -> QPalette:
    palette = QPalette()
    roles = QPalette.ColorRole
    groups = QPalette.ColorGroup
    for role, color in {
        roles.Window: DESK,
        roles.WindowText: INK,
        roles.Base: PAPER,
        roles.AlternateBase: DESK,
        roles.Text: INK,
        roles.Button: DESK,
        roles.ButtonText: INK,
        roles.Highlight: NAVY,
        roles.HighlightedText: WHITE,
        roles.ToolTipBase: PAPER,
        roles.ToolTipText: INK,
        roles.PlaceholderText: DISABLED_INK,
        roles.BrightText: WHITE,
        roles.Link: "#194687",
        roles.LinkVisited: "#633877",
        roles.Light: WHITE,
        roles.Midlight: "#f4eedf",
        roles.Mid: "#8b8475",
        roles.Dark: "#53515a",
        roles.Shadow: INK,
    }.items():
        palette.setColor(role, QColor(color))
    for role in (roles.WindowText, roles.Text, roles.ButtonText):
        palette.setColor(groups.Disabled, role, QColor(DISABLED_INK))
    for role in (roles.Base, roles.Button):
        palette.setColor(groups.Disabled, role, QColor(DISABLED_PAPER))
    return palette


# Usar colores explícitos también donde Qt pinta por encima de la paleta.
STYLESHEET = """
QMainWindow, QDialog, QWidget#desk, QWidget#inspector { background: $desk; color: $ink; }
QWidget#commandTray, QWidget#workPanel {
    background: $desk;
    border: 1px solid;
    border-color: #ffffff #686052 #686052 #ffffff;
}
QLabel, QCheckBox, QMenu, QMenuBar, QStatusBar { color: $ink; }
QMenuBar { background: $paper; border-bottom: 1px solid #686052; padding: 3px 5px; }
QMenuBar::item { padding: 4px 10px; }
QMenuBar::item:selected, QMenu::item:selected { background: $navy; color: #ffffff; }
QMenu { background: $paper; padding: 3px; border: 1px solid #686052; }
QLabel#panelTitle, QLabel#brand {
    background: $navy;
    color: #ffffff;
    border: 1px solid #101e35;
    font-weight: bold;
    padding: 4px 8px;
}
QLabel#brand {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #132747,stop:1 #294f7b);
    font-size: 18px;
    padding: 7px 10px;
}
QLabel#mediaName { background: $paper; color: $ink; padding: 3px 7px; }
QLabel#selectionHint { color: $ink; padding: 0 2px 2px; }
QPushButton {
    background: $paper;
    color: $ink;
    border: 2px solid;
    border-color: #fffdf3 #69665d #69665d #fffdf3;
    padding: 4px 9px;
}
QPushButton:hover { background: #e1eefa; }
QPushButton:pressed { background: #cfdfef; border-color: #69665d #fdf9ed #fdf9ed #69665d; }
QPushButton:disabled { color: $disabledInk; background: $disabledPaper; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QListWidget:focus { border-color: #235693; }
QPushButton#primary:enabled {
    background: $navy; color: #ffffff;
    border-color: #7497b8 #132840 #132840 #7497b8;
    font-weight: bold;
}
QPushButton#primary:hover { background: #345a85; }
QPushButton#primary:pressed { background: #1f3856; border-color: #132840 #7497b8 #7497b8 #132840; }
QLineEdit, QListWidget, QScrollArea, QDoubleSpinBox, QSpinBox,
QComboBox, QFrame#monitor, QFrame#track {
    border: 1px solid;
    border-color: #737067 #fffdf3 #fffdf3 #737067;
    color: $ink;
    background: $paper;
    selection-background-color: $navy;
    selection-color: #ffffff;
}
QFrame#monitor, QFrame#track { background: $workspace; border-width: 2px; }
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox { min-height: 21px; padding: 1px 5px; }
QComboBox QAbstractItemView {
    background: $paper; color: $ink; selection-background-color: $navy; selection-color: #fff;
}
QLineEdit:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled, QComboBox:disabled {
    color: $disabledInk; background: $disabledPaper;
}
QListWidget::item { padding: 4px 6px; border-bottom: 1px solid #d3ccba; }
QListWidget::item:selected { background: $navy; color: #ffffff; }
QLabel#timeCode, QProgressBar {
    background: $workspace;
    color: $timecode;
    border: 1px solid #555e53;
    padding: 3px 7px;
}
QProgressBar { padding: 0; min-height: 18px; text-align: center; }
QProgressBar::chunk { background: #285765; }
QSplitter::handle { background: #b6b1a4; width: 6px; }
QStatusBar { background: $paper; border-top: 1px solid #686052; color: $ink; }
QToolTip { background: #fff4ce; border: 1px solid #645e48; color: $ink; }
"""

for name, value in {
    "ink": INK,
    "paper": PAPER,
    "desk": DESK,
    "navy": NAVY,
    "disabledInk": DISABLED_INK,
    "disabledPaper": DISABLED_PAPER,
    "workspace": WORKSPACE,
    "timecode": TIMECODE,
}.items():
    STYLESHEET = STYLESHEET.replace(f"${name}", value)
