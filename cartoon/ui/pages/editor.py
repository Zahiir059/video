from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
                               QLineEdit, QMessageBox, QPushButton, QSlider, QTabWidget, QVBoxLayout, QWidget)

from ...config import AUDIO_EXTS, VIDEO_EXTS
from ...jobs import FuncWorker
from ...media import (EditSpec, MediaError, apply_edit, make_thumbnail, probe, split_at, tmp_path, validate_video)
from ..widgets import Card, PrimaryButton, Spinner, VideoPlayer, label
from .base import Page


def _slider(lo: int, hi: int, val: int) -> tuple[QSlider, QWidget]:
    s = QSlider(Qt.Horizontal)
    s.setRange(lo, hi)
    s.setValue(val)
    lb = label(str(val), "Muted")
    lb.setMinimumWidth(40)
    s.valueChanged.connect(lambda v: lb.setText(str(v)))
    box = QWidget()
    h = QHBoxLayout(box)
    h.setContentsMargins(0, 0, 0, 0)
    h.addWidget(s, 1)
    h.addWidget(lb)
    return s, box


class EditorPage(Page):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.src: str | None = None
        self.info = None
        self.subs: str | None = None
        self.music: str | None = None
        self.voice: str | None = None
        self.sfx: str | None = None
        self.worker: FuncWorker | None = None

        self.lay.addWidget(label("Video Editor", "H1"))
        self.lay.addWidget(label("Edits are made with FFmpeg and saved as a new video in My Creations. "
                                 "Several edits can be applied together; apply again to chain more.", "Muted", True))
        row = QHBoxLayout()
        row.setSpacing(16)
        left = Card()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(16, 14, 16, 14)
        self.player = VideoPlayer(min_height=300, placeholder="Open a video to start editing")
        ll.addWidget(self.player, 1)
        self.info_lbl = label("No video opened.", "Muted", True)
        ll.addWidget(self.info_lbl)
        b = QHBoxLayout()
        open_b = QPushButton("Open video...")
        open_b.clicked.connect(self.pick)
        studio_b = QPushButton("Use Studio video")
        studio_b.clicked.connect(lambda: ctx.video_path and self.open(ctx.video_path))
        b.addWidget(open_b)
        b.addWidget(studio_b)
        ll.addLayout(b)
        row.addWidget(left, 3)

        tabs = QTabWidget()
        tabs.addTab(self._tab_trim(), "Trim / Split")
        tabs.addTab(self._tab_geometry(), "Crop / Rotate")
        tabs.addTab(self._tab_speed_color(), "Speed / Color")
        tabs.addTab(self._tab_text(), "Text / Subtitles")
        tabs.addTab(self._tab_audio(), "Audio")
        row.addWidget(tabs, 3)
        self.lay.addLayout(row)

        act = QHBoxLayout()
        self.apply_btn = PrimaryButton("Apply edits and save")
        self.apply_btn.clicked.connect(self.apply)
        self.use_btn = QPushButton("Use result in AI Studio")
        self.use_btn.clicked.connect(self.use_in_studio)
        self.spin = Spinner(24)
        self.spin.hide()
        self.status = label("", "Muted", True)
        act.addWidget(self.apply_btn)
        act.addWidget(self.use_btn)
        act.addWidget(self.spin)
        act.addWidget(self.status, 1)
        self.lay.addLayout(act)
        self.lay.addStretch(1)
        self._enable(False)

    # ------------------------------------------------------------- tabs
    def _tab(self) -> tuple[QWidget, QFormLayout]:
        w = QWidget()
        f = QFormLayout(w)
        f.setContentsMargins(14, 14, 14, 14)
        f.setVerticalSpacing(12)
        return w, f

    def _tab_trim(self):
        w, f = self._tab()
        self.t_start = QDoubleSpinBox()
        self.t_end = QDoubleSpinBox()
        for s in (self.t_start, self.t_end):
            s.setDecimals(2)
            s.setRange(0, 36000)
            s.setSuffix(" s")
        sb = QPushButton("Use player position")
        sb.clicked.connect(lambda: self.t_start.setValue(self.player.position_ms() / 1000))
        eb = QPushButton("Use player position")
        eb.clicked.connect(lambda: self.t_end.setValue(self.player.position_ms() / 1000))
        f.addRow("Start", self._pair(self.t_start, sb))
        f.addRow("End", self._pair(self.t_end, eb))
        self.split_btn = QPushButton("Split at player position (saves 2 videos)")
        self.split_btn.clicked.connect(self.split)
        f.addRow(self.split_btn)
        return w

    def _pair(self, a, b) -> QWidget:
        box = QWidget()
        h = QHBoxLayout(box)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(a, 1)
        h.addWidget(b)
        return box

    def _tab_geometry(self):
        w, f = self._tab()
        self.cx, bx = _slider(0, 90, 0)
        self.cy, by = _slider(0, 90, 0)
        self.cw, bw = _slider(10, 100, 100)
        self.ch, bh = _slider(10, 100, 100)
        f.addRow("Crop left %", bx)
        f.addRow("Crop top %", by)
        f.addRow("Crop width %", bw)
        f.addRow("Crop height %", bh)
        self.rot = QComboBox()
        for t, v in (("None", 0), ("90 degrees clockwise", 90), ("180 degrees", 180), ("90 degrees counter-clockwise", 270)):
            self.rot.addItem(t, v)
        f.addRow("Rotate", self.rot)
        self.fh = QCheckBox("Flip horizontally (mirror)")
        self.fv = QCheckBox("Flip vertically")
        f.addRow(self.fh)
        f.addRow(self.fv)
        return w

    def _tab_speed_color(self):
        w, f = self._tab()
        self.speed = QDoubleSpinBox()
        self.speed.setRange(0.25, 4.0)
        self.speed.setSingleStep(0.25)
        self.speed.setValue(1.0)
        self.speed.setSuffix(" x")
        slow = QPushButton("Slow motion (0.5x)")
        slow.clicked.connect(lambda: self.speed.setValue(0.5))
        f.addRow("Speed", self._pair(self.speed, slow))
        self.bri, b1 = _slider(-100, 100, 0)
        self.con, b2 = _slider(50, 200, 100)
        self.sat, b3 = _slider(0, 300, 100)
        f.addRow("Brightness", b1)
        f.addRow("Contrast %", b2)
        f.addRow("Saturation %", b3)
        return w

    def _tab_text(self):
        w, f = self._tab()
        self.text = QLineEdit()
        self.text.setPlaceholderText("Text shown on the video")
        f.addRow("Text overlay", self.text)
        self.tpos = QComboBox()
        for t in ("bottom", "center", "top"):
            self.tpos.addItem(t.title(), t)
        f.addRow("Position", self.tpos)
        self.tsize, bs = _slider(16, 120, 40)
        f.addRow("Size", bs)
        self.tcol = QComboBox()
        for t in ("white", "yellow", "cyan", "pink", "black"):
            self.tcol.addItem(t.title(), t)
        f.addRow("Colour", self.tcol)
        self.subs_lbl = label("No subtitle file.", "Muted")
        sb = QPushButton("Choose .srt subtitle file...")
        sb.clicked.connect(self._pick_subs)
        f.addRow(self._pair(self.subs_lbl, sb))
        f.addRow(label("Automatic subtitle generation needs a speech-to-text service and is not included. "
                       "Import an .srt file instead.", "Muted", True))
        return w

    def _file_row(self, text: str, setter) -> tuple[QWidget, object]:
        lb = label("none", "Muted")
        btn = QPushButton(text)
        btn.clicked.connect(lambda: setter(lb))
        return self._pair(lb, btn), lb

    def _tab_audio(self):
        w, f = self._tab()
        self.mute = QCheckBox("Remove original audio")
        f.addRow(self.mute)
        self.vol, bv = _slider(0, 200, 100)
        f.addRow("Original volume %", bv)
        r1, _ = self._file_row("Add background music...", lambda lb: self._pick_audio("music", lb))
        f.addRow(r1)
        self.mvol, bm = _slider(0, 200, 50)
        f.addRow("Music volume %", bm)
        self.mstart = QDoubleSpinBox()
        self.mstart.setRange(0, 36000)
        self.mstart.setSuffix(" s")
        self.mdur = QDoubleSpinBox()
        self.mdur.setRange(0, 36000)
        self.mdur.setSuffix(" s  (0 = all)")
        f.addRow("Trim music: start", self.mstart)
        f.addRow("Trim music: length", self.mdur)
        r2, _ = self._file_row("Add voiceover file...", lambda lb: self._pick_audio("voice", lb))
        f.addRow(r2)
        r3, _ = self._file_row("Add sound effect...", lambda lb: self._pick_audio("sfx", lb))
        f.addRow(r3)
        self.sfx_at = QDoubleSpinBox()
        self.sfx_at.setRange(0, 36000)
        self.sfx_at.setSuffix(" s")
        f.addRow("Sound effect at", self.sfx_at)
        f.addRow(label("To make a voiceover, record it with Windows Sound Recorder and add the file here.",
                       "Muted", True))
        return w

    # ------------------------------------------------------------- file picking
    def _pick_subs(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Subtitles", self.ctx.settings.get("last_dir"), "Subtitles (*.srt)")
        if p:
            self.subs = p
            self.subs_lbl.setText(Path(p).name)

    def _pick_audio(self, which: str, lb) -> None:
        exts = " ".join("*" + e for e in sorted(AUDIO_EXTS | VIDEO_EXTS))
        p, _ = QFileDialog.getOpenFileName(self, "Choose audio", self.ctx.settings.get("last_dir"), f"Audio ({exts})")
        if p:
            setattr(self, which, p)
            lb.setText(Path(p).name)

    def pick(self) -> None:
        exts = " ".join("*" + e for e in sorted(VIDEO_EXTS))
        p, _ = QFileDialog.getOpenFileName(self, "Open video", self.ctx.settings.get("last_dir"), f"Videos ({exts})")
        if p:
            self.ctx.settings.set("last_dir", str(Path(p).parent))
            self.open(p)

    # ------------------------------------------------------------- state
    def _enable(self, on: bool) -> None:
        for b in (self.apply_btn, self.use_btn, self.split_btn):
            b.setEnabled(on)

    def open(self, path: str) -> None:
        try:
            info = validate_video(path)
        except MediaError as e:
            QMessageBox.warning(self, "Cannot open", str(e))
            return
        self.src, self.info = path, info
        self.player.set_source(path)
        self.info_lbl.setText(Path(path).name + "\n" + info.summary())
        self.t_start.setValue(0)
        self.t_end.setValue(info.duration)
        self._enable(True)
        self.status.setText("")
        self.ctx.navigate(3)

    def _spec(self) -> EditSpec:
        s = EditSpec()
        dur = self.info.duration
        s.trim_start = self.t_start.value()
        end = self.t_end.value()
        s.trim_end = end if 0 < end < dur - 0.02 else None
        x, y = self.cx.value() / 100, self.cy.value() / 100
        w, h = min(self.cw.value() / 100, 1 - x), min(self.ch.value() / 100, 1 - y)
        if (x, y, w, h) != (0, 0, 1, 1):
            s.crop = (x, y, w, h)
        s.rotate = self.rot.currentData()
        s.flip_h, s.flip_v = self.fh.isChecked(), self.fv.isChecked()
        s.speed = self.speed.value()
        s.brightness = self.bri.value() / 100
        s.contrast = self.con.value() / 100
        s.saturation = self.sat.value() / 100
        s.text, s.text_pos = self.text.text(), self.tpos.currentData()
        s.text_size, s.text_color = self.tsize.value(), self.tcol.currentData()
        s.subtitles = self.subs
        s.mute, s.volume = self.mute.isChecked(), self.vol.value() / 100
        s.music, s.music_volume = self.music, self.mvol.value() / 100
        s.music_start = self.mstart.value()
        s.music_dur = self.mdur.value() or None
        s.voice, s.sfx, s.sfx_at = self.voice, self.sfx, self.sfx_at.value()
        return s

    # ------------------------------------------------------------- actions
    def _busy(self, on: bool, msg: str = "") -> None:
        self._enable(not on and bool(self.src))
        self.spin.setVisible(on)
        if on:
            self.spin.start()
        else:
            self.spin.stop()
        self.status.setText(msg)

    def apply(self) -> None:
        if not self.src:
            return
        out = tmp_path(".mp4")
        spec = self._spec()
        self._busy(True, "Rendering with FFmpeg...")
        self.worker = FuncWorker(apply_edit, self.src, out, spec)
        self.worker.done.connect(lambda _r: self._saved([out], "Edited"))
        self.worker.failed.connect(self._failed)
        self.worker.start()

    def split(self) -> None:
        if not self.src:
            return
        t = self.player.position_ms() / 1000
        a, b = tmp_path(".mp4"), tmp_path(".mp4")
        self._busy(True, "Splitting...")
        self.worker = FuncWorker(split_at, self.src, t, a, b)
        self.worker.done.connect(lambda _r: self._saved([a, b], "Split"))
        self.worker.failed.connect(self._failed)
        self.worker.start()

    def _saved(self, outs: list[str], what: str) -> None:
        try:
            first = None
            for i, o in enumerate(outs):
                final = self.ctx.store(o, "edits")
                Path(o).unlink(missing_ok=True)
                thumb = self.ctx.new_thumb_path()
                make_thumbnail(final, thumb)
                suffix = f" (part {i + 1})" if len(outs) > 1 else ""
                self.ctx.db.add(name=f"{what} - {Path(self.src).stem}{suffix}"[:60], original_path=self.src,
                                output_path=final, thumb_path=thumb, out_thumb_path=thumb, style="-",
                                provider="ffmpeg", status="Completed", kind="edit")
                first = first or final
            self._busy(False, f"{what} video saved to My Creations.")
            self.ctx.libraryChanged.emit()
            if first:
                self.src, self.info = first, probe(first)
                self.player.set_source(first)
                self.info_lbl.setText(Path(first).name + "\n" + self.info.summary())
                self.t_start.setValue(0)
                self.t_end.setValue(self.info.duration)
        except Exception as e:
            self._failed(str(e))

    def _failed(self, msg: str) -> None:
        self._busy(False, "Failed.")
        QMessageBox.warning(self, "Edit failed", msg)

    def use_in_studio(self) -> None:
        if self.src and self.ctx.studio:
            self.ctx.navigate(1)
            self.ctx.studio.load_video(self.src)
