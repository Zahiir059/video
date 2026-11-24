from __future__ import annotations

import os
import time

from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QInputDialog, QLineEdit, QMessageBox, QScrollArea,
                               QVBoxLayout, QWidget)

from ..dialogs import CompareDialog, ExportDialog
from ..widgets import button, card, label, status_chip, thumb_label


class CreationsPage(QWidget):
    def __init__(self, ctx, win):
        super().__init__()
        self.setObjectName("Page")
        self.ctx, self.win = ctx, win
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 28)
        outer.addWidget(label("My Creations", "Heading"))
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by name or style...")
        self.search.textChanged.connect(self.refresh)
        self.flt = QComboBox()
        self.flt.addItems(["All", "Favorites", "Generated", "Originals"])
        self.flt.currentIndexChanged.connect(self.refresh)
        bar.addWidget(self.search, 1)
        bar.addWidget(self.flt)
        outer.addLayout(bar)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        body = QWidget()
        body.setObjectName("Page")
        self.list = QVBoxLayout(body)
        self.list.setSpacing(10)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        ctx.changed.connect(self.refresh)
        self.refresh()

    def refresh(self, *_):
        while self.list.count():
            it = self.list.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        rows = self.ctx.db.list(self.search.text(), self.flt.currentText())
        if not rows:
            self.list.addWidget(label("Nothing here yet.", "Sub"))
        for r in rows:
            c = card(shadow=False)
            h = QHBoxLayout(c)
            h.setContentsMargins(14, 10, 14, 10)
            h.addWidget(thumb_label(r["thumb_path"], 128, 72))
            col = QVBoxLayout()
            col.addWidget(label(("★ " if r["favorite"] else "") + r["name"], "SubHeading"))
            when = time.strftime("%d %b %Y %H:%M", time.localtime(r["created"]))
            demo = "   |   DEMO (not AI)" if r["is_demo"] else ""
            col.addWidget(label(f"Style: {r['style'] or '-'}   |   {when}{demo}", "Sub"))
            if r["error"] and r["status"] == "Failed":
                col.addWidget(label(r["error"][:120], "Sub"))
            h.addLayout(col, 1)
            h.addWidget(status_chip(r["status"]))
            pid = r["id"]
            h.addWidget(button("Preview", "", lambda pid=pid: self.win.preview_project(pid)))
            h.addWidget(button("★", "", lambda pid=pid: self.fav(pid)))
            h.addWidget(button("Rename", "", lambda pid=pid: self.rename(pid)))
            h.addWidget(button("Export", "", lambda pid=pid: self.export(pid)))
            h.addWidget(button("Edit", "", lambda pid=pid: self.win.edit_project(pid)))
            h.addWidget(button("Delete", "", lambda pid=pid: self.delete(pid)))
            self.list.addWidget(c)
        self.list.addStretch(1)

    def fav(self, pid):
        r = self.ctx.db.get(pid)
        if r:
            self.ctx.db.update(pid, favorite=0 if r["favorite"] else 1)
            self.ctx.changed.emit()

    def rename(self, pid):
        r = self.ctx.db.get(pid)
        if not r:
            return
        name, ok = QInputDialog.getText(self, "Rename", "New name:", text=r["name"])
        if ok and name.strip():
            self.ctx.db.update(pid, name=name.strip()[:60])
            self.ctx.changed.emit()

    def export(self, pid):
        r = self.ctx.db.get(pid)
        src = r and (r["output_path"] or r["original_path"])
        if not src or not os.path.exists(src):
            QMessageBox.information(self, "Export", "There is no video file for this project.")
            return
        ExportDialog(src, r["name"], self).exec()

    def delete(self, pid):
        r = self.ctx.db.get(pid)
        if not r:
            return
        if QMessageBox.question(self, "Delete", f"Delete '{r['name']}' and its video files?") != QMessageBox.Yes:
            return
        self.ctx.delete_files(r["original_path"], r["output_path"], r["thumb_path"])
        self.ctx.db.delete(pid)
        self.ctx.changed.emit()
