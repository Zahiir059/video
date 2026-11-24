from __future__ import annotations

import os

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QConicalGradient, QPainter, QPen, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QHBoxLayout,
                               QLabel, QPushButton, QSlider, QStackedWidget, QVBoxLayout, QWidget)

from . import art
from .theme import CYAN, PINK, VIOLET


# Headless self-test on Linux has no GPU video surface; use a silent stub there.
def _headless() -> bool:
    return os.environ.get("QT_QPA_PLATFORM") == "offscreen" or bool(os.environ.get("CARTOON_NO_VIDEO"))


def has_audio_input() -> bool:
    if _headless():
        return False
    try:
        return bool(QMediaDevices.audioInputs())
    except Exception:
        return False


def has_video_input() -> bool:
    if _headless():
        return False
    try:
        return bool(QMediaDevices.videoInputs())
    except Exception:
        return False


class _NullPlayer:
    def __getattr__(self, name):
        return lambda *a, **k: None

    def duration(self):
        return 0

    def playbackState(self):
        return None


def label(text: str = "", obj: str = "", wrap: bool = False) -> QLabel:
    lb = QLabel(text)
    if obj:
        lb.setObjectName(obj)
    lb.setWordWrap(wrap)
    return lb


def button(text: str, obj: str = "", slot=None) -> QPushButton:
    b = QPushButton(text)
    if obj:
        b.setObjectName(obj)
    b.setCursor(Qt.PointingHandCursor)
    if slot:
        b.clicked.connect(lambda _=False: slot())
    return b


def card(shadow: bool = True) -> QFrame:
    f = QFrame()
    f.setObjectName("Card")
    if shadow:
        e = QGraphicsDropShadowEffect(f)
        e.setBlurRadius(28)
        e.setOffset(0, 6)
        e.setColor(QColor(0, 0, 0, 90))
        f.setGraphicsEffect(e)
    return f


