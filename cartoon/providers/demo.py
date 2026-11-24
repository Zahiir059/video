from __future__ import annotations

from ..media import MediaError, demo_stylize, tmp_path
from .base import Provider, ProviderError


class DemoProvider(Provider):
    id = "demo"
    name = "Demo Mode (no AI)"
    is_demo = True
    supports_prompt = False
    supports_negative = False
    capabilities = []
    description = ("DEMO MODE: no AI service is connected. The result is made by a simple local FFmpeg "
                   "edge/colour filter. It is NOT AI-generated and ignores the style and prompt.")

    def generate(self, video, style, prompt, negative, params, report, cancelled):
        report(10, "DEMO: applying a simple local filter (this is not AI)")
        out = tmp_path(".mp4")
        try:
            demo_stylize(video, out)
        except MediaError as e:
            raise ProviderError(str(e))
        if cancelled():
            raise ProviderError("Cancelled.")
        report(100, "DEMO result ready (not AI-generated)")
        return out
