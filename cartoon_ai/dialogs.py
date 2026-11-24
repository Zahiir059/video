from __future__ import annotations

import os
import time

from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import (QAudioInput, QCamera, QMediaCaptureSession, QMediaDevices,
                                  QMediaFormat, QMediaRecorder)
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QHBoxLayout, QMessageBox,
                               QSlider, QSpinBox, QVBoxLayout)

from . import ffmpeg_tools as ff
from . import paths
from .jobs import run_blocking
from .widgets import VideoPlayer, button, label

MAX_SECONDS = 10.0


class TrimDialog(QDialog):
    """Pick a segment of at most 10 seconds. Used when a video is longer than the AI limit."""

    def __init__(self, info: ff.VideoInfo, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Trim to 10 seconds")
        self.setMinimumWidth(640)
        self.info = info
        self.result_path = ""
        lay = QVBoxLayout(self)
        lay.addWidget(label("This video is %.1f s long" % info.duration, "SubHeading"))
        lay.addWidget(label("The AI can transform at most 10 seconds. Drag the slider to choose "
                            "which part to keep.", "Sub", wrap=True))
        self.player = VideoPlayer(min_h=240)
        self.player.load(info.path)
        lay.addWidget(self.player)
        self.len_spin = QSpinBox()
        self.len_spin.setRange(1, 10)
        self.len_spin.setValue(10)
        self.len_spin.setSuffix(" s segment")
        self.start = QSlider(Qt.Horizontal)
        self.start.setRange(0, 0)
        self.info_lb = label("", "Sub")
        row = QHBoxLayout()
        row.addWidget(label("Start:"))
        row.addWidget(self.start, 1)
        row.addWidget(self.len_spin)
        lay.addLayout(row)
        lay.addWidget(self.info_lb)
        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(button("Cancel", "", self.reject))
        self.ok = button("Trim and use this segment", "Primary", self._do)
        btns.addWidget(self.ok)
        lay.addLayout(btns)
        self.start.valueChanged.connect(self._changed)
        self.len_spin.valueChanged.connect(self._range)
        self._range()

    def _range(self):
        mx = max(0, int((self.info.duration - self.len_spin.value()) * 10))
        self.start.setRange(0, mx)
        self._changed()

    def _changed(self):
        s = self.start.value() / 10.0
        e = s + self.len_spin.value()
        self.info_lb.setText(f"Segment: {s:.1f} s  to  {min(e, self.info.duration):.1f} s")
        self.player.player.setPosition(int(s * 1000))

    def _do(self):
        s = self.start.value() / 10.0
        d = min(float(self.len_spin.value()), self.info.duration - s)
        dst = paths.work_file(f"trim_{int(time.time() * 1000)}.mp4")
        try:
            self.result_path = run_blocking(self, "Trimming video...", lambda: ff.trim(self.info.path, dst, s, d))
        except Exception as e:
            QMessageBox.warning(self, "Trim failed", str(e))
            return
        self.player.clear()
        self.accept()

    def done(self, r):
        self.player.clear()
        super().done(r)


class ExportDialog(QDialog):
    def __init__(self, src: str, default_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export video")
        self.src = src
        self.default_name = default_name
        lay = QVBoxLayout(self)
        lay.addWidget(label("Export as MP4", "SubHeading"))
        self.res = QComboBox()
        self.res.addItems(["Original size", "480p", "720p", "1080p"])
        self.asp = QComboBox()
        self.asp.addItems(["Original aspect ratio", "16:9", "9:16", "1:1"])
        lay.addWidget(label("Resolution"))
        lay.addWidget(self.res)
        lay.addWidget(label("Aspect ratio (black bars are added, nothing is cropped)"))
        lay.addWidget(self.asp)
        lay.addWidget(label("Resolution and aspect are applied here on your PC. The size of the "
                            "AI-generated video itself is decided by the AI service.", "Sub", wrap=True))
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(button("Cancel", "", self.reject))
        row.addWidget(button("Choose file and export", "Primary", self._go))
        lay.addLayout(row)

    def _go(self):
        dst, _ = QFileDialog.getSaveFileName(self, "Save MP4", self.default_name + ".mp4", "MP4 video (*.mp4)")
        if not dst:
            return
        if not dst.lower().endswith(".mp4"):
            dst += ".mp4"
        h = {0: None, 1: 480, 2: 720, 3: 1080}[self.res.currentIndex()]
        a = {0: None, 1: (16, 9), 2: (9, 16), 3: (1, 1)}[self.asp.currentIndex()]
        try:
            run_blocking(self, "Exporting...", lambda: ff.export_video(self.src, dst, h, a))
        except Exception as e:
            QMessageBox.warning(self, "Export failed", str(e))
            return
        QMessageBox.information(self, "Export finished", f"Saved:\n{dst}")
        self.accept()


class CompareDialog(QDialog):
    """Original and cartoon videos side by side."""

    def __init__(self, original: str, output: str, parent=None, title="Compare"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1000, 560)
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        left, right = QVBoxLayout(), QVBoxLayout()
        self.a = VideoPlayer("Original not available")
        self.b = VideoPlayer("Result not available")
        left.addWidget(label("Original", "SubHeading"))
        left.addWidget(self.a)
        right.addWidget(label("Cartoon result", "SubHeading"))
        right.addWidget(self.b)
        row.addLayout(left)
        row.addLayout(right)
        lay.addLayout(row, 1)
        if original and os.path.exists(original):
            self.a.load(original)
        if output and os.path.exists(output):
            self.b.load(output)
        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(button("Play both", "Primary", self._both))
        btns.addWidget(button("Pause", "", self._pause))
        btns.addWidget(button("Close", "", self.accept))
        lay.addLayout(btns)

    def _both(self):
        self.a.play_from_start()
        self.b.play_from_start()

    def _pause(self):
        self.a.stop()
        self.b.stop()

    def done(self, r):
        self.a.clear()
        self.b.clear()
        super().done(r)


class RecordVideoDialog(QDialog):
    """Webcam recording (only offered when a camera exists)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record video")
        self.resize(640, 480)
        self.result_path = ""
        self.session = QMediaCaptureSession(self)
        self.camera = QCamera(QMediaDevices.defaultVideoInput(), self)
        self.session.setCamera(self.camera)
        self.view = QVideoWidget()
        self.session.setVideoOutput(self.view)
        self.rec = QMediaRecorder(self)
        self.session.setRecorder(self.rec)
        self.path = paths.work_file(f"record_{int(time.time())}.mp4")
        self.rec.setOutputLocation(QUrl.fromLocalFile(self.path))
        lay = QVBoxLayout(self)
        lay.addWidget(self.view, 1)
        self.note = label("Record up to 10 seconds, then press Stop.", "Sub")
        lay.addWidget(self.note)
        row = QHBoxLayout()
        self.start_b = button("Start recording", "Primary", self._start)
        self.stop_b = button("Stop and use", "", self._stop)
        self.stop_b.setEnabled(False)
        row.addWidget(self.start_b)
        row.addWidget(self.stop_b)
        row.addStretch(1)
        row.addWidget(button("Cancel", "", self.reject))
        lay.addLayout(row)
        self.rec.recorderStateChanged.connect(self._state)
        self.rec.errorOccurred.connect(lambda *_: self.note.setText("Recording error: " + self.rec.errorString()))
        self.camera.start()

    def _start(self):
        self.rec.record()
        self.start_b.setEnabled(False)
        self.stop_b.setEnabled(True)

    def _stop(self):
        self.rec.stop()

    def _state(self, st):
        if st == QMediaRecorder.StoppedState and self.stop_b.isEnabled():
            self.result_path = self.path if os.path.exists(self.path) else ""
            self.accept()

    def done(self, r):
        try:
            self.camera.stop()
        except Exception:
            pass
        super().done(r)


class RecordAudioDialog(QDialog):
    """Voice-over recording (only offered when a microphone exists)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record voice-over")
        self.result_path = ""
        self.session = QMediaCaptureSession(self)
        self.mic = QAudioInput(QMediaDevices.defaultAudioInput(), self)
        self.session.setAudioInput(self.mic)
        self.rec = QMediaRecorder(self)
        self.session.setRecorder(self.rec)
        fmt = QMediaFormat(QMediaFormat.FileFormat.Mpeg4Audio)
        self.rec.setMediaFormat(fmt)
        self.path = paths.work_file(f"voice_{int(time.time())}.m4a")
        self.rec.setOutputLocation(QUrl.fromLocalFile(self.path))
        lay = QVBoxLayout(self)
        self.note = label("Press Start, speak, then Stop.", "Sub")
        lay.addWidget(self.note)
        row = QHBoxLayout()
        self.start_b = button("Start", "Primary", self._start)
        self.stop_b = button("Stop and use", "", self.rec.stop)
        self.stop_b.setEnabled(False)
        row.addWidget(self.start_b)
        row.addWidget(self.stop_b)
        row.addWidget(button("Cancel", "", self.reject))
        lay.addLayout(row)
        self.rec.recorderStateChanged.connect(self._state)

    def _start(self):
        self.rec.record()
        self.start_b.setEnabled(False)
        self.stop_b.setEnabled(True)
        self.note.setText("Recording...")

    def _state(self, st):
        if st == QMediaRecorder.StoppedState and self.stop_b.isEnabled():
            self.result_path = self.path if os.path.exists(self.path) else ""
            self.accept()
