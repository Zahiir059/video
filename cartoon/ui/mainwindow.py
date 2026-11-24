from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QButtonGroup, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                               QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from ..config import APP_NAME
from . import theme
from .pages.about import AboutPage
from .pages.creations import CreationsPage
from .pages.editor import EditorPage
from .pages.home import HomePage
from .pages.settings_page import SettingsPage
from .pages.studio import StudioPage
from .pages.styles_page import StylesPage
from .widgets import IconButton

NAV = [("home", "Home Dashboard"), ("studio", "AI Video Studio"), ("styles", "Animation Styles"),
       ("editor", "Video Editor"), ("creations", "My Creations"), ("settings", "Settings"), ("about", "About")]


def logo_pixmap(size: int) -> QPixmap:
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, size * 2, size * 2)
    g.setColorAt(0, QColor(theme.PURPLE))
    g.setColorAt(0.6, QColor(theme.VIOLET))
    g.setColorAt(1, QColor(theme.PINK))
    p.setBrush(g)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(0, 0, size * 2, size * 2, size * 0.5, size * 0.5)
    s = theme.svg_pixmap("sparkle", "#FFFFFF", int(size * 0.62))
    off = (size * 2 - s.width()) // 2
    p.drawPixmap(off, off, s)
    p.end()
    pm.setDevicePixelRatio(2)
    return pm


class MainWindow(QMainWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(logo_pixmap(64)))
        self.resize(1320, 840)
        self.setMinimumSize(1100, 700)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # sidebar
        side = QWidget()
        side.setObjectName("Sidebar")
        side.setFixedWidth(238)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 18, 14, 14)
        sl.setSpacing(6)
        brand = QHBoxLayout()
        lg = QLabel()
        lg.setPixmap(logo_pixmap(40))
        lg.setFixedSize(40, 40)
        name = QLabel(APP_NAME)
        name.setObjectName("H2")
        brand.addWidget(lg)
        brand.addWidget(name, 1)
        sl.addLayout(brand)
        sl.addSpacing(16)
        self.group = QButtonGroup(self)
        self.nav_buttons: list[QPushButton] = []
        for i, (ic, text) in enumerate(NAV):
            b = QPushButton("  " + text)
            b.setObjectName("NavButton")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setIconSize(b.iconSize() * 1.0)
            self.group.addButton(b, i)
            self.nav_buttons.append(b)
            sl.addWidget(b)
        sl.addStretch(1)
        tip = QLabel("Videos stay on your PC.\nAI mode uploads only when you press Generate.")
        tip.setObjectName("Muted")
        tip.setWordWrap(True)
        sl.addWidget(tip)
        self.group.idClicked.connect(self.go)
        outer.addWidget(side)

        # right
        right = QVBoxLayout()
        right.setSpacing(0)
        header = QWidget()
        header.setObjectName("Header")
        header.setFixedHeight(60)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 18, 0)
        self.title = QLabel("Home Dashboard")
        self.title.setObjectName("H2")
        self.badge = QLabel("")
        hl.addWidget(self.title)
        hl.addSpacing(12)
        hl.addWidget(self.badge)
        hl.addStretch(1)
        self.theme_btn = IconButton("sun", "Toggle dark / light mode")
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.profile_btn = IconButton("user", "Profile")
        self.profile_btn.clicked.connect(lambda: QMessageBox.information(
            self, "Profile", "Cartoon AI works without an account.\nYour projects are stored locally on this PC."))
        self.settings_btn = IconButton("settings", "Settings")
        self.settings_btn.clicked.connect(lambda: self.go(5))
        for w in (self.theme_btn, self.profile_btn, self.settings_btn):
            hl.addWidget(w)
        right.addWidget(header)
        self.stack = QStackedWidget()
        right.addWidget(self.stack, 1)
        outer.addLayout(right, 1)

        # pages
        self.home = HomePage(ctx)
        self.studio = StudioPage(ctx)
        self.styles = StylesPage(ctx)
        self.editor = EditorPage(ctx)
        self.creations = CreationsPage(ctx)
        self.settings = SettingsPage(ctx)
        self.about = AboutPage(ctx)
        for pg in (self.home, self.studio, self.styles, self.editor, self.creations, self.settings, self.about):
            self.stack.addWidget(pg)
        ctx.studio, ctx.editor = self.studio, self.editor
        ctx.navigate = self.go
        ctx.themeChanged.connect(self.apply_theme)
        ctx.providerChanged.connect(self.update_badge)
        self.update_badge()
        self.apply_theme(ctx.theme)
        self.group.button(0).setChecked(True)

    def go(self, index: int) -> None:
        self.group.button(index).setChecked(True)
        self.stack.setCurrentIndex(index)
        self.title.setText(NAV[index][1])
        self.refresh_icons()

    def toggle_theme(self) -> None:
        self.ctx.settings.set("theme", "light" if self.ctx.theme == "dark" else "dark")
        self.ctx.themeChanged.emit(self.ctx.theme)

    def apply_theme(self, name: str) -> None:
        QApplication.instance().setStyleSheet(theme.build_qss(name))
        self.refresh_icons()

    def refresh_icons(self) -> None:
        pal = theme.palette(self.ctx.theme)
        for i, b in enumerate(self.nav_buttons):
            color = theme.CYAN if b.isChecked() else pal["muted"]
            b.setIcon(theme.icon(NAV[i][0], color, 20))
        self.theme_btn.icon_name = "sun" if self.ctx.theme == "dark" else "moon"
        for w in (self.theme_btn, self.profile_btn, self.settings_btn):
            w.set_color(pal["muted"])

    def update_badge(self) -> None:
        p = self.ctx.provider()
        self.badge.setObjectName("DemoBadge" if p.is_demo else "LiveBadge")
        self.badge.setText("DEMO MODE - not AI" if p.is_demo else "AI CONNECTED")
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)

    def closeEvent(self, e):
        for pl in (self.studio.in_player, self.studio.out_player, self.editor.player):
            pl.release()
        super().closeEvent(e)
