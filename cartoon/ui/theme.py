"""Colours, stylesheet (dark + light) and vector icons."""
from __future__ import annotations

from string import Template

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

PURPLE, VIOLET, BLUE, CYAN, PINK = "#5425D6", "#8B5CF6", "#3B82F6", "#22D3EE", "#EC4899"

PALETTES = {
    "dark": dict(bg="#10111B", card="#1C1D2B", text="#FFFFFF", muted="#A3A6BF", border="#2C2E45",
                 input="#14151F", hover="#252740", soft="rgba(139,92,246,0.24)"),
    "light": dict(bg="#F3F4FB", card="#FFFFFF", text="#161828", muted="#5B5E7A", border="#DFE1F0",
                  input="#F1F2F9", hover="#EAEBF7", soft="rgba(139,92,246,0.14)"),
}

ICONS = {
    "home": "M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z M9 22V12h6v10",
    "studio": "M23 7l-7 5 7 5z M3 5h11a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z",
    "styles": "M12 2 2 7l10 5 10-5z M2 17l10 5 10-5 M2 12l10 5 10-5",
    "editor": "M6 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M20 4 8.12 15.88 M14.47 14.48 20 20 M8.12 8.12 12 12",
    "creations": "M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z",
    "settings": "M4 21v-7 M4 10V3 M12 21v-9 M12 8V3 M20 21v-5 M20 12V3 M1 14h6 M9 8h6 M17 16h6",
    "about": "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z M12 16v-4 M12 8h.01",
    "user": "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2 M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
    "upload": "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4 M17 8l-5-5-5 5 M12 3v12",
    "record": "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
    "heart": "M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z",
    "play": "M5 3l14 9-14 9z",
    "pause": "M6 4h4v16H6z M14 4h4v16h-4z",
    "full": "M8 3H5a2 2 0 0 0-2 2v3 M21 8V5a2 2 0 0 0-2-2h-3 M3 16v3a2 2 0 0 0 2 2h3 M16 21h3a2 2 0 0 0 2-2v-3",
    "sun": "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z M12 1v2 M12 21v2 M4.22 4.22l1.42 1.42 M18.36 18.36l1.42 1.42 M1 12h2 M21 12h2 M4.22 19.78l1.42-1.42 M18.36 5.64l1.42-1.42",
    "moon": "M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z",
    "trash": "M3 6h18 M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6 M10 11v6 M14 11v6 M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2",
    "edit": "M12 20h9 M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z",
    "download": "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4 M7 10l5 5 5-5 M12 15V3",
    "compare": "M12 3v18 M3 5h6v14H3z M15 5h6v14h-6z",
    "sparkle": "M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z",
}


def svg_pixmap(name: str, color: str, size: int = 22) -> QPixmap:
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%s" '
           'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="%s"/></svg>'
           % (color, ICONS[name]))
    r = QSvgRenderer(QByteArray(svg.encode()))
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    r.render(p)
    p.end()
    pm.setDevicePixelRatio(2)
    return pm


def icon(name: str, color: str, size: int = 22) -> QIcon:
    return QIcon(svg_pixmap(name, color, size))


_QSS = Template("""
* { font-family: "Segoe UI", "Inter", "Noto Sans", sans-serif; font-size: 13px; }
QWidget { color: $text; }
QMainWindow, #Root, #PageBody, QScrollArea, QStackedWidget { background: $bg; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QLabel { background: transparent; }
#Sidebar { background: $card; border-right: 1px solid $border; }
#Header { background: $bg; border-bottom: 1px solid $border; }
#NavButton { text-align: left; padding: 11px 14px; border: none; border-left: 4px solid transparent;
  border-radius: 10px; color: $muted; background: transparent; font-size: 14px; }
#NavButton:hover { background: $hover; color: $text; }
#NavButton:checked { background: $soft; color: $text; border-left: 4px solid $cyan; font-weight: 600; }
#Card { background: $card; border: 1px solid $border; border-radius: 16px; }
#Card[selected="true"] { border: 2px solid $cyan; }
#H1 { font-size: 26px; font-weight: 800; }
#H2 { font-size: 17px; font-weight: 700; }
#Muted { color: $muted; }
#Badge { background: $soft; border-radius: 10px; padding: 3px 10px; font-weight: 600; }
#DemoBadge { background: #B45309; color: white; border-radius: 10px; padding: 4px 12px; font-weight: 700; }
#LiveBadge { background: #047857; color: white; border-radius: 10px; padding: 4px 12px; font-weight: 700; }
#Banner { background: $soft; border: 1px solid $violet; border-radius: 12px; padding: 10px 14px; }
#DropZone { background: $input; border: 2px dashed $violet; border-radius: 16px; }
#DropZone:hover { border-color: $cyan; background: $hover; }
QPushButton { background: $input; border: 1px solid $border; border-radius: 10px; padding: 8px 14px; }
QPushButton:hover { border-color: $violet; background: $hover; }
QPushButton:pressed { background: $soft; }
QPushButton:disabled { color: $muted; background: $input; border-color: $border; }
#PrimaryButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 $purple, stop:0.55 $violet, stop:1 $pink);
  color: white; border: none; font-weight: 700; font-size: 14px; padding: 12px 24px; border-radius: 12px; }
#PrimaryButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 $violet, stop:0.55 $blue, stop:1 $cyan); }
#PrimaryButton:disabled { background: $hover; color: $muted; }
#IconButton { border: none; background: transparent; padding: 8px; border-radius: 10px; }
#IconButton:hover { background: $hover; }
#HeroButton { background: white; color: $purple; border: none; font-weight: 800; font-size: 15px;
  padding: 13px 28px; border-radius: 14px; }
#HeroButton:hover { background: #F3E8FF; }
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
  background: $input; border: 1px solid $border; border-radius: 8px; padding: 6px 8px;
  selection-background-color: $violet; }
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid $violet; }
QComboBox QAbstractItemView { background: $card; border: 1px solid $border; selection-background-color: $violet; }
QSlider::groove:horizontal { height: 6px; background: $border; border-radius: 3px; }
QSlider::sub-page:horizontal { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 $violet, stop:1 $cyan); border-radius: 3px; }
QSlider::handle:horizontal { background: white; border: 2px solid $violet; width: 14px; height: 14px; margin: -6px 0; border-radius: 9px; }
QProgressBar { background: $input; border: none; border-radius: 6px; height: 12px; text-align: center; color: transparent; }
QProgressBar::chunk { border-radius: 6px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 $violet, stop:0.6 $blue, stop:1 $cyan); }
QTabWidget::pane { border: 1px solid $border; border-radius: 10px; background: $card; top: -1px; }
QTabBar::tab { background: transparent; padding: 8px 14px; color: $muted; border-radius: 8px; margin: 2px; }
QTabBar::tab:selected { background: $soft; color: $text; font-weight: 600; }
QTabBar::tab:hover { color: $text; }
QCheckBox, QRadioButton { spacing: 8px; background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: $border; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: $violet; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar:horizontal { height: 10px; background: transparent; }
QScrollBar::handle:horizontal { background: $border; border-radius: 4px; }
QDialog, QMessageBox { background: $bg; }
QToolTip { background: $card; color: $text; border: 1px solid $violet; padding: 4px; }
""")


def build_qss(theme: str) -> str:
    p = dict(PALETTES.get(theme, PALETTES["dark"]))
    p.update(purple=PURPLE, violet=VIOLET, blue=BLUE, cyan=CYAN, pink=PINK)
    return _QSS.substitute(p)


def palette(theme: str) -> dict:
    return PALETTES.get(theme, PALETTES["dark"])
