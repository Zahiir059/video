"""Shared application state passed to every page."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from .config import LIB_DIR, Settings
from .db import Database
from .providers import make_provider


class Context(QObject):
    videoChanged = Signal(str)
    styleChanged = Signal(str)
    libraryChanged = Signal()
    themeChanged = Signal(str)
    providerChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings()
        self.db = Database()
        self.style_id: str = self.settings.get("style", "anime")
        self.video_path: str | None = None
        self.video_info = None
        self.navigate = lambda index: None
        self.studio = None
        self.editor = None

    @property
    def theme(self) -> str:
        return self.settings.get("theme", "dark")

    def provider(self):
        return make_provider(self.settings)

    def set_style(self, style_id: str) -> None:
        self.style_id = style_id
        self.settings.set("style", style_id)
        self.styleChanged.emit(style_id)

    def set_video(self, path: str | None, info) -> None:
        self.video_path, self.video_info = path, info
        self.videoChanged.emit(path or "")

    def store(self, src: str, sub: str) -> str:
        """Copy a file into the library (originals / outputs / edits / thumbs)."""
        ext = Path(src).suffix or ".mp4"
        dest = LIB_DIR / sub / (uuid.uuid4().hex[:12] + ext)
        shutil.copyfile(src, dest)
        return str(dest)

    def new_thumb_path(self) -> str:
        return str(LIB_DIR / "thumbs" / (uuid.uuid4().hex[:12] + ".jpg"))
