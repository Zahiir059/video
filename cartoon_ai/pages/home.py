from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from ..styles_data import BY_ID, POPULAR
from ..widgets import HeroBanner, StyleCard, button, card, label, status_chip, thumb_label


class HomePage(QWidget):
    def __init__(self, ctx, win):
        super().__init__()
        self.setObjectName("Page")
        self.ctx, self.win = ctx, win
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        body = QWidget()
        body.setObjectName("Page")
        self.lay = QVBoxLayout(body)
        self.lay.setContentsMargins(28, 22, 28, 28)
        self.lay.setSpacing(18)
        scroll.setWidget(body)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # hero
        hero = QWidget()
        hero.setMinimumHeight(260)
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(0, 0, 0, 0)
        banner = HeroBanner()
        hl.addWidget(banner)
        txt = QVBoxLayout(banner)
        txt.setContentsMargins(36, 30, 36, 30)
        h1 = label("Turn Your Videos Into Art")
        h1.setStyleSheet("font-size:34px;font-weight:800;color:white;")
        h2 = label("Transform ordinary videos into extraordinary animations", wrap=True)
        h2.setStyleSheet("font-size:16px;color:rgba(255,255,255,0.88);")
        h2.setMaximumWidth(460)
        txt.addWidget(h1)
        txt.addWidget(h2)
        txt.addSpacing(10)
        b = button("Create Cartoon Video  →", "Hero", lambda: win.open_studio())
        b.setFixedWidth(250)
        txt.addWidget(b)
        txt.addStretch(1)
        self.lay.addWidget(hero)

        # quick actions
        self.lay.addWidget(label("Quick Actions", "SubHeading"))
        row = QHBoxLayout()
        row.setSpacing(14)
        for icon, title, sub, fn in (
            ("⬆", "Upload Video", "MP4, MOV and more", win.pick_video),
            ("●", "Record Video", "Use your webcam", win.record_video),
            ("✦", "Choose Animation Style", "15 styles", lambda: win.go(2)),
            ("▣", "My Creations", "Your library", lambda: win.go(4)),
        ):
            c = card()
            cl = QVBoxLayout(c)
            cl.setContentsMargins(18, 16, 18, 16)
            ic = label(icon)
            ic.setStyleSheet("font-size:26px;color:#8B5CF6;")
            cl.addWidget(ic)
            cl.addWidget(label(title, "SubHeading"))
            cl.addWidget(label(sub, "Sub"))
            cl.addWidget(button("Open", "", fn))
            row.addWidget(c)
        self.lay.addLayout(row)

        # popular styles
        self.lay.addWidget(label("Popular Styles", "SubHeading"))
        pr = QHBoxLayout()
        pr.setSpacing(14)
        for sid in POPULAR:
            sc = StyleCard(BY_ID[sid], small=True)
            sc.selected.connect(win.choose_style)
            pr.addWidget(sc)
        pr.addStretch(1)
        wrap = QWidget()
        wrap.setObjectName("Page")
        wrap.setLayout(pr)
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QScrollArea.NoFrame)
        sa.setFixedHeight(235)
        sa.setWidget(wrap)
        self.lay.addWidget(sa)

        # recent projects
        self.lay.addWidget(label("Recent Projects", "SubHeading"))
        self.recent = QVBoxLayout()
        self.recent.setSpacing(10)
        self.lay.addLayout(self.recent)
        self.lay.addStretch(1)
        ctx.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        while self.recent.count():
            it = self.recent.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        rows = self.ctx.db.list(limit=5)
        if not rows:
            self.recent.addWidget(label("No projects yet. Upload a video to create your first cartoon.", "Sub"))
            return
        for r in rows:
            c = card(shadow=False)
            h = QHBoxLayout(c)
            h.setContentsMargins(14, 10, 14, 10)
            h.addWidget(thumb_label(r["thumb_path"]))
            col = QVBoxLayout()
            col.addWidget(label(r["name"], "SubHeading"))
            col.addWidget(label(f"Style: {r['style'] or '-'}" + ("   |   DEMO (not AI)" if r["is_demo"] else ""), "Sub"))
            h.addLayout(col, 1)
            h.addWidget(status_chip(r["status"]))
            pid = r["id"]
            h.addWidget(button("Preview", "", lambda pid=pid: self.win.preview_project(pid)))
            h.addWidget(button("Edit", "", lambda pid=pid: self.win.edit_project(pid)))
            self.recent.addWidget(c)
