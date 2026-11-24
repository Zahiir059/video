from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (QComboBox, QGridLayout, QHBoxLayout, QInputDialog, QLineEdit, QMessageBox,
                               QPushButton, QVBoxLayout)

from ..cards import status_badge, thumb_label
from ..dialogs import CompareDialog, ExportDialog, PreviewDialog
from ..widgets import Card, label
from .base import Page, clear_layout

FILTERS = ["All", "Generated videos", "Original videos", "Edited videos", "Favorites"]


class CreationsPage(Page):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.lay.addWidget(label("My Creations", "H1"))
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by name, style or prompt...")
        self.search.textChanged.connect(self.refresh)
        self.filter = QComboBox()
        self.filter.addItems(FILTERS)
        self.filter.currentIndexChanged.connect(self.refresh)
        bar.addWidget(self.search, 1)
        bar.addWidget(self.filter)
        self.lay.addLayout(bar)
        self.grid = QGridLayout()
        self.grid.setSpacing(14)
        self.lay.addLayout(self.grid)
        self.empty = label("Nothing here yet.", "Muted")
        self.lay.addWidget(self.empty)
        self.lay.addStretch(1)
        ctx.libraryChanged.connect(self.refresh)
        self.refresh()

    def refresh(self, *_a) -> None:
        clear_layout(self.grid)
        mode = self.filter.currentText()
        rows = self.ctx.db.list(search=self.search.text().strip(), favorites=(mode == "Favorites"),
                                kind={"Generated videos": "ai", "Edited videos": "edit"}.get(mode))
        if mode == "Original videos":
            rows = [r for r in rows if r["original_path"] and Path(r["original_path"]).exists()]
        self.empty.setVisible(not rows)
        for i, r in enumerate(rows):
            self.grid.addWidget(self._card(r, mode == "Original videos"), i // 3, i % 3)
        for c in range(3):
            self.grid.setColumnStretch(c, 1)

    def _card(self, r, originals: bool) -> Card:
        pid = r["id"]
        path = r["original_path"] if originals else (r["output_path"] or r["original_path"])
        c = Card(shadow=True)
        v = QVBoxLayout(c)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(6)
        v.addWidget(thumb_label(r["thumb_path"] if originals else (r["out_thumb_path"] or r["thumb_path"]), 250, 140))
        v.addWidget(label(((r["name"] or "Untitled") + (" (original)" if originals else "")), "H2", True))
        line = QHBoxLayout()
        line.addWidget(label(r["style"] or "-", "Muted"))
        line.addWidget(status_badge(r))
        line.addStretch(1)
        v.addLayout(line)
        if r["status"] == "Failed" and r["error"]:
            v.addWidget(label(r["error"][:140], "Muted", True))
        b1, b2 = QHBoxLayout(), QHBoxLayout()
        ok = bool(path) and Path(path).exists()
        buttons = [
            (b1, "Preview", lambda: PreviewDialog(path, r["name"] or "Preview", self).exec(), ok),
            (b1, "Edit", lambda: self.ctx.editor.open(path), ok),
            (b1, "Export", lambda: ExportDialog(path, Path(path).stem, self).exec(), ok),
            (b2, "Unfavorite" if r["favorite"] else "Favorite", lambda: self._fav(pid, not r["favorite"]), True),
            (b2, "Rename", lambda: self._rename(pid, r["name"]), True),
            (b2, "Delete", lambda: self._delete(pid), True),
        ]
        if r["kind"] == "ai" and r["output_path"] and not originals:
            buttons.append((b2, "Compare", lambda: CompareDialog(r["original_path"], r["output_path"], self).exec(),
                            ok and Path(r["original_path"]).exists()))
        for lay, text, fn, enabled in buttons:
            b = QPushButton(text)
            b.setEnabled(bool(enabled))
            b.clicked.connect(lambda _=False, f=fn: f())
            lay.addWidget(b)
        v.addLayout(b1)
        v.addLayout(b2)
        return c

    def _fav(self, pid: int, on: bool) -> None:
        self.ctx.db.update(pid, favorite=1 if on else 0)
        self.ctx.libraryChanged.emit()

    def _rename(self, pid: int, old: str) -> None:
        name, ok = QInputDialog.getText(self, "Rename", "New name:", text=old or "")
        if ok and name.strip():
            self.ctx.db.update(pid, name=name.strip()[:80])
            self.ctx.libraryChanged.emit()

    def _delete(self, pid: int) -> None:
        r = self.ctx.db.get(pid)
        if not r:
            return
        if QMessageBox.question(self, "Delete", f"Delete '{r['name']}' and its files from the library?") != QMessageBox.Yes:
            return
        files = [r["output_path"], r["out_thumb_path"], r["thumb_path"]]
        if r["kind"] == "ai":
            files.append(r["original_path"])
        for f in files:
            if f:
                try:
                    Path(f).unlink(missing_ok=True)
                except OSError:
                    pass
        self.ctx.db.delete(pid)
        self.ctx.libraryChanged.emit()
