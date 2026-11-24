from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QMessageBox,
                               QPlainTextEdit, QProgressBar, QPushButton, QSlider, QSpinBox, QStackedWidget,
                               QVBoxLayout, QWidget)

from ... import styles as S
from ...config import MAX_SECONDS, VIDEO_EXTS
from ...jobs import GenerateWorker
from ...media import MediaError, make_thumbnail, probe, validate_video
from ..cards import STATUS_COLORS
from ..dialogs import CompareDialog, ExportDialog, TrimDialog, make_segment
from ..widgets import Card, DropZone, PrimaryButton, Spinner, StyleArt, VideoPlayer, label
from .base import Page, clear_layout


class StudioPage(Page):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.worker: GenerateWorker | None = None
        self.project_id: int | None = None
        self.output_path: str | None = None
        self.last_args: tuple | None = None
        self.getters: dict = {}
        self.provider = ctx.provider()

        self.lay.addWidget(label("AI Video Studio", "H1"))
        self.banner = Card()
        bl = QHBoxLayout(self.banner)
        bl.setContentsMargins(14, 10, 14, 10)
        self.banner_text = label("", wrap=True)
        bl.addWidget(self.banner_text, 1)
        self.banner_btn = QPushButton("Connect AI service")
        self.banner_btn.clicked.connect(lambda: ctx.navigate(5))
        bl.addWidget(self.banner_btn)
        self.lay.addWidget(self.banner)

        # ------------------------------------------------ videos row
        row = QHBoxLayout()
        row.setSpacing(16)
        # original
        oc = Card()
        ol = QVBoxLayout(oc)
        ol.setContentsMargins(16, 14, 16, 14)
        ol.addWidget(label("1. Original video", "H2"))
        self.in_stack = QStackedWidget()
        self.drop = DropZone()
        self.drop.fileDropped.connect(self.load_video)
        self.drop.clicked.connect(self.pick_video)
        self.in_player = VideoPlayer(min_height=240)
        self.in_stack.addWidget(self.drop)
        self.in_stack.addWidget(self.in_player)
        ol.addWidget(self.in_stack, 1)
        self.info_lbl = label("No video selected.", "Muted", True)
        ol.addWidget(self.info_lbl)
        br = QHBoxLayout()
        self.replace_btn = QPushButton("Replace")
        self.remove_btn = QPushButton("Remove")
        self.edit_btn = QPushButton("Trim / Crop / Rotate...")
        self.sample_btn = QPushButton("Make a sample clip")
        self.replace_btn.clicked.connect(self.pick_video)
        self.remove_btn.clicked.connect(self.remove_video)
        self.edit_btn.clicked.connect(self.open_in_editor)
        self.sample_btn.clicked.connect(self.make_sample)
        for b in (self.replace_btn, self.remove_btn, self.edit_btn, self.sample_btn):
            br.addWidget(b)
        ol.addLayout(br)
        row.addWidget(oc, 1)
        # output
        pc = Card()
        pl = QVBoxLayout(pc)
        pl.setContentsMargins(16, 14, 16, 14)
        pl.addWidget(label("3. Cartoon result", "H2"))
        self.out_player = VideoPlayer(min_height=240, placeholder="Your cartoon video will appear here")
        pl.addWidget(self.out_player, 1)
        self.out_info = label("", "Muted", True)
        pl.addWidget(self.out_info)
        ob = QHBoxLayout()
        self.regen_btn = QPushButton("Regenerate")
        self.compare_btn = QPushButton("Compare / side by side")
        self.fav_btn = QPushButton("Save as favorite")
        self.export_btn = QPushButton("Export MP4...")
        self.regen_btn.clicked.connect(self.regenerate)
        self.compare_btn.clicked.connect(self.compare)
        self.fav_btn.clicked.connect(self.favorite)
        self.export_btn.clicked.connect(self.export)
        for b in (self.regen_btn, self.compare_btn, self.fav_btn, self.export_btn):
            b.setEnabled(False)
            ob.addWidget(b)
        pl.addLayout(ob)
        row.addWidget(pc, 1)
        self.lay.addLayout(row)

        # ------------------------------------------------ controls row
        row2 = QHBoxLayout()
        row2.setSpacing(16)
        cc = Card()
        cl = QVBoxLayout(cc)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.addWidget(label("2. Style and AI controls", "H2"))
        sr = QHBoxLayout()
        self.style_art_host = QVBoxLayout()
        sr.addLayout(self.style_art_host)
        sc = QVBoxLayout()
        self.style_name = label("", "H2")
        self.style_desc = label("", "Muted", True)
        ch = QPushButton("Change style")
        ch.clicked.connect(lambda: ctx.navigate(2))
        sc.addWidget(self.style_name)
        sc.addWidget(self.style_desc)
        sc.addWidget(ch)
        sc.addStretch(1)
        sr.addLayout(sc, 1)
        cl.addLayout(sr)
        cl.addWidget(label("Extra prompt (added to the style prompt)"))
        self.prompt = QPlainTextEdit()
        self.prompt.setFixedHeight(64)
        cl.addWidget(self.prompt)
        cl.addWidget(label("Negative prompt (things to avoid)"))
        self.negative = QPlainTextEdit()
        self.negative.setFixedHeight(52)
        cl.addWidget(self.negative)
        self.caps_host = QVBoxLayout()
        cl.addLayout(self.caps_host)
        self.caps_note = label("", "Muted", True)
        cl.addWidget(self.caps_note)
        row2.addWidget(cc, 3)

        rc = Card()
        rl = QVBoxLayout(rc)
        rl.setContentsMargins(16, 14, 16, 14)
        rl.addWidget(label("Generate", "H2"))
        self.gen_btn = PrimaryButton("Generate Cartoon Video")
        self.gen_btn.clicked.connect(self.generate)
        rl.addWidget(self.gen_btn)
        hb = QHBoxLayout()
        self.spinner = Spinner(28)
        self.spinner.hide()
        self.status = label("Ready.", "Muted", True)
        hb.addWidget(self.spinner)
        hb.addWidget(self.status, 1)
        rl.addLayout(hb)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        rl.addWidget(self.bar)
        b2 = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.retry_btn = QPushButton("Retry")
        self.cancel_btn.clicked.connect(self.cancel)
        self.retry_btn.clicked.connect(self.retry)
        self.cancel_btn.hide()
        self.retry_btn.hide()
        b2.addWidget(self.cancel_btn)
        b2.addWidget(self.retry_btn)
        rl.addLayout(b2)
        rl.addWidget(label("Nothing is sent anywhere until you press Generate. In AI mode your 10-second clip "
                           "is uploaded to the connected cloud service.", "Muted", True))
        rl.addStretch(1)
        row2.addWidget(rc, 2)
        self.lay.addLayout(row2)
        self.lay.addStretch(1)

        ctx.styleChanged.connect(lambda _s: self.refresh_style())
        ctx.providerChanged.connect(self.refresh_provider)
        self.refresh_style()
        self.refresh_provider()

    # --------------------------------------------------------------- style / provider
    def refresh_style(self) -> None:
        st = S.get(self.ctx.style_id)
        clear_layout(self.style_art_host)
        self.style_art_host.addWidget(StyleArt(st, 150, 90))
        self.style_name.setText(st.name)
        self.style_desc.setText(st.desc)

    def refresh_provider(self, force: bool = True) -> None:
        p = self.provider = self.ctx.provider()
        key = (p.id, getattr(p, "model", ""))
        if not force and key == getattr(self, "_prov_key", None):
            return
        self._prov_key = key
        if p.is_demo:
            self.banner_text.setText(
                "DEMO MODE - no AI service is connected. Results come from a simple local FFmpeg filter and "
                "are NOT AI-generated. Add an API key in Settings for real video-to-video AI (needs internet).")
            self.banner_btn.show()
            self.banner.setStyleSheet("#Card{background:rgba(180,83,9,0.25); border:1px solid #B45309; border-radius:12px;}")
        else:
            self.banner_text.setText(f"AI connected: {p.name}. Model: {self.ctx.settings.get('model')}. "
                                     "Generation runs in the cloud and needs internet; the provider may charge your account.")
            self.banner_btn.hide()
            self.banner.setStyleSheet("#Card{background:rgba(4,120,87,0.22); border:1px solid #047857; border-radius:12px;}")
        self.prompt.setEnabled(p.supports_prompt)
        self.negative.setEnabled(p.supports_negative)
        if not p.supports_prompt:
            self.prompt.setPlaceholderText("Not used in Demo Mode.")
            self.negative.setPlaceholderText("Not used in Demo Mode.")
        else:
            self.prompt.setPlaceholderText("e.g. a girl dancing in a neon street, vivid colours")
            self.negative.setPlaceholderText("e.g. blurry, extra limbs")
        self._build_caps()

    def _build_caps(self) -> None:
        clear_layout(self.caps_host)
        self.getters = {}
        for cap in self.provider.capabilities:
            self.caps_host.addWidget(label(cap.label))
            if cap.kind == "slider":
                s = QSlider(Qt.Horizontal)
                s.setRange(int(cap.minimum / cap.step), int(cap.maximum / cap.step))
                s.setValue(int(cap.default / cap.step))
                val = label(f"{cap.default:g}", "Muted")
                s.valueChanged.connect(lambda v, lb=val, st=cap.step: lb.setText(f"{v * st:g}"))
                h = QHBoxLayout()
                h.addWidget(s, 1)
                h.addWidget(val)
                self.caps_host.addLayout(h)
                self.getters[cap.key] = lambda s=s, st=cap.step: s.value() * st
            elif cap.kind == "int":
                sp = QSpinBox()
                sp.setRange(int(cap.minimum), int(cap.maximum))
                sp.setValue(int(cap.default))
                self.caps_host.addWidget(sp)
                self.getters[cap.key] = lambda sp=sp: sp.value()
            else:
                cb = QComboBox()
                for lbl, v in cap.choices:
                    cb.addItem(lbl, v)
                cb.setCurrentIndex(max(0, cb.findData(cap.default)))
                self.caps_host.addWidget(cb)
                self.getters[cap.key] = lambda cb=cb: cb.currentData()
            if cap.help:
                self.caps_host.addWidget(label(cap.help, "Muted", True))
        if self.provider.is_demo:
            self.caps_note.setText("Controls such as style intensity appear here only when a connected AI model "
                                   "really supports them.")
        else:
            self.caps_note.setText("Only controls supported by this model are shown. It has no face-consistency, "
                                   "motion or lighting inputs, so those are not offered.")

    # --------------------------------------------------------------- input video
    def pick_video(self) -> None:
        exts = " ".join("*" + e for e in sorted(VIDEO_EXTS))
        path, _ = QFileDialog.getOpenFileName(self, "Choose a video", self.ctx.settings.get("last_dir"),
                                              f"Videos ({exts});;All files (*.*)")
        if path:
            self.ctx.settings.set("last_dir", str(Path(path).parent))
            self.load_video(path)

    def load_video(self, path: str) -> None:
        try:
            info = validate_video(path)
        except MediaError as e:
            QMessageBox.warning(self, "Cannot use this video", str(e))
            return
        if info.duration > MAX_SECONDS + 0.05:
            dlg = TrimDialog(info, self)
            if dlg.exec() != dlg.Accepted:
                return
            try:
                seg = make_segment(info, dlg.start())
                info = probe(seg)
            except MediaError as e:
                QMessageBox.warning(self, "Trim failed", str(e))
                return
        self.ctx.set_video(info.path, info)
        self.show_video()

    def show_video(self) -> None:
        info = self.ctx.video_info
        if not self.ctx.video_path or info is None:
            self.in_player.set_source(None)
            self.in_stack.setCurrentIndex(0)
            self.info_lbl.setText("No video selected.")
        else:
            self.in_player.set_source(self.ctx.video_path)
            self.in_stack.setCurrentIndex(1)
            self.info_lbl.setText(info.summary())
        has = bool(self.ctx.video_path)
        for b in (self.replace_btn, self.remove_btn, self.edit_btn):
            b.setEnabled(has)
        self.gen_btn.setEnabled(has and not self._running())

    def remove_video(self) -> None:
        self.ctx.set_video(None, None)
        self.show_video()

    def open_in_editor(self) -> None:
        if self.ctx.video_path and self.ctx.editor:
            self.ctx.editor.open(self.ctx.video_path)

    def make_sample(self) -> None:
        from ...media import make_sample_clip, tmp_path
        out = tmp_path(".mp4")
        try:
            make_sample_clip(out)
        except MediaError as e:
            QMessageBox.warning(self, "Sample clip", str(e))
            return
        self.load_video(out)

    # --------------------------------------------------------------- generate
    def _running(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def generate(self) -> None:
        info = self.ctx.video_info
        if not self.ctx.video_path or info is None:
            QMessageBox.information(self, "No video", "Upload a video first.")
            return
        if info.duration > MAX_SECONDS + 0.05:
            QMessageBox.warning(self, "Too long", "The AI limit is 10 seconds. Trim the video first.")
            return
        st = S.get(self.ctx.style_id)
        extra = self.prompt.toPlainText().strip()
        prompt = st.prompt + (", " + extra if extra else "")
        neg = st.negative
        eneg = self.negative.toPlainText().strip()
        if eneg:
            neg += ", " + eneg
        params = {k: g() for k, g in self.getters.items()}
        self.last_args = (self.ctx.video_path, st, prompt, neg, params)
        self._start(*self.last_args)

    def regenerate(self) -> None:
        self.generate()

    def retry(self) -> None:
        if self.last_args:
            self._start(*self.last_args)

    def _start(self, video, st, prompt, neg, params) -> None:
        if self._running():
            return
        prov = self.ctx.provider()
        self.provider = prov
        try:
            orig = self.ctx.store(video, "originals")
            othumb = self.ctx.new_thumb_path()
            make_thumbnail(orig, othumb)
            self.project_id = self.ctx.db.add(
                name=f"{st.name} - {Path(video).stem}"[:60], original_path=orig, thumb_path=othumb,
                style=st.name, prompt=prompt, negative=neg, provider=prov.id, status="Processing",
                params=params, kind="ai")
        except Exception as e:
            QMessageBox.warning(self, "Could not start", str(e))
            return
        self.ctx.libraryChanged.emit()
        self._ui_running(True)
        self.status.setText("Starting..." if not prov.is_demo else "DEMO: starting local filter...")
        self.worker = GenerateWorker(prov, video, st, prompt, neg, params, self)
        self.worker.progress.connect(self._progress)
        self.worker.succeeded.connect(self._done)
        self.worker.failed.connect(self._failed)
        self.worker.start()

    def cancel(self) -> None:
        if self.worker:
            self.worker.cancel()
            self.status.setText("Cancelling...")

    def _ui_running(self, on: bool) -> None:
        self.gen_btn.setEnabled(not on and bool(self.ctx.video_path))
        self.cancel_btn.setVisible(on)
        if on:
            self.retry_btn.hide()
            self.spinner.start()
            self.bar.setRange(0, 100)
            self.bar.setValue(0)
            self.out_player.set_source(None)
            self.out_player.set_placeholder("Generating... please wait")
            for b in (self.regen_btn, self.compare_btn, self.fav_btn, self.export_btn):
                b.setEnabled(False)
        else:
            self.spinner.stop()

    def _progress(self, pct: int, msg: str) -> None:
        self.status.setText(msg)
        if pct < 0:
            self.bar.setRange(0, 0)
        else:
            self.bar.setRange(0, 100)
            self.bar.setValue(pct)

    def _done(self, tmp_out: str) -> None:
        try:
            final = self.ctx.store(tmp_out, "outputs")
            Path(tmp_out).unlink(missing_ok=True)
            thumb = self.ctx.new_thumb_path()
            make_thumbnail(final, thumb)
            self.ctx.db.update(self.project_id, output_path=final, out_thumb_path=thumb, status="Completed")
        except Exception as e:
            self._failed("Could not save the result: " + str(e), False)
            return
        self.output_path = final
        self._ui_running(False)
        self.bar.setRange(0, 100)
        self.bar.setValue(100)
        demo = self.provider.is_demo
        self.status.setText("DEMO result ready (not AI-generated)." if demo else "Finished. Saved to My Creations.")
        self.out_player.set_source(final)
        self.out_info.setText("DEMO output - made by a plain FFmpeg filter, NOT by AI." if demo
                              else "AI-generated by " + self.provider.name + ".")
        for b in (self.regen_btn, self.compare_btn, self.fav_btn, self.export_btn):
            b.setEnabled(True)
        self.fav_btn.setText("Save as favorite")
        self.ctx.libraryChanged.emit()

    def _failed(self, msg: str, retryable: bool) -> None:
        self._ui_running(False)
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        cancelled = msg.startswith("Cancelled")
        if self.project_id:
            self.ctx.db.update(self.project_id, status="Failed", error=msg)
        self.ctx.libraryChanged.emit()
        self.status.setText("Cancelled." if cancelled else "Failed: " + msg)
        self.out_player.set_placeholder("Cancelled." if cancelled else "Generation failed. See the message on the right.")
        self.retry_btn.show()
        if not cancelled:
            QMessageBox.warning(self, "Generation failed",
                                msg + ("\n\nThis looks temporary - press Retry." if retryable else ""))

    # --------------------------------------------------------------- output actions
    def compare(self) -> None:
        if self.ctx.video_path and self.output_path:
            CompareDialog(self.ctx.video_path, self.output_path, self).exec()

    def favorite(self) -> None:
        if self.project_id:
            self.ctx.db.update(self.project_id, favorite=1)
            self.fav_btn.setText("Saved to favorites")
            self.ctx.libraryChanged.emit()

    def export(self) -> None:
        if self.output_path:
            ExportDialog(self.output_path, Path(self.output_path).stem, self).exec()

    def showEvent(self, e):
        super().showEvent(e)
        self.refresh_provider(force=False)
