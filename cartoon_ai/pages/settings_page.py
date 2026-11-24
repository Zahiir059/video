from __future__ import annotations

import os

from PySide6.QtWidgets import (QComboBox, QFormLayout, QHBoxLayout, QLineEdit, QMessageBox, QPlainTextEdit,
                               QScrollArea, QVBoxLayout, QWidget)

from .. import paths, secrets_store
from ..providers import ProviderError
from ..widgets import button, card, label


class SettingsPage(QWidget):
    def __init__(self, ctx, win):
        super().__init__()
        self.setObjectName("Page")
        self.ctx, self.win = ctx, win
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        body = QWidget()
        body.setObjectName("Page")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(28, 22, 28, 28)
        lay.setSpacing(14)
        lay.addWidget(label("Settings", "Heading"))

        # appearance
        c1 = card(False)
        f1 = QVBoxLayout(c1)
        f1.setContentsMargins(18, 14, 18, 14)
        f1.addWidget(label("Appearance", "SubHeading"))
        self.theme = QComboBox()
        self.theme.addItems(["Dark mode", "Light mode"])
        self.theme.setCurrentIndex(0 if ctx.dark else 1)
        self.theme.currentIndexChanged.connect(self._theme)
        f1.addWidget(self.theme)
        lay.addWidget(c1)

        # AI service
        c2 = card(False)
        f2 = QVBoxLayout(c2)
        f2.setContentsMargins(18, 14, 18, 14)
        f2.addWidget(label("AI service (Replicate)", "SubHeading"))
        f2.addWidget(label(
            "Real video-to-video AI runs in the cloud, so it needs an internet connection and a paid API key. "
            "Without a key the app stays in Demo Mode (a plain local filter, clearly labelled, NOT AI).\n"
            "1) Create an account at replicate.com  2) Add billing  3) Copy your API token from "
            "replicate.com/account/api-tokens  4) Paste it below and press Save key.", "Sub", wrap=True))
        self.status = label("", "Chip")
        f2.addWidget(self.status)
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.Password)
        self.key.setPlaceholderText("Paste API token (r8_...)")
        f2.addWidget(self.key)
        row = QHBoxLayout()
        row.addWidget(button("Save key", "Primary", self.save_key))
        row.addWidget(button("Remove key", "", self.remove_key))
        row.addWidget(button("Test connection", "", self.test))
        row.addStretch(1)
        f2.addLayout(row)
        f2.addWidget(label("The key is kept in Windows Credential Manager, never in a file or in the app.", "Sub", wrap=True))
        form = QFormLayout()
        self.model = QLineEdit(str(ctx.cfg.get("model")))
        self.template = QPlainTextEdit(str(ctx.cfg.get("template")))
        self.template.setFixedHeight(80)
        form.addRow("Model (owner/name)", self.model)
        form.addRow("Input template (JSON)", self.template)
        f2.addLayout(form)
        f2.addWidget(label("Placeholders: {video} {prompt} {mode}. Check the model's API tab on replicate.com; "
                           "if its field names differ, edit the template. Default settings are untested "
                           "against a live account.", "Sub", wrap=True))
        f2.addWidget(button("Save model settings", "", self.save_model))
        lay.addWidget(c2)

        # storage
        c3 = card(False)
        f3 = QVBoxLayout(c3)
        f3.setContentsMargins(18, 14, 18, 14)
        f3.addWidget(label("Storage", "SubHeading"))
        f3.addWidget(label(f"Your projects are stored in:\n{paths.data_dir()}", "Sub", wrap=True))
        r3 = QHBoxLayout()
        r3.addWidget(button("Open folder", "", self.open_folder))
        r3.addWidget(button("Clear temporary files", "", self.clear_tmp))
        r3.addStretch(1)
        f3.addLayout(r3)
        lay.addWidget(c3)
        lay.addStretch(1)
        scroll.setWidget(body)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.refresh_status()

    def refresh_status(self):
        prov = self.ctx.real_provider()
        if prov.configured():
            self.status.setText("Key saved. Live AI mode.")
            self.status.setObjectName("ChipOk")
        else:
            self.status.setText("No key. Demo Mode.")
            self.status.setObjectName("ChipWarn")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def _theme(self):
        self.ctx.cfg.set("theme", "dark" if self.theme.currentIndex() == 0 else "light")
        self.win.apply_theme()

    def save_key(self):
        v = self.key.text().strip()
        if len(v) < 10:
            QMessageBox.warning(self, "API key", "That does not look like a valid key.")
            return
        try:
            secrets_store.set_key("replicate", v)
        except secrets_store.SecretError as e:
            QMessageBox.warning(self, "API key", str(e))
            return
        self.key.clear()
        self.refresh_status()
        self.ctx.changed.emit()
        self.win.update_badge()

    def remove_key(self):
        secrets_store.delete_key("replicate")
        self.refresh_status()
        self.ctx.changed.emit()
        self.win.update_badge()

    def save_model(self):
        import json
        try:
            json.loads(self.template.toPlainText())
        except Exception:
            QMessageBox.warning(self, "Template", "The input template is not valid JSON.")
            return
        self.ctx.cfg.set("model", self.model.text().strip())
        self.ctx.cfg.set("template", self.template.toPlainText().strip())
        self.refresh_status()
        self.ctx.changed.emit()
        self.win.update_badge()
        QMessageBox.information(self, "Saved", "Model settings saved.")

    def test(self):
        from ..jobs import run_blocking
        prov = self.ctx.real_provider()
        try:
            msg = run_blocking(self, "Contacting Replicate...", prov.test_connection)
            QMessageBox.information(self, "Connection", msg)
        except ProviderError as e:
            QMessageBox.warning(self, "Connection", str(e))
        except Exception as e:
            QMessageBox.warning(self, "Connection", f"Could not connect: {e}")

    def open_folder(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths.data_dir())))

    def clear_tmp(self):
        paths.clear_work()
        QMessageBox.information(self, "Temporary files", "Temporary files were cleared.")