def fade_in(w: QWidget, ms: int = 200) -> None:
    eff = QGraphicsOpacityEffect(w)
    w.setGraphicsEffect(eff)
    anim = QPropertyAnimation(eff, b"opacity", w)
    anim.setDuration(ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.finished.connect(lambda: w.setGraphicsEffect(None))
    anim.start()
    w._fade = anim  # keep a reference


def fmt_time(ms: int) -> str:
    s = max(0, int(ms / 1000))
    return f"{s // 60}:{s % 60:02d}"


class Spinner(QWidget):
    """Animated loading ring."""

    def __init__(self, size: int = 30, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._a = 0
        self._t = QTimer(self)
        self._t.timeout.connect(self._tick)
        self.hide()

    def _tick(self):
        self._a = (self._a + 14) % 360
        self.update()

    def start(self):
        self.show()
        self._t.start(30)

    def stop(self):
        self._t.stop()
        self.hide()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QConicalGradient(self.width() / 2, self.height() / 2, -self._a)
        g.setColorAt(0, QColor(CYAN))
        g.setColorAt(.6, QColor(VIOLET))
        g.setColorAt(1, QColor(PINK))
        pen = QPen(g, 4)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(QRectF(4, 4, self.width() - 8, self.height() - 8), 0, 270 * 16)


class HeroBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(250)

    def paintEvent(self, _):
        p = QPainter(self)
        art.hero_paint(p, self.width(), self.height())


class VideoPlayer(QWidget):
    """Preview player: play/pause, seek bar, time, full screen."""

    def __init__(self, placeholder: str = "No video selected", parent=None, min_h: int = 200):
        super().__init__(parent)
        self.headless = _headless()
        self.stack = QStackedWidget()
        self.ph = QLabel(placeholder)
        self.ph.setAlignment(Qt.AlignCenter)
        self.ph.setWordWrap(True)
        self.ph.setStyleSheet("background:#0A0A12;color:#8E8CA8;border-radius:12px;padding:12px;")
        self.video = QWidget() if self.headless else QVideoWidget()
        self.video.setStyleSheet("background:#000;")
        self.stack.addWidget(self.ph)
        self.stack.addWidget(self.video)
        self.stack.setMinimumHeight(min_h)

        self.audio = None
        if self.headless:
            self.player = _NullPlayer()
        else:
            self.player = QMediaPlayer(self)
            try:  # a PC without any sound device must not crash the app
                if QMediaDevices.audioOutputs():
                    self.audio = QAudioOutput(self)
                    self.player.setAudioOutput(self.audio)
            except Exception:
                self.audio = None
            self.player.setVideoOutput(self.video)

        self.btn = button("▶", "Icon")
        self.slider = QSlider(Qt.Horizontal)
        self.time = label("0:00 / 0:00", "Sub")
        self.full = button("⛶", "Icon")
        self.full.setToolTip("Full screen (press Esc to leave)")
        bar = QHBoxLayout()
        bar.addWidget(self.btn)
        bar.addWidget(self.slider, 1)
        bar.addWidget(self.time)
        bar.addWidget(self.full)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(self.stack, 1)
        lay.addLayout(bar)

        self.btn.clicked.connect(self.toggle)
        self.full.clicked.connect(self.go_full)
        self.slider.sliderMoved.connect(self.player.setPosition)
        if not self.headless:
            self.player.durationChanged.connect(lambda d: self.slider.setRange(0, d))
            self.player.positionChanged.connect(self._pos)
            self.player.playbackStateChanged.connect(self._state)
            self.player.errorOccurred.connect(self._err)
        self.path = ""

    def load(self, path: str):
        self.path = path
        if self.headless:
            self.ph.setText("Video preview is disabled in headless test mode.\n" + os.path.basename(path))
            return
        self.stack.setCurrentIndex(1)
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.pause()

    def clear(self, text: str | None = None):
        self.path = ""
        self.player.stop()
        self.player.setSource(QUrl())
        if text:
            self.ph.setText(text)
        self.stack.setCurrentIndex(0)
        self.slider.setRange(0, 0)
        self.time.setText("0:00 / 0:00")

    def toggle(self):
        if not self.path:
            return
        if not self.headless and self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def play_from_start(self):
        if self.path:
            self.player.setPosition(0)
            self.player.play()

    def stop(self):
        self.player.pause()

    def go_full(self):
        if self.path:
            self.video.setFullScreen(not self.video.isFullScreen())

    def _pos(self, pos: int):
        if not self.slider.isSliderDown():
            self.slider.setValue(pos)
        self.time.setText(f"{fmt_time(pos)} / {fmt_time(self.player.duration())}")

    def _state(self, st):
        self.btn.setText("❚❚" if st == QMediaPlayer.PlayingState else "▶")

    def _err(self, _err, text: str):
        if self.path:
            self.ph.setText("This video cannot be previewed here (the file is still usable).\n" + text)
            self.stack.setCurrentIndex(0)


class StyleCard(QFrame):
    selected = Signal(str)

    def __init__(self, style: dict, small: bool = False, parent=None):
        super().__init__(parent)
        self.style_id = style["id"]
        self.setObjectName("Card")
        e = QGraphicsDropShadowEffect(self)
        e.setBlurRadius(24)
        e.setOffset(0, 5)
        e.setColor(QColor(0, 0, 0, 90))
        self.setGraphicsEffect(e)
        w, h = (210, 118) if small else (270, 150)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 12)
        lay.setSpacing(6)
        pic = QLabel()
        pic.setPixmap(art.style_pixmap(style, w, h))
        pic.setFixedSize(QSize(w, h))
        lay.addWidget(pic, alignment=Qt.AlignHCenter)
        lay.addWidget(label(style["name"], "SubHeading"))
        if not small:
            lay.addWidget(label(style["desc"], "Sub", wrap=True))
        b = button("Select style" if not small else "Use", "Primary" if not small else "")
        b.clicked.connect(lambda: self.selected.emit(self.style_id))
        lay.addWidget(b)
        self.setFixedWidth(w + 22)

    def mousePressEvent(self, e):
        self.selected.emit(self.style_id)


def thumb_label(path: str, w: int = 96, h: int = 54) -> QLabel:
    lb = QLabel()
    lb.setFixedSize(w, h)
    lb.setAlignment(Qt.AlignCenter)
    lb.setStyleSheet("background:#0A0A12;border-radius:8px;")
    pm = QPixmap(path) if path else QPixmap()
    if not pm.isNull():
        lb.setPixmap(pm.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
    else:
        lb.setText("▶")
    return lb


def status_chip(status: str) -> QLabel:
    obj = {"Completed": "ChipOk", "Processing": "ChipWarn", "Failed": "ChipBad",
           "Interrupted": "ChipBad", "Cancelled": "ChipBad"}.get(status, "Chip")
    return label(status, obj)
