"""Reusable widgets: cards, buttons, video player, drop zone, spinner."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QSlider, QStackedLayout, QVBoxLayout, QWidget)

from . import theme
from .art import paint_hero, paint_style_art


def label(text: str, name: str = "", wrap: bool = False) -> QLabel:
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    lb.setWordWrap(wrap)
    return lb


def glow(widget: QWidget, color: str = theme.VIOLET, blur: int = 28, alpha: int = 110, dy: int = 6) -> None:
    fx = QGraphicsDropShadowEffect(widget)
    c = QColor(color)
    c.setAlpha(alpha)
    fx.setColor(c)
    fx.setBlurRadius(blur)
    fx.setOffset(0, dy)
    widget.setGraphicsEffect(fx)


class Card(QFrame):
    """Rounded card. Do NOT enable shadow on cards that contain a video widget."""

    def __init__(self, shadow: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        if shadow:
            glow(self, "#000000", 24, 70, 5)

    def set_selected(self, on: bool) -> None:
        self.setProperty("selected", "true" if on else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class PrimaryButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("PrimaryButton")
        self.setCursor(Qt.PointingHandCursor)
        glow(self, theme.VIOLET, 26, 120, 5)


class IconButton(QPushButton):
    def __init__(self, icon_name: str, tip: str = "", color: str = "#A3A6BF", parent=None):
        super().__init__(parent)
        self.setObjectName("IconButton")
        self.icon_name = icon_name
        self.setToolTip(tip)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(38, 38)
        self.set_color(color)

    def set_color(self, color: str) -> None:
        self.setIcon(theme.icon(self.icon_name, color, 20))


class StyleArt(QWidget):
    def __init__(self, style, w: int = 200, h: int = 118, parent=None):
        super().__init__(parent)
        self.style_obj = style
        self.setFixedSize(w, h)

    def paintEvent(self, _e):
        p = QPainter(self)
        paint_style_art(p, QRectF(0, 0, self.width(), self.height()), self.style_obj)


class HeroBanner(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(250)
        glow(self, theme.PURPLE, 40, 120, 10)

    def paintEvent(self, _e):
        p = QPainter(self)
        paint_hero(p, QRectF(0, 0, self.width(), self.height()))


class Spinner(QWidget):
    def __init__(self, size: int = 30, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def start(self) -> None:
        self.timer.start(16)
        self.show()

    def stop(self) -> None:
        self.timer.stop()
        self.hide()

    def _tick(self) -> None:
        self.angle = (self.angle + 8) % 360
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(4, 4, self.width() - 8, self.height() - 8)
        p.setPen(QPen(QColor(139, 92, 246, 60), 4))
        p.drawEllipse(r)
        p.setPen(QPen(QColor(theme.CYAN), 4, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(r, -self.angle * 16, 100 * 16)


class DropZone(QFrame):
    fileDropped = Signal(str)
    clicked = Signal()

    def __init__(self, text: str = "Drop a video here\nor click to browse", parent=None):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(220)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        ic = QLabel()
        ic.setPixmap(theme.svg_pixmap("upload", theme.VIOLET, 46))
        ic.setAlignment(Qt.AlignCenter)
        t = QLabel(text)
        t.setAlignment(Qt.AlignCenter)
        t.setObjectName("H2")
        s = label("MP4, MOV, AVI, MKV, WEBM...  |  max 10 seconds for AI", "Muted")
        s.setAlignment(Qt.AlignCenter)
        for w in (ic, t, s):
            lay.addWidget(w)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            if u.isLocalFile():
                self.fileDropped.emit(u.toLocalFile())
                break

    def mousePressEvent(self, _e):
        self.clicked.emit()


def fmt_time(ms: int) -> str:
    s = max(0, ms) // 1000
    return f"{s // 60}:{s % 60:02d}"


class VideoPlayer(QWidget):
    """Video + play/pause + seek bar + time + full screen."""

    def __init__(self, parent=None, min_height: int = 220, placeholder: str = "No video"):
        super().__init__(parent)
        self.path: str | None = None
        self.video = QVideoWidget()
        self.video.setMinimumHeight(min_height)
        self.video.setStyleSheet("background:#000;")
        self.player = QMediaPlayer(self)
        self.audio = None
        try:                                   # no sound card -> play silently instead of crashing
            if not os.environ.get("CARTOONAI_NO_AUDIO") and len(QMediaDevices.audioOutputs()) > 0:
                self.audio = QAudioOutput(self)
                self.player.setAudioOutput(self.audio)
        except Exception:
            self.audio = None
        self.player.setVideoOutput(self.video)

        self.ph = QLabel(placeholder)
        self.ph.setAlignment(Qt.AlignCenter)
        self.ph.setObjectName("Muted")
        self.ph.setMinimumHeight(min_height)
        self.ph.setStyleSheet("background:#0B0B12; border-radius:12px; color:#8A8DA8;")

        self.stack_host = QWidget()
        self.stack = QStackedLayout(self.stack_host)
        self.stack.addWidget(self.ph)
        self.stack.addWidget(self.video)

        self.btn = QPushButton()
        self.btn.setObjectName("IconButton")
        self.btn.setFixedSize(36, 36)
        self.btn.setIcon(theme.icon("play", "#8B5CF6", 18))
        self.btn.clicked.connect(self.toggle)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self.player.setPosition)
        self.time = QLabel("0:00 / 0:00")
        self.time.setObjectName("Muted")
        self.full = QPushButton()
        self.full.setObjectName("IconButton")
        self.full.setFixedSize(36, 36)
        self.full.setIcon(theme.icon("full", "#8B5CF6", 18))
        self.full.setToolTip("Full screen (Esc to exit)")
        self.full.clicked.connect(lambda: self.path and self.video.setFullScreen(True))

        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        for w in (self.btn, self.slider, self.time, self.full):
            bar.addWidget(w)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.stack_host, 1)
        lay.addLayout(bar)

        self.player.positionChanged.connect(self._pos)
        self.player.durationChanged.connect(lambda d: self.slider.setRange(0, d))
        self.player.playbackStateChanged.connect(self._state)
        self.set_controls(False)

    def set_controls(self, on: bool) -> None:
        for w in (self.btn, self.slider, self.time, self.full):
            w.setEnabled(on)

    def set_source(self, path: str | None) -> None:
        self.player.stop()
        if not path or not Path(path).exists():
            self.path = None
            self.player.setSource(QUrl())
            self.stack.setCurrentIndex(0)
            self.set_controls(False)
            self.time.setText("0:00 / 0:00")
            return
        self.path = path
        self.player.setSource(QUrl.fromLocalFile(path))
        self.stack.setCurrentIndex(1)
        self.set_controls(True)
        self.player.pause()           # shows the first frame

    def set_placeholder(self, text: str) -> None:
        self.ph.setText(text)

    def toggle(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def play(self) -> None:
        if self.path:
            self.player.play()

    def pause(self) -> None:
        self.player.pause()

    def position_ms(self) -> int:
        return self.player.position()

    def _pos(self, ms: int) -> None:
        if not self.slider.isSliderDown():
            self.slider.setValue(ms)
        self.time.setText(f"{fmt_time(ms)} / {fmt_time(self.player.duration())}")

    def _state(self, st) -> None:
        playing = st == QMediaPlayer.PlayingState
        self.btn.setIcon(theme.icon("pause" if playing else "play", "#8B5CF6", 18))

    def release(self) -> None:
        self.player.stop()
        self.player.setSource(QUrl())
        self.path = None
