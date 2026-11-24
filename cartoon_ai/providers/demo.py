from __future__ import annotations

import time

from .. import ffmpeg_tools as ff
from .. import paths
from .base import Cancelled, JobRequest, Provider, ProviderError


class DemoProvider(Provider):
    """Used only when no AI key is configured. It applies a plain local filter so you can
    see the app flow. It is NOT AI and the app labels every result as DEMO."""

    id = "demo"
    name = "Demo Mode (no AI key)"
    is_demo = True
    capabilities: set = set()
    notes = "Local filter only - not AI generated."

    def __init__(self) -> None:
        self.label_png = None
        try:  # built on the GUI thread (Qt drawing); the label says this is not AI
            from .. import textimg
            self.label_png = textimg.render_text_png(
                "DEMO - local filter, NOT AI", 22, "white", 420, box_color="#EC4899", box_alpha=230,
                dst=paths.work_file("demo_label.png"))
        except Exception:
            self.label_png = None

    def run(self, req: JobRequest, report, cancelled) -> str:
        report("DEMO MODE: applying a simple local filter (this is NOT AI)...")
        time.sleep(0.6)
        if cancelled():
            raise Cancelled()
        dst = paths.work_file(f"demo_{int(time.time() * 1000)}.mp4")
        try:
            return ff.demo_filter(req.video_path, dst, self.label_png)
        except ff.VideoError as e:
            raise ProviderError(str(e))
