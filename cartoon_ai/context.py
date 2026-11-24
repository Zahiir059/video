from __future__ import annotations

import os
import shutil
import time

from PySide6.QtCore import QObject, Signal

from . import ffmpeg_tools as ff
from . import paths
from .config import Config
from .db import Database
from .providers import DemoProvider, ReplicateProvider


class Ctx(QObject):
    changed = Signal()  # projects or settings changed

    def __init__(self) -> None:
        super().__init__()
        paths.ensure()
        paths.clear_work()
        self.cfg = Config()
        self.db = Database(paths.db_path())
        self.db.mark_interrupted()

    @property
    def dark(self) -> bool:
        return self.cfg.get("theme") != "light"

    def real_provider(self) -> ReplicateProvider:
        return ReplicateProvider(self.cfg)

    def active_provider(self):
        rep = self.real_provider()
        return rep if rep.configured() else DemoProvider()

    def keep_file(self, src: str, prefix: str) -> str:
        """Copy a working file into the permanent videos folder."""
        dst = str(paths.videos_dir() / f"{prefix}_{int(time.time() * 1000)}{os.path.splitext(src)[1] or '.mp4'}")
        shutil.copy2(src, dst)
        return dst

    def make_thumb(self, video: str) -> str:
        dst = str(paths.thumbs_dir() / f"t_{int(time.time() * 1000)}.jpg")
        return dst if ff.make_thumbnail(video, dst) else ""

    def delete_files(self, *files: str) -> None:
        for f in files:
            try:
                if f and os.path.isfile(f) and os.path.dirname(os.path.abspath(f)).startswith(str(paths.data_dir())):
                    os.remove(f)
            except OSError:
                pass
