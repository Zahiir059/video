from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QMessageBox, QProgressBar,
                               QScrollArea, QSlider, QTextEdit, QVBoxLayout, QWidget)

from .. import art
from .. import ffmpeg_tools as ff
from ..dialogs import CompareDialog, ExportDialog, MAX_SECONDS, TrimDialog
from ..jobs import JobWorker
from ..providers import ALL_CONTROLS, JobRequest
from ..styles_data import BY_ID, STYLES
from ..widgets import Spinner, VideoPlayer, button, card, label


class StudioPage(QWidget):
    def __init__(self, ctx, win):
        super().__init__()
        self.setObjectName("Page")
        self.ctx, self.win = ctx, win
        self.source = ""
        self.info: ff.VideoInfo | None = None
        self.output = ""
        self.project_id = 0
        self.worker: JobWorker | None = None
        self.style_id = "anime"

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("Page")
        root = QVBoxLayout(body)
        root.setContentsMargins(28, 22, 28, 28)
        root.setSpacing(14)
        root.addWidget(label("AI Video Studio", "Heading"))
        self.banner = label("", wrap=True)
        root.addWidget(self.banner)

        cols = QHBoxLayout()
        cols.setSpacing(16)
        root.addLayout(cols)

        # ---- left: original -------------------------------------------------
        left = card(False)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(16, 14, 16, 14)
        ll.addWidget(label("1. Original video", "SubHeading"))
        self.drop = label("Drag and drop a video here\nor use the Upload button", "Drop")
        self.drop.setAlignment(Qt.AlignCenter)
        ll.addWidget(self.drop)
        self.player_in = VideoPlayer("No video selected", min_h=190)
        ll.addWidget(self.player_in)
        self.info_lb = label("", "Sub", wrap=True)
        ll.addWidget(self.info_lb)
        r1 = QHBoxLayout()
        r1.addWidget(button("Upload video", "Primary", win.pick_video))
        r1.addWidget(button("Record", "", win.record_video))
        ll.addLayout(r1)
        r2 = QHBoxLayout()
        self.trim_b = button("Trim", "", self.retrim)
        self.edit_b = button("Crop / Edit", "", self.send_to_editor)
        self.remove_b = button("Remove", "", self.remove_video)
        for b in (self.trim_b, self.edit_b, self.remove_b):
            b.setEnabled(False)
            r2.addWidget(b)
        ll.addLayout(r2)
        cols.addWidget(left, 1)

        # ---- middle: style + controls ---------------------------------------
        mid = card(False)
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(16, 14, 16, 14)
        ml.addWidget(label("2. Style and controls", "SubHeading"))
        self.style_pic = QFrame()
        self.pic_lb = label()
        pl = QVBoxLayout(self.style_pic)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.addWidget(self.pic_lb)
        ml.addWidget(self.style_pic, alignment=Qt.AlignHCenter)
        self.style_combo = QComboBox()
        for s in STYLES:
            self.style_combo.addItem(s["name"], s["id"])
        self.style_combo.currentIndexChanged.connect(self._combo)
        ml.addWidget(self.style_combo)
        self.style_desc = label("", "Sub", wrap=True)
        ml.addWidget(self.style_desc)
        self.controls = QVBoxLayout()
        ml.addLayout(self.controls)
        ml.addStretch(1)
        cols.addWidget(mid, 1)

        # ---- right: output --------------------------------------------------
        right = card(False)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(16, 14, 16, 14)
        rl.addWidget(label("3. Result", "SubHeading"))
        self.player_out = VideoPlayer("Your cartoon video will appear here", min_h=190)
        rl.addWidget(self.player_out)
        self.result_note = label("", "Sub", wrap=True)
        rl.addWidget(self.result_note)
        srow = QHBoxLayout()
        self.spin = Spinner(28)
        self.status = label("Ready.", "Sub", wrap=True)
        srow.addWidget(self.spin)
        srow.addWidget(self.status, 1)
        rl.addLayout(srow)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.setTextVisible(False)
        self.bar.hide()
        rl.addWidget(self.bar)
        self.gen_b = button("Generate cartoon video", "Primary", self.generate)
        self.gen_b.setEnabled(False)
        rl.addWidget(self.gen_b)
        self.cancel_b = button("Cancel job", "", self.cancel)
        self.cancel_b.hide()
        rl.addWidget(self.cancel_b)
        grid = QGridLayout()
        self.regen_b = button("Regenerate", "", self.generate)
        self.cmp_b = button("Compare", "", self.compare)
        self.fav_b = button("★ Favorite", "", self.favorite)
        self.exp_b = button("Export...", "", self.export)
        for i, b in enumerate((self.regen_b, self.cmp_b, self.fav_b, self.exp_b)):
            b.setEnabled(False)
            grid.addWidget(b, i // 2, i % 2)
        rl.addLayout(grid)
        cols.addWidget(right, 1)
        root.addStretch(1)
        scroll.setWidget(body)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.refresh_controls()
        self.set_style(self.style_id)
        ctx.changed.connect(self.refresh_controls)

    # ---- controls built from what the provider really supports ----------------
    def refresh_controls(self):
        prov = self.ctx.active_provider()
        if prov.is_demo:
            self.banner.setText(
                "DEMO MODE - no AI key is connected. Results here come from a plain local filter and are "
                "NOT AI generated. To get real AI transformations, open Settings and add a Replicate API key "
                "(internet connection required).")
            self.banner.setStyleSheet("background:#7C2D12;color:#FED7AA;padding:10px 14px;border-radius:10px;")
        else:
            self.banner.setText(f"Connected: {prov.name}. {prov.notes}")
            self.banner.setStyleSheet("background:#14532D;color:#BBF7D0;padding:10px 14px;border-radius:10px;")
        while self.controls.count():
            it = self.controls.takeAt(0)
            w = it.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        caps = prov.capabilities
        self.prompt_edit = self.neg_edit = self.intensity = self.enh = None
        if "prompt" in caps:
            self.controls.addWidget(label(ALL_CONTROLS["prompt"]))
            self.prompt_edit = QTextEdit()
            self.prompt_edit.setPlaceholderText("Optional: extra words, e.g. 'golden hour, soft smile'")
            self.prompt_edit.setFixedHeight(64)
            self.controls.addWidget(self.prompt_edit)
        if "negative_prompt" in caps:
            self.controls.addWidget(label(ALL_CONTROLS["negative_prompt"]))
            self.neg_edit = QTextEdit()
            self.neg_edit.setFixedHeight(48)
            self.controls.addWidget(self.neg_edit)
        if "intensity" in caps:
            self.int_lb = label("")
            self.controls.addWidget(self.int_lb)
            self.intensity = QSlider(Qt.Horizontal)
            self.intensity.setRange(0, 100)
            self.intensity.setValue(50)
            self.intensity.valueChanged.connect(self._int_text)
            self.controls.addWidget(self.intensity)
            self._int_text()
        if "auto_enhance" in caps:
            self.enh = QCheckBox("AI Auto Enhancement (adds quality words to the prompt)")
            self.enh.setChecked(True)
            self.controls.addWidget(self.enh)
        missing = [v for k, v in ALL_CONTROLS.items() if k not in caps]
        if missing:
            n = label("Not offered by the connected model (so not shown): " + ", ".join(missing) + ".", "Sub", wrap=True)
            self.controls.addWidget(n)

    def _int_text(self):
        v = self.intensity.value()
        mode = "stays close to the original" if v < 34 else "balanced" if v < 67 else "strongly reimagined"
        self.int_lb.setText(f"{ALL_CONTROLS['intensity']}: {v}  ({mode})")

    # ---- style ----------------------------------------------------------------
    def set_style(self, sid: str):
        if sid not in BY_ID:
            return
        self.style_id = sid
        s = BY_ID[sid]
        self.style_combo.blockSignals(True)
        self.style_combo.setCurrentIndex(self.style_combo.findData(sid))
        self.style_combo.blockSignals(False)
        self.pic_lb.setPixmap(art.style_pixmap(s, 250, 125))
        self.style_desc.setText(s["desc"])

    def _combo(self):
        self.set_style(self.style_combo.currentData())

    # ---- video input ----------------------------------------------------------
    def load_video(self, path: str) -> bool:
        try:
            info = ff.probe(path)
        except ff.VideoError as e:
            QMessageBox.warning(self, "Cannot use this file", str(e))
            return False
        prov = self.ctx.active_provider()
        if info.size_bytes > prov.max_bytes:
            QMessageBox.warning(self, "File too large",
                                f"This file is {info.size_bytes / 1048576:.0f} MB. The limit is "
                                f"{prov.max_bytes // 1048576} MB. Trim or compress it first.")
            return False
        if info.duration > MAX_SECONDS + 0.05:
            dlg = TrimDialog(info, self)
            if dlg.exec() != dlg.DialogCode.Accepted or not dlg.result_path:
                return False
            path = dlg.result_path
            try:
                info = ff.probe(path)
            except ff.VideoError as e:
                QMessageBox.warning(self, "Trim problem", str(e))
                return False
        self.source, self.info = path, info
        self.player_in.load(path)
        self.info_lb.setText(os.path.basename(path) + "\n" + info.summary())
        self.drop.hide()
        for b in (self.trim_b, self.edit_b, self.remove_b):
            b.setEnabled(True)
        self.gen_b.setEnabled(info.duration <= MAX_SECONDS + 0.05)
        self.status.setText("Ready. Choose a style and press Generate.")
        return True

    def remove_video(self):
        self.source, self.info = "", None
        self.player_in.clear("No video selected")
        self.info_lb.setText("")
        self.drop.show()
        for b in (self.trim_b, self.edit_b, self.remove_b, self.gen_b):
            b.setEnabled(False)

    def retrim(self):
        if not self.info:
            return
        dlg = TrimDialog(self.info, self)
        if dlg.exec() == dlg.DialogCode.Accepted and dlg.result_path:
            self.load_video(dlg.result_path)

    def send_to_editor(self):
        if self.source:
            self.win.open_editor(self.source)

    # ---- generate -------------------------------------------------------------
    def generate(self):
        if not self.source or not self.info:
            QMessageBox.information(self, "No video", "Upload a video first.")
            return
        if self.info.duration > MAX_SECONDS + 0.05:
            QMessageBox.warning(self, "Too long", "The selected segment is longer than 10 seconds. Trim it first.")
            return
        if self.worker and self.worker.isRunning():
            return
        prov = self.ctx.active_provider()
        s = BY_ID[self.style_id]
        req = JobRequest(
            video_path=self.source, style_id=s["id"], style_name=s["name"], style_prompt=s["prompt"],
            prompt=self.prompt_edit.toPlainText() if self.prompt_edit else "",
            negative_prompt=self.neg_edit.toPlainText() if self.neg_edit else "",
            intensity=self.intensity.value() if self.intensity else 50,
            auto_enhance=self.enh.isChecked() if self.enh else False)
        kept = self.ctx.keep_file(self.source, "orig")
        self.project_id = self.ctx.db.add(
            name=os.path.splitext(os.path.basename(self.source))[0][:40] or "Project",
            style=s["name"], status="Processing", original_path=kept,
            thumb_path=self.ctx.make_thumb(kept), provider=prov.id, is_demo=int(prov.is_demo),
            prompt=req.prompt)
        self.ctx.changed.emit()
        self.worker = JobWorker(prov, req, self)
        self.worker.status.connect(self.status.setText)
        self.worker.finished_ok.connect(self._ok)
        self.worker.failed.connect(self._fail)
        self.worker.cancelled_sig.connect(self._cancelled)
        self._busy(True)
        self.status.setText("Starting...")
        self.worker.start()

    def _busy(self, on: bool):
        self.gen_b.setEnabled(not on and bool(self.source))
        self.cancel_b.setVisible(on)
        self.bar.setVisible(on)
        if on:
            self.spin.start()
            for b in (self.regen_b, self.cmp_b, self.fav_b, self.exp_b):
                b.setEnabled(False)
        else:
            self.spin.stop()

    def _ok(self, path: str):
        prov = self.ctx.active_provider()
        out = self.ctx.keep_file(path, "out")
        self.output = out
        self.ctx.db.update(self.project_id, status="Completed", output_path=out,
                           thumb_path=self.ctx.make_thumb(out) or self.ctx.db.get(self.project_id)["thumb_path"])
        self.player_out.load(out)
        self._busy(False)
        for b in (self.regen_b, self.cmp_b, self.fav_b, self.exp_b):
            b.setEnabled(True)
        if prov.is_demo:
            self.status.setText("Demo preview finished. This is a simple local filter, NOT an AI result.")
            self.result_note.setText("DEMO - not AI generated.")
        else:
            self.status.setText("Done. Saved to My Creations.")
            self.result_note.setText(f"Generated by {prov.name}.")
        self.ctx.changed.emit()

    def _fail(self, msg: str, retriable: bool):
        self.ctx.db.update(self.project_id, status="Failed", error=msg)
        self._busy(False)
        self.gen_b.setText("Retry" if retriable else "Generate cartoon video")
        self.status.setText("Failed: " + msg + ("  (You can press Retry. Failed jobs are not kept as results.)" if retriable else ""))
        self.ctx.changed.emit()

    def _cancelled(self):
        self.ctx.db.update(self.project_id, status="Cancelled")
        self._busy(False)
        self.status.setText("Cancelled.")
        self.ctx.changed.emit()

    def cancel(self):
        if self.worker:
            self.worker.cancel()
            self.status.setText("Cancelling...")

    # ---- result actions -------------------------------------------------------
    def compare(self):
        if self.output:
            row = self.ctx.db.get(self.project_id)
            CompareDialog(row["original_path"] if row else self.source, self.output, self).exec()

    def favorite(self):
        if self.project_id:
            self.ctx.db.update(self.project_id, favorite=1)
            self.status.setText("Marked as favorite.")
            self.ctx.changed.emit()

    def export(self):
        if self.output:
            ExportDialog(self.output, "cartoon", self).exec()

    def shutdown(self):
        self.player_in.clear()
        self.player_out.clear()
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(4000)
