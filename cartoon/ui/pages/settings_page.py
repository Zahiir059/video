from __future__ import annotations

import shutil

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit, QMessageBox, QPushButton, QVBoxLayout

from ...config import DEFAULT_MODEL, LIB_DIR, TMP_DIR, delete_api_key, get_api_key, set_api_key
from ...jobs import FuncWorker
from ..widgets import Card, PrimaryButton, label
from .base import Page


class SettingsPage(Page):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.worker = None
        self.lay.addWidget(label("Settings", "H1"))

        # appearance
        c = Card()
        v = QVBoxLayout(c)
        v.setContentsMargins(18, 16, 18, 16)
        v.addWidget(label("Appearance", "H2"))
        self.theme_btn = QPushButton()
        self.theme_btn.clicked.connect(self.toggle_theme)
        v.addWidget(self.theme_btn)
        self.lay.addWidget(c)

        # AI provider
        c = Card()
        v = QVBoxLayout(c)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(8)
        v.addWidget(label("AI service (Replicate)", "H2"))
        self.state = label("", "Badge")
        v.addWidget(self.state)
        v.addWidget(label(
            "Real video-to-video AI runs in the cloud. You need internet and your own Replicate account "
            "(replicate.com > Account > API tokens). Replicate bills your account for each generation. "
            "Without a key the app stays in Demo Mode, which uses a plain local filter and is NOT AI.", "Muted", True))
        v.addWidget(label("API token"))
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.Password)
        self.key.setPlaceholderText("r8_...   (stored in Windows Credential Manager, never in a file)")
        v.addWidget(self.key)
        row = QHBoxLayout()
        save = PrimaryButton("Save key")
        save.clicked.connect(self.save_key)
        test = QPushButton("Test connection")
        test.clicked.connect(self.test)
        rm = QPushButton("Remove key")
        rm.clicked.connect(self.remove_key)
        for b in (save, test, rm):
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        v.addWidget(label("Model (owner/name)"))
        self.model = QLineEdit(ctx.settings.get("model", DEFAULT_MODEL))
        v.addWidget(self.model)
        mrow = QHBoxLayout()
        ms = QPushButton("Save model")
        ms.clicked.connect(self.save_model)
        mr = QPushButton("Reset to default")
        mr.clicked.connect(lambda: (self.model.setText(DEFAULT_MODEL), self.save_model()))
        mrow.addWidget(ms)
        mrow.addWidget(mr)
        mrow.addStretch(1)
        v.addLayout(mrow)
        v.addWidget(label("The Studio controls match the default model. Another model may ignore or reject them.",
                          "Muted", True))
        self.force = QCheckBox("Force Demo Mode (never contact the AI service)")
        self.force.setChecked(bool(ctx.settings.get("force_demo", False)))
        self.force.toggled.connect(self.set_force)
        v.addWidget(self.force)
        self.msg = label("", "Muted", True)
        v.addWidget(self.msg)
        self.lay.addWidget(c)

        # storage
        c = Card()
        v = QVBoxLayout(c)
        v.setContentsMargins(18, 16, 18, 16)
        v.addWidget(label("Storage", "H2"))
        v.addWidget(label("Your library: " + str(LIB_DIR), "Muted", True))
        row = QHBoxLayout()
        o = QPushButton("Open library folder")
        o.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(LIB_DIR))))
        t = QPushButton("Clear temporary files")
        t.clicked.connect(self.clear_tmp)
        row.addWidget(o)
        row.addWidget(t)
        row.addStretch(1)
        v.addLayout(row)
        self.lay.addWidget(c)
        self.lay.addStretch(1)
        self.update_state()

    def update_state(self) -> None:
        p = self.ctx.provider()
        self.state.setText("DEMO MODE (no AI)" if p.is_demo else "AI connected: " + p.name)
        has = bool(get_api_key())
        self.key.setPlaceholderText(("A key is stored. Paste a new one to replace it." if has
                                     else "r8_...   (stored in Windows Credential Manager, never in a file)"))
        icon = "sun" if self.ctx.theme == "dark" else "moon"
        self.theme_btn.setText("Switch to Light Mode" if self.ctx.theme == "dark" else "Switch to Dark Mode")

    def toggle_theme(self) -> None:
        self.ctx.settings.set("theme", "light" if self.ctx.theme == "dark" else "dark")
        self.ctx.themeChanged.emit(self.ctx.theme)
        self.update_state()

    def save_key(self) -> None:
        k = self.key.text().strip()
        if not k:
            self.msg.setText("Paste your API token first.")
            return
        ok, m = set_api_key(k)
        self.msg.setText(m)
        if ok:
            self.key.clear()
        self.ctx.providerChanged.emit()
        self.update_state()

    def remove_key(self) -> None:
        delete_api_key()
        self.msg.setText("API key removed. The app is back in Demo Mode unless REPLICATE_API_TOKEN is set.")
        self.ctx.providerChanged.emit()
        self.update_state()

    def save_model(self) -> None:
        self.ctx.settings.set("model", self.model.text().strip() or DEFAULT_MODEL)
        self.msg.setText("Model saved.")
        self.ctx.providerChanged.emit()

    def set_force(self, on: bool) -> None:
        self.ctx.settings.set("force_demo", on)
        self.ctx.providerChanged.emit()
        self.update_state()

    def test(self) -> None:
        p = self.ctx.provider()
        if p.is_demo:
            self.msg.setText("Demo Mode is active - save an API key (and untick Force Demo) to test the AI service.")
            return
        self.msg.setText("Testing...")
        self.worker = FuncWorker(p.test_connection)
        self.worker.done.connect(lambda m: self.msg.setText(str(m)))
        self.worker.failed.connect(lambda m: self.msg.setText("Failed: " + m))
        self.worker.start()

    def clear_tmp(self) -> None:
        n = 0
        for f in TMP_DIR.glob("*"):
            try:
                f.unlink()
                n += 1
            except OSError:
                pass
        QMessageBox.information(self, "Temporary files", f"Removed {n} temporary file(s).")
