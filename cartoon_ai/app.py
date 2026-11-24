from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFileDialog, QFrame, QHBoxLayout, QMainWindow,
                               QMenu, QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from . import APP_NAME, __version__, art, paths
from .context import Ctx
from .dialogs import CompareDialog, RecordVideoDialog
from .pages.about import AboutPage
from .pages.creations import CreationsPage
from .pages.editor import EditorPage
from .pages.home import HomePage
from .pages.settings_page import SettingsPage
from .pages.studio import StudioPage
from .pages.styles_page import StylesPage
from .theme import stylesheet
from .widgets import button, fade_in, has_video_input, label

VIDEO_FILTER = ("Video files (*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.wmv *.flv *.mpg *.mpeg *.3gp);;"
                "All files (*.*)")
VIDEO_EXT = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".wmv", ".flv", ".mpg", ".mpeg", ".3gp")

NAV = [("⌂", "Home Dashboard"), ("✦", "AI Video Studio"), ("◈", "Animation Styles"),
       ("✂", "Video Editor"), ("▣", "My Creations"), ("⚙", "Settings"), ("ⓘ", "About")]


class MainWindow(QMainWindow):
    def __init__(self, ctx: Ctx):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(f"{APP_NAME}")
        self.resize(1280, 780)
        self.setMinimumSize(1180, 680)
        self.setAcceptDrops(True)
        self.setWindowIcon(QIcon(art.logo_pixmap(64)))

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # sidebar
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(220)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 18, 14, 14)
        sl.setSpacing(6)
        logo_row = QHBoxLayout()
        lg = label()
        lg.setPixmap(art.logo_pixmap(40))
        logo_row.addWidget(lg)
        nm = label("Cartoon AI")
        nm.setStyleSheet("font-size:20px;font-weight:800;")
        logo_row.addWidget(nm)
        logo_row.addStretch(1)
        sl.addLayout(logo_row)
        sl.addSpacing(16)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.nav_buttons = []
        for i, (ic, name) in enumerate(NAV):
            b = QPushButton(f"  {ic}   {name}")
            b.setObjectName("NavButton")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, i=i: self.go(i))
            self.group.addButton(b, i)
            self.nav_buttons.append(b)
            sl.addWidget(b)
        sl.addStretch(1)
        sl.addWidget(label(f"v{__version__}  |  local projects", "Sub"))
        root.addWidget(side)

        # right side
        right = QVBoxLayout()
        right.setSpacing(0)
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(60)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 18, 0)
        self.title = label("Home Dashboard", "SubHeading")
        hl.addWidget(self.title)
        hl.addStretch(1)
        self.badge = label()
        hl.addWidget(self.badge)
        prof = button("☺", "Icon")
        prof.setToolTip("Profile")
        prof.clicked.connect(self._profile)
        setb = button("⚙", "Icon", lambda: self.go(5))
        setb.setToolTip("Settings")
        hl.addWidget(prof)
        hl.addWidget(setb)
        right.addWidget(header)

        self.stack = QStackedWidget()
        self.home = HomePage(ctx, self)
        self.studio = StudioPage(ctx, self)
        self.styles = StylesPage(ctx, self)
        self.editor = EditorPage(ctx, self)
        self.creations = CreationsPage(ctx, self)
        self.settings = SettingsPage(ctx, self)
        self.about = AboutPage(ctx, self)
        for p in (self.home, self.studio, self.styles, self.editor, self.creations, self.settings, self.about):
            self.stack.addWidget(p)
        right.addWidget(self.stack, 1)
        root.addLayout(right, 1)

        self.apply_theme()
        self.update_badge()
        ctx.changed.connect(self.update_badge)
        self.go(0, animate=False)

    # ---- navigation ------------------------------------------------------------
    def go(self, i: int, animate: bool = True):
        self.stack.setCurrentIndex(i)
        self.nav_buttons[i].setChecked(True)
        self.title.setText(NAV[i][1])
        if animate:
            fade_in(self.stack.currentWidget())

    def open_studio(self, path: str | None = None):
        self.go(1)
        if path:
            self.studio.load_video(path)

    def open_editor(self, path: str):
        self.go(3)
        self.editor.open_video(path)

    def choose_style(self, sid: str):
        self.studio.set_style(sid)
        self.go(1)

    # ---- actions ---------------------------------------------------------------
    def pick_video(self):
        p, _ = QFileDialog.getOpenFileName(self, "Choose a video", "", VIDEO_FILTER)
        if p:
            self.open_studio(p)

    def record_video(self):
        if not has_video_input():
            QMessageBox.information(self, "Record video", "No camera was found on this PC.")
            return
        try:
            d = RecordVideoDialog(self)
            if d.exec() and d.result_path:
                self.open_studio(d.result_path)
        except Exception as e:
            QMessageBox.warning(self, "Record video", f"Recording is not available: {e}")

    def preview_project(self, pid: int):
        r = self.ctx.db.get(pid)
        if not r:
            return
        CompareDialog(r["original_path"], r["output_path"], self, title=r["name"]).exec()

    def edit_project(self, pid: int):
        r = self.ctx.db.get(pid)
        if not r:
            return
        src = r["output_path"] or r["original_path"]
        if src and os.path.exists(src):
            self.open_editor(src)
        else:
            QMessageBox.information(self, "Edit", "This project has no video file.")

    def _profile(self):
        m = QMenu(self)
        m.addAction("Local profile (no account needed)").setEnabled(False)
        m.addAction("Your projects stay on this PC").setEnabled(False)
        m.addSeparator()
        m.addAction("Open Settings", lambda: self.go(5))
        m.exec(self.cursor().pos())

    def apply_theme(self):
        QApplication.instance().setStyleSheet(stylesheet(self.ctx.dark))

    def update_badge(self):
        prov = self.ctx.active_provider()
        if prov.is_demo:
            self.badge.setText("DEMO MODE - no AI key")
            self.badge.setObjectName("DemoBadge")
        else:
            self.badge.setText("LIVE AI: " + prov.id.capitalize())
            self.badge.setObjectName("LiveBadge")
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)

    # ---- drag and drop ---------------------------------------------------------
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if p and p.lower().endswith(VIDEO_EXT):
                self.open_studio(p)
                return
        QMessageBox.information(self, "Drop a video", "That file does not look like a video.")

    def closeEvent(self, e):
        self.studio.shutdown()
        self.editor.shutdown()
        paths.clear_work()
        super().closeEvent(e)


def main(argv) -> int:
    if "--selftest" in argv and os.name != "nt" and not os.environ.get("DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    if "--selftest" in argv:
        from .selftest import run
        i = argv.index("--selftest")
        out = argv[i + 1] if len(argv) > i + 1 else "selftest.txt"
        return run(app, out)
    ctx = Ctx()
    win = MainWindow(ctx)
    win.show()
    return app.exec()
