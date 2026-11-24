from __future__ import annotations

import os
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
                               QLineEdit, QListWidget, QMessageBox, QSlider, QSpinBox, QTabWidget, QVBoxLayout,
                               QWidget)

from .. import ffmpeg_tools as ff
from .. import paths
from ..dialogs import RecordAudioDialog
from ..jobs import run_blocking
from ..widgets import VideoPlayer, button, card, has_audio_input, label


def _slider(lo, hi, val):
    s = QSlider(Qt.Horizontal)
    s.setRange(lo, hi)
    s.setValue(val)
    return s


class EditorPage(QWidget):
    def __init__(self, ctx, win):
        super().__init__()
        self.setObjectName("Page")
        self.ctx, self.win = ctx, win
        self.path = ""
        self.info: ff.VideoInfo | None = None
        self.overlays: list[dict] = []
        self.sub_path = ""
        self.music_path = ""

        root = QHBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 28)
        root.setSpacing(16)

        left = QVBoxLayout()
        left.addWidget(label("Video Editor", "Heading"))
        self.player = VideoPlayer("Open a video to start editing", min_h=300)
        left.addWidget(self.player, 1)
        self.info_lb = label("", "Sub", wrap=True)
        left.addWidget(self.info_lb)
        row = QHBoxLayout()
        row.addWidget(button("Open video...", "", self.open_dialog))
        self.apply_b = button("Apply edits", "Primary", self.apply)
        self.apply_b.setEnabled(False)
        row.addWidget(self.apply_b)
        left.addLayout(row)
        row2 = QHBoxLayout()
        self.use_b = button("Use in AI Studio", "", lambda: self.path and win.open_studio(self.path))
        self.save_b = button("Save to My Creations", "", self.save_creation)
        self.exp_b = button("Export...", "", self.export)
        for b in (self.use_b, self.save_b, self.exp_b):
            b.setEnabled(False)
            row2.addWidget(b)
        left.addLayout(row2)
        root.addLayout(left, 3)

        tabs = QTabWidget()
        root.addWidget(tabs, 2)
        tabs.addTab(self._tab_trim(), "Trim")
        tabs.addTab(self._tab_frame(), "Crop")
        tabs.addTab(self._tab_speed(), "Speed")
        tabs.addTab(self._tab_color(), "Color")
        tabs.addTab(self._tab_text(), "Text")
        tabs.addTab(self._tab_audio(), "Audio")

    # ---- tabs ------------------------------------------------------------------
    def _tab_trim(self):
        w = QWidget()
        f = QFormLayout(w)
        self.t_start = QDoubleSpinBox()
        self.t_start.setDecimals(1)
        self.t_start.setSuffix(" s")
        self.t_end = QDoubleSpinBox()
        self.t_end.setDecimals(1)
        self.t_end.setSuffix(" s")
        f.addRow("Start", self.t_start)
        f.addRow("End (0 = to the end)", self.t_end)
        f.addRow(label("Trim is applied with 'Apply edits'.", "Sub"))
        self.split_t = QDoubleSpinBox()
        self.split_t.setDecimals(1)
        self.split_t.setSuffix(" s")
        f.addRow("Split at", self.split_t)
        f.addRow(button("Split into two clips", "", self.split))
        f.addRow(label("Split saves two new clips to My Creations and keeps this one.", "Sub", wrap=True))
        return w

    def _tab_frame(self):
        w = QWidget()
        f = QFormLayout(w)
        self.crop = QComboBox()
        self.crop.addItems(["No crop", "Center crop 16:9", "Center crop 9:16", "Center crop 1:1",
                            "Center crop 4:3", "Custom rectangle"])
        f.addRow("Crop", self.crop)
        self.cx, self.cy, self.cw, self.ch = (QSpinBox() for _ in range(4))
        for s in (self.cx, self.cy, self.cw, self.ch):
            s.setRange(0, 8000)
        self.cw.setValue(640)
        self.ch.setValue(360)
        f.addRow("Custom: x", self.cx)
        f.addRow("Custom: y", self.cy)
        f.addRow("Custom: width", self.cw)
        f.addRow("Custom: height", self.ch)
        self.rot = QComboBox()
        self.rot.addItems(["No rotation", "Rotate 90° clockwise", "Rotate 180°", "Rotate 90° counter-clockwise"])
        f.addRow("Rotate", self.rot)
        self.fh = QCheckBox("Flip horizontally")
        self.fv = QCheckBox("Flip vertically")
        f.addRow(self.fh)
        f.addRow(self.fv)
        return w

    def _tab_speed(self):
        w = QWidget()
        f = QFormLayout(w)
        self.speed = QDoubleSpinBox()
        self.speed.setRange(0.25, 4.0)
        self.speed.setSingleStep(0.25)
        self.speed.setValue(1.0)
        self.speed.setSuffix(" x")
        f.addRow("Speed", self.speed)
        f.addRow(button("Slow motion (0.5x)", "", lambda: self.speed.setValue(0.5)))
        f.addRow(button("Normal (1x)", "", lambda: self.speed.setValue(1.0)))
        f.addRow(button("Fast (2x)", "", lambda: self.speed.setValue(2.0)))
        return w

    def _tab_color(self):
        w = QWidget()
        f = QFormLayout(w)
        self.br = _slider(-50, 50, 0)
        self.co = _slider(50, 200, 100)
        self.sa = _slider(0, 300, 100)
        f.addRow("Brightness", self.br)
        f.addRow("Contrast", self.co)
        f.addRow("Saturation", self.sa)
        f.addRow(button("Reset", "", lambda: (self.br.setValue(0), self.co.setValue(100), self.sa.setValue(100))))
        return w

    def _tab_text(self):
        w = QWidget()
        f = QFormLayout(w)
        self.ov_text = QLineEdit()
        self.ov_text.setPlaceholderText("Text to show on the video")
        self.ov_pos = QComboBox()
        self.ov_pos.addItems(["Bottom", "Center", "Top"])
        self.ov_size = QSpinBox()
        self.ov_size.setRange(12, 120)
        self.ov_size.setValue(40)
        self.ov_from = QDoubleSpinBox()
        self.ov_to = QDoubleSpinBox()
        for s in (self.ov_from, self.ov_to):
            s.setDecimals(1)
            s.setRange(0, 3600)
            s.setSuffix(" s")
        self.ov_to.setValue(5)
        self.ov_color = QComboBox()
        self.ov_color.addItems(["white", "yellow", "cyan", "pink"])
        f.addRow("Text", self.ov_text)
        f.addRow("Position", self.ov_pos)
        f.addRow("Size", self.ov_size)
        f.addRow("Colour", self.ov_color)
        f.addRow("From", self.ov_from)
        f.addRow("To", self.ov_to)
        f.addRow(button("Add text overlay", "", self.add_overlay))
        self.ov_list = QListWidget()
        self.ov_list.setFixedHeight(80)
        f.addRow(self.ov_list)
        f.addRow(button("Remove selected", "", self.del_overlay))
        self.sub_lb = label("No subtitle file loaded", "Sub")
        sub_b = button("Load subtitles (.srt)...", "", self.load_srt)
        if not ff.has_filter("subtitles"):
            sub_b.setEnabled(False)
            sub_b.setToolTip("This FFmpeg build cannot burn in subtitles; use text overlays")
        f.addRow(sub_b)
        f.addRow(self.sub_lb)
        f.addRow(label("Automatic subtitle generation is not included (it needs a speech-to-text "
                       "service). Load an .srt you already have, or use text overlays.", "Sub", wrap=True))
        return w

    def _tab_audio(self):
        w = QWidget()
        f = QFormLayout(w)
        self.vol = _slider(0, 200, 100)
        self.mute = QCheckBox("Remove original audio")
        f.addRow("Original volume", self.vol)
        f.addRow(self.mute)
        self.mus_lb = label("No extra audio added", "Sub")
        f.addRow(button("Add music / sound effect / voice-over file...", "", self.load_music))
        f.addRow(self.mus_lb)
        self.mus_vol = _slider(0, 200, 100)
        self.mus_off = QDoubleSpinBox()
        self.mus_off.setSuffix(" s")
        self.mus_off.setDecimals(1)
        f.addRow("Extra audio volume", self.mus_vol)
        f.addRow("Starts at", self.mus_off)
        rec = button("Record voice-over with microphone...", "", self.record_voice)
        if not has_audio_input():
            rec.setEnabled(False)
            rec.setToolTip("No microphone found")
        f.addRow(rec)
        f.addRow(label("To trim the extra audio, cut the file in another tool first. The video itself "
                       "is trimmed on the Trim tab.", "Sub", wrap=True))
        return w

    # ---- actions ---------------------------------------------------------------
    def open_dialog(self):
        p, _ = QFileDialog.getOpenFileName(self, "Open video", "",
                                           "Video files (*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.wmv *.flv *.mpg *.mpeg *.3gp);;All files (*.*)")
        if p:
            self.open_video(p)

    def open_video(self, path: str) -> bool:
        try:
            info = ff.probe(path)
        except ff.VideoError as e:
            QMessageBox.warning(self, "Cannot open", str(e))
            return False
        self.path, self.info = path, info
        self.player.load(path)
        self.info_lb.setText(os.path.basename(path) + "\n" + info.summary())
        for b in (self.apply_b, self.use_b, self.save_b, self.exp_b):
            b.setEnabled(True)
        for s in (self.t_start, self.t_end, self.split_t):
            s.setRange(0, info.duration)
        self.t_start.setValue(0)
        self.t_end.setValue(0)
        self.split_t.setValue(round(info.duration / 2, 1))
        return True

    def add_overlay(self):
        t = self.ov_text.text().strip()
        if not t:
            return
        self.overlays.append(dict(
            text=t, pos=self.ov_pos.currentText().lower(), size=self.ov_size.value(),
            color=self.ov_color.currentText(), start=self.ov_from.value(), end=self.ov_to.value()))
        self.ov_list.addItem(f"{t}  ({self.ov_from.value():.1f}-{self.ov_to.value():.1f}s)")
        self.ov_text.clear()

    def del_overlay(self):
        r = self.ov_list.currentRow()
        if r >= 0:
            self.ov_list.takeItem(r)
            self.overlays.pop(r)

    def load_srt(self):
        p, _ = QFileDialog.getOpenFileName(self, "Subtitles", "", "Subtitles (*.srt)")
        if p:
            self.sub_path = p
            self.sub_lb.setText(os.path.basename(p))

    def load_music(self):
        p, _ = QFileDialog.getOpenFileName(self, "Audio file", "", "Audio (*.mp3 *.wav *.m4a *.aac *.ogg *.flac);;All files (*.*)")
        if p:
            self.music_path = p
            self.mus_lb.setText(os.path.basename(p))

    def record_voice(self):
        try:
            d = RecordAudioDialog(self)
            if d.exec() and d.result_path:
                self.music_path = d.result_path
                self.mus_lb.setText("Voice-over recorded")
        except Exception as e:
            QMessageBox.warning(self, "Recording", f"Could not record: {e}")

    def options(self) -> dict:
        o: dict = dict(start=self.t_start.value(), end=self.t_end.value() or None)
        c = self.crop.currentIndex()
        if c in (1, 2, 3, 4):
            o["crop"] = ("ratio",) + {1: (16, 9), 2: (9, 16), 3: (1, 1), 4: (4, 3)}[c]
        elif c == 5:
            o["crop"] = ("rect", self.cx.value(), self.cy.value(), self.cw.value(), self.ch.value())
        o["rotate"] = {0: 0, 1: 90, 2: 180, 3: 270}[self.rot.currentIndex()]
        o["flip_h"], o["flip_v"] = self.fh.isChecked(), self.fv.isChecked()
        o["speed"] = self.speed.value()
        o["brightness"] = self.br.value() / 100.0
        o["contrast"] = self.co.value() / 100.0
        o["saturation"] = self.sa.value() / 100.0
        o["overlays"] = list(self.overlays)
        if self.sub_path:
            o["subtitles"] = self.sub_path
        o["volume"] = self.vol.value() / 100.0
        o["mute"] = self.mute.isChecked()
        if self.music_path:
            o["music"] = dict(path=self.music_path, volume=self.mus_vol.value() / 100.0, offset=self.mus_off.value())
        return o

    def apply(self):
        if not self.path:
            return
        dst = paths.work_file(f"edit_{int(time.time() * 1000)}.mp4")
        o, src = self.options(), self.path
        try:
            from .. import textimg
            h = self.info.height if self.info else 360
            w = self.info.width if self.info else 640
            for ov in o["overlays"]:
                ov["png"] = textimg.render_text_png(
                    ov["text"], int(ov["size"] * h / 360), ov["color"], int(w * 0.9))
        except Exception as e:
            QMessageBox.warning(self, "Text overlay", f"Could not create the text image: {e}")
            return
        try:
            run_blocking(self, "Applying edits...", lambda: ff.apply_edits(src, dst, o))
        except Exception as e:
            QMessageBox.warning(self, "Edit failed", str(e))
            return
        self.reset_controls()
        self.open_video(dst)

    def reset_controls(self):
        self.crop.setCurrentIndex(0)
        self.rot.setCurrentIndex(0)
        self.fh.setChecked(False)
        self.fv.setChecked(False)
        self.speed.setValue(1.0)
        self.br.setValue(0)
        self.co.setValue(100)
        self.sa.setValue(100)
        self.overlays.clear()
        self.ov_list.clear()
        self.sub_path = self.music_path = ""
        self.sub_lb.setText("No subtitle file loaded")
        self.mus_lb.setText("No extra audio added")
        self.vol.setValue(100)
        self.mute.setChecked(False)

    def split(self):
        if not self.path:
            return
        a = paths.work_file(f"split_a_{int(time.time() * 1000)}.mp4")
        b = paths.work_file(f"split_b_{int(time.time() * 1000)}.mp4")
        t, src = self.split_t.value(), self.path
        try:
            run_blocking(self, "Splitting...", lambda: ff.split_at(src, t, a, b))
        except Exception as e:
            QMessageBox.warning(self, "Split failed", str(e))
            return
        for part, nm in ((a, "Part 1"), (b, "Part 2")):
            kept = self.ctx.keep_file(part, "split")
            self.ctx.db.add(name=f"{os.path.splitext(os.path.basename(src))[0][:30]} {nm}", style="Edited",
                            status="Completed", output_path=kept, thumb_path=self.ctx.make_thumb(kept))
        self.ctx.changed.emit()
        QMessageBox.information(self, "Split", "Two clips were saved to My Creations.")

    def save_creation(self):
        if not self.path:
            return
        kept = self.ctx.keep_file(self.path, "edit")
        self.ctx.db.add(name=os.path.splitext(os.path.basename(self.path))[0][:40] or "Edited video",
                        style="Edited", status="Completed", output_path=kept, thumb_path=self.ctx.make_thumb(kept))
        self.ctx.changed.emit()
        QMessageBox.information(self, "Saved", "Saved to My Creations.")

    def export(self):
        if self.path:
            from ..dialogs import ExportDialog
            ExportDialog(self.path, "edited", self).exec()

    def shutdown(self):
        self.player.clear()
