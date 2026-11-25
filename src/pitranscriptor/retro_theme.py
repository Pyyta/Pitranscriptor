"""Estilo de los editores de escritorio de los noventa."""

WORKSPACE = "#101d1c"
GRID = "#243b36"
TRACE = "#86ba98"
TIMECODE = "#c3ddc9"
PLAYHEAD = "#f3c879"

STYLESHEET = """
QMainWindow, QDialog, QWidget#desk, QWidget#inspector { background: #c9c6b9; }
QWidget#commandTray, QWidget#workPanel {
    background: #d4d0c4;
    border: 1px solid;
    border-color: #faf8ee #66655c #66655c #faf8ee;
}
QMenuBar { background: #e1ddcf; border-bottom: 1px solid #78756c; padding: 3px 5px; }
QMenuBar::item { padding: 4px 10px; }
QMenuBar::item:selected, QMenu::item:selected { background: #253e68; color: #fffaf0; }
QMenu { background: #e7e2d5; padding: 3px; border: 1px solid #66655c; }
QLabel#panelTitle, QLabel#brand {
    background: #253e68;
    color: #fffaf0;
    border: 1px solid #152947;
    font-weight: bold;
    padding: 4px 8px;
}
QLabel#brand {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #20365e,stop:1 #405c83);
    font-size: 18px;
    padding: 7px 10px;
}
QLabel#mediaName { background: #e7e3d7; color: #28332f; padding: 3px 7px; }
QPushButton {
    background: #e6e2d5;
    border: 2px solid;
    border-color: #fffdf3 #69665d #69665d #fffdf3;
    padding: 4px 9px;
}
QPushButton:hover { background: #f3efe2; }
QPushButton:pressed { background: #c9c5b8; border-color: #69665d #fdf9ed #fdf9ed #69665d; }
QPushButton:disabled { color: #656259; background: #d1cdbf; }
QPushButton#primary:enabled {
    background: #264970; color: #ffffff;
    border-color: #7497b8 #132840 #132840 #7497b8;
    font-weight: bold;
}
QPushButton#primary:hover { background: #345a85; }
QPushButton#primary:pressed { background: #1f3856; border-color: #132840 #7497b8 #7497b8 #132840; }
QLineEdit, QListWidget, QScrollArea, QDoubleSpinBox, QSpinBox,
QComboBox, QFrame#monitor, QFrame#track {
    border: 1px solid;
    border-color: #737067 #fffdf3 #fffdf3 #737067;
    background: #f7f4e8;
    selection-background-color: #253e68;
    selection-color: #ffffff;
}
QFrame#monitor, QFrame#track { background: #101d1c; border-width: 2px; }
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox { min-height: 21px; padding: 1px 5px; }
QListWidget::item { padding: 4px 6px; border-bottom: 1px solid #e3dfd1; }
QListWidget::item:selected { background: #253e68; color: #fff; }
QLabel#timeCode, QProgressBar {
    background: #101d1c;
    color: #c3ddc9;
    border: 1px solid #555e53;
    padding: 3px 7px;
}
QProgressBar { padding: 0; min-height: 18px; text-align: center; }
QProgressBar::chunk { background: #527865; }
QSplitter::handle { background: #b6b1a4; width: 6px; }
QStatusBar { background: #ddd8ca; border-top: 1px solid #817e74; color: #222b25; }
QToolTip { background: #fff4ce; border: 1px solid #645e48; color: #172635; }
"""
