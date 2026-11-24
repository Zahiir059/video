"""Cards used on several pages."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from . import theme
from .widgets import Card, StyleArt, label

STATUS_COLORS = {"Completed": "#10B981", "Processing": "#F59E0B", "Failed": "#EF4444", "Interrupted": "#9CA3AF"}


class StyleCard(Card):
    chosen = Signal(str)

    def __init__(self, ctx, style, parent=None):
        super().__init__(shadow=True, parent=parent)
        self.ctx, self.style_obj = ctx, style
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
        lay.addWidget(StyleArt(style, 216, 124), 0, Qt.AlignHCenter)
        lay.addWidget(label(style.name, "H2"))
        lay.addWidget(label(style.desc, "Muted", True), 1)
        self.btn = QPushButton("Select")
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.clicked.connect(lambda: self.chosen.emit(style.id))
        lay.addWidget(self.btn)
        ctx.styleChanged.connect(lambda _s: self.refresh())
        self.refresh()

    def refresh(self) -> None:
        on = self.ctx.style_id == self.style_obj.id
        self.btn.setText("Selected" if on else "Select")
        self.set_selected(on)


class ActionCard(Card):
    clicked = Signal()

    def __init__(self, icon_name: str, title: str, subtitle: str, color: str, parent=None):
        super().__init__(shadow=True, parent=parent)
        self.setCursor(Qt.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        ic = QLabel()
        ic.setPixmap(theme.svg_pixmap(icon_name, color, 30))
        ic.setFixedSize(40, 40)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(label(title, "H2"))
        col.addWidget(label(subtitle, "Muted", True))
        lay.addWidget(ic)
        lay.addLayout(col, 1)

    def mousePressEvent(self, _e):
        self.clicked.emit()


def status_text(row) -> str:
    s = row["status"] or ""
    if s == "Completed" and row["provider"] == "demo":
        return "Completed - DEMO (not AI)"
    return s


def thumb_label(path: str | None, w: int, h: int) -> QLabel:
    lb = QLabel()
    lb.setFixedSize(w, h)
    lb.setAlignment(Qt.AlignCenter)
    lb.setStyleSheet("background:#0B0B12; border-radius:10px; color:#8A8DA8;")
    if path and Path(path).exists():
        pm = QPixmap(path)
        if not pm.isNull():
            lb.setPixmap(pm.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            lb.setScaledContents(False)
            return lb
    lb.setText("No preview")
    return lb


def status_badge(row) -> QLabel:
    text = status_text(row)
    color = STATUS_COLORS.get(row["status"], "#9CA3AF")
    lb = QLabel(text)
    lb.setStyleSheet(f"background:{color}; color:white; border-radius:9px; padding:2px 9px; font-weight:600;")
    return lb
