from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QMessageBox, QPushButton, QVBoxLayout

from ... import styles as S
from .. import theme
from ..cards import ActionCard, StyleCard, status_badge, status_text, thumb_label
from ..dialogs import PreviewDialog
from ..widgets import Card, HeroBanner, label
from .base import Page, clear_layout


class HomePage(Page):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        # ---- hero
        hero = HeroBanner()
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(36, 28, 36, 28)
        col = QVBoxLayout()
        col.setSpacing(10)
        badge = label("AI VIDEO STUDIO")
        badge.setStyleSheet("background:rgba(255,255,255,0.22); color:white; border-radius:10px; "
                            "padding:3px 12px; font-weight:700; letter-spacing:1px;")
        badge.setSizePolicy(badge.sizePolicy().horizontalPolicy(), badge.sizePolicy().verticalPolicy())
        h = label("Turn Your Videos Into Art", wrap=True)
        h.setStyleSheet("color:white; font-size:34px; font-weight:800; background:transparent;")
        d = label("Transform ordinary videos into extraordinary animations", wrap=True)
        d.setStyleSheet("color:rgba(255,255,255,0.92); font-size:16px; background:transparent;")
        btn = QPushButton("Create Cartoon Video")
        btn.setObjectName("HeroButton")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: ctx.navigate(1))
        row = QHBoxLayout()
        row.addWidget(badge)
        row.addStretch(1)
        col.addLayout(row)
        col.addWidget(h)
        col.addWidget(d)
        col.addSpacing(6)
        brow = QHBoxLayout()
        brow.addWidget(btn)
        brow.addStretch(1)
        col.addLayout(brow)
        col.addStretch(1)
        hl.addLayout(col, 5)
        hl.addStretch(4)
        self.lay.addWidget(hero)

        # ---- quick actions
        self.lay.addWidget(label("Quick Actions", "H2"))
        qa = QGridLayout()
        qa.setSpacing(14)
        items = [
            ("upload", "Upload Video", "MP4, MOV and more", theme.CYAN, self.upload),
            ("record", "Record Video", "Use Windows Camera, then upload", theme.PINK, self.record),
            ("styles", "Choose Animation Style", "15 styles", theme.VIOLET, lambda: ctx.navigate(2)),
            ("creations", "My Creations", "Your library", theme.BLUE, lambda: ctx.navigate(4)),
        ]
        for i, (ic, t, s, c, fn) in enumerate(items):
            card = ActionCard(ic, t, s, c)
            card.clicked.connect(fn)
            qa.addWidget(card, 0, i)
            qa.setColumnStretch(i, 1)
        self.lay.addLayout(qa)

        # ---- popular styles
        self.lay.addWidget(label("Popular Styles", "H2"))
        grid = QGridLayout()
        grid.setSpacing(14)
        for i, sid in enumerate(S.POPULAR):
            sc = StyleCard(ctx, S.get(sid))
            sc.chosen.connect(self.choose)
            grid.addWidget(sc, i // 3, i % 3)
        for c in range(3):
            grid.setColumnStretch(c, 1)
        self.lay.addLayout(grid)

        # ---- recent projects
        head = QHBoxLayout()
        head.addWidget(label("Recent Projects", "H2"))
        head.addStretch(1)
        more = QPushButton("View all")
        more.clicked.connect(lambda: ctx.navigate(4))
        head.addWidget(more)
        self.lay.addLayout(head)
        self.recent = QVBoxLayout()
        self.recent.setSpacing(10)
        self.lay.addLayout(self.recent)
        self.lay.addStretch(1)
        ctx.libraryChanged.connect(self.refresh)
        self.refresh()

    def choose(self, sid: str) -> None:
        self.ctx.set_style(sid)
        self.ctx.navigate(1)

    def upload(self) -> None:
        self.ctx.navigate(1)
        if self.ctx.studio:
            self.ctx.studio.pick_video()

    def record(self) -> None:
        QMessageBox.information(
            self, "Record Video",
            "In-app camera recording is not included in this version.\n\n"
            "Record with the Windows Camera app (or your phone), then use Upload Video.")

    def refresh(self) -> None:
        clear_layout(self.recent)
        rows = self.ctx.db.recent(4)
        if not rows:
            c = Card()
            cl = QVBoxLayout(c)
            cl.setContentsMargins(20, 18, 20, 18)
            cl.addWidget(label("No projects yet. Upload a video to create your first cartoon.", "Muted", True))
            self.recent.addWidget(c)
            return
        for r in rows:
            c = Card(shadow=True)
            cl = QHBoxLayout(c)
            cl.setContentsMargins(12, 10, 12, 10)
            cl.addWidget(thumb_label(r["out_thumb_path"] or r["thumb_path"], 140, 80))
            info = QVBoxLayout()
            info.addWidget(label(r["name"] or "Untitled", "H2"))
            line = QHBoxLayout()
            line.addWidget(label("Style: " + (r["style"] or "-"), "Muted"))
            line.addWidget(status_badge(r))
            line.addStretch(1)
            info.addLayout(line)
            cl.addLayout(info, 1)
            pv = QPushButton("Preview")
            ed = QPushButton("Edit")
            path = r["output_path"] or r["original_path"]
            pv.setEnabled(bool(path))
            ed.setEnabled(bool(path))
            pv.clicked.connect(lambda _=False, p=path, n=r["name"]: PreviewDialog(p, n or "Preview", self).exec())
            ed.clicked.connect(lambda _=False, p=path: self.ctx.editor.open(p))
            cl.addWidget(pv)
            cl.addWidget(ed)
            self.recent.addWidget(c)
