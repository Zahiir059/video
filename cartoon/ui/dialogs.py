"""Modal dialogs: preview, compare, export, 10-second trimmer."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QSlider, QVBoxLayout)

from ..config import LIB_DIR, MAX_SECONDS
from ..jobs import FuncWorker
from ..media import ASPECTS, MediaError, cut_segment, export_video, probe, tmp_path
from .widgets import PrimaryButton, Spinner, VideoPlayer, label


class PreviewDialog(QDialog):
    def __init__(self, path: str, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(820, 560)
        lay = QVBoxLayout(self)
        lay.addWidget(label(title, "H2"))
        self.player = VideoPlayer(min_height=380)
        lay.addWidget(self.player, 1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        lay.addWidget(close, 0, Qt.AlignRight)
        self.player.set_source(path)
        self.player.play()

    def done(self, r):
        self.player.release()
        super().done(r)


class CompareDialog(QDialog):
    def __init__(self, original: str, result: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compare: original vs result")
        self.resize(1100, 560)
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        self.a, self.b = VideoPlayer(min_height=340), VideoPlayer(min_height=340)
        for title, pl in (("Original", self.a), ("Result", self.b)):
            col = QVBoxLayout()
            col.addWidget(label(title, "H2"))
            col.addWidget(pl, 1)
            row.addLayout(col, 1)
        lay.addLayout(row, 1)
        btns = QHBoxLayout()
        play = PrimaryButton("Play both")
        pause = QPushButton("Pause both")
        restart = QPushButton("Restart")
        close = QPushButton("Close")
        play.clicked.connect(lambda: (self.a.play(), self.b.play()))
        pause.clicked.connect(lambda: (self.a.pause(), self.b.pause()))
        restart.clicked.connect(self._restart)
        close.clicked.connect(self.accept)
        for b in (play, pause, restart):
            btns.addWidget(b)
        btns.addStretch(1)
        btns.addWidget(close)
        lay.addLayout(btns)
        self.a.set_source(original)
        self.b.set_source(result)
        self.a.player.setLoops(-1)
        self.b.player.setLoops(-1)

    def _restart(self) -> None:
        for p in (self.a, self.b):
            p.player.setPosition(0)
            p.play()

    def done(self, r):
        self.a.release()
        self.b.release()
        super().done(r)


class ExportDialog(QDialog):
    def __init__(self, src: str, suggested: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export video (MP4)")
        self.setMinimumWidth(460)
        self.src, self.suggested = src, suggested
        try:
            self.native_h = probe(src).height
        except MediaError:
            self.native_h = 0
        lay = QVBoxLayout(self)
        lay.addWidget(label("Export as MP4", "H2"))
        lay.addWidget(label(f"This video is {self.native_h}p. Larger sizes are scaled up locally by FFmpeg "
                            "(no extra detail is created).", "Muted", True))
        self.res = QComboBox()
        self.res.addItem("Original size", None)
        for h in (480, 720, 1080):
            self.res.addItem(f"{h}p" + (" (upscaled locally)" if h > self.native_h else ""), h)
        self.asp = QComboBox()
        for k, v in ASPECTS.items():
            self.asp.addItem(k + ("" if v is None else " (black bars added if needed)"), v)
        lay.addWidget(label("Resolution"))
        lay.addWidget(self.res)
        lay.addWidget(label("Aspect ratio"))
        lay.addWidget(self.asp)
        self.status = label("", "Muted", True)
        self.spin = Spinner(24)
        self.spin.hide()
        lay.addWidget(self.status)
        lay.addWidget(self.spin)
        row = QHBoxLayout()
        self.go = PrimaryButton("Export...")
        self.go.clicked.connect(self.run)
        cancel = QPushButton("Close")
        cancel.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(cancel)
        row.addWidget(self.go)
        lay.addLayout(row)
        self.worker = None

    def run(self) -> None:
        dest, _ = QFileDialog.getSaveFileName(self, "Save MP4", str(Path.home() / (self.suggested + ".mp4")),
                                              "MP4 video (*.mp4)")
        if not dest:
            return
        if not dest.lower().endswith(".mp4"):
            dest += ".mp4"
        self.go.setEnabled(False)
        self.status.setText("Exporting...")
        self.spin.start()
        self.worker = FuncWorker(export_video, self.src, dest, self.res.currentData(), self.asp.currentData())
        self.worker.done.connect(lambda _r: self._finish("Saved to " + dest))
        self.worker.failed.connect(lambda m: self._finish("Export failed: " + m))
        self.worker.start()

    def _finish(self, msg: str) -> None:
        self.spin.stop()
        self.go.setEnabled(True)
        self.status.setText(msg)


class TrimDialog(QDialog):
    """Shown for videos longer than 10 s: choose which 10-second segment to use."""

    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.info = info
        self.setWindowTitle("Choose a 10-second segment")
        self.resize(760, 560)
        lay = QVBoxLayout(self)
        lay.addWidget(label("Your video is longer than 10 seconds", "H2"))
        lay.addWidget(label(f"The AI can transform at most {MAX_SECONDS:.0f} seconds. Your video is "
                            f"{info.duration:.1f} s long. Drag the slider to pick the segment to use.", "Muted", True))
        self.player = VideoPlayer(min_height=300)
        lay.addWidget(self.player, 1)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, max(0, int((info.duration - MAX_SECONDS) * 10)))
        self.slider.valueChanged.connect(self._moved)
        lay.addWidget(self.slider)
        self.lbl = label("", "H2")
        lay.addWidget(self.lbl)
        row = QHBoxLayout()
        prev = QPushButton("Preview segment")
        prev.clicked.connect(self._preview)
        ok = PrimaryButton("Use this 10-second segment")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        row.addWidget(prev)
        row.addStretch(1)
        row.addWidget(cancel)
        row.addWidget(ok)
        lay.addLayout(row)
        self.player.set_source(info.path)
        self.player.player.positionChanged.connect(self._watch)
        self._moved(0)

    def start(self) -> float:
        return self.slider.value() / 10.0

    def _moved(self, _v) -> None:
        s = self.start()
        e = min(self.info.duration, s + MAX_SECONDS)
        self.lbl.setText(f"Selected: {s:.1f} s  to  {e:.1f} s   ({e - s:.1f} s)")
        self.player.player.setPosition(int(s * 1000))

    def _preview(self) -> None:
        self.player.player.setPosition(int(self.start() * 1000))
        self.player.play()

    def _watch(self, ms: int) -> None:
        if ms >= (self.start() + MAX_SECONDS) * 1000:
            self.player.pause()

    def done(self, r):
        self.player.release()
        super().done(r)


def make_segment(info, start: float) -> str:
    """Cuts the chosen segment into a temp MP4 (re-encoded so it is frame accurate)."""
    out = tmp_path(".mp4")
    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        cut_segment(info.path, start, min(MAX_SECONDS, info.duration - start), out)
    finally:
        QApplication.restoreOverrideCursor()
    return out


def warn(parent, title: str, text: str) -> None:
    QMessageBox.warning(parent, title, text)
