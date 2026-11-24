from __future__ import annotations

from dataclasses import dataclass, field


class ProviderError(Exception):
    def __init__(self, msg: str, retriable: bool = False):
        super().__init__(msg)
        self.retriable = retriable


class Cancelled(Exception):
    pass


@dataclass
class JobRequest:
    video_path: str
    style_id: str
    style_name: str
    style_prompt: str
    prompt: str = ""
    negative_prompt: str = ""
    intensity: int = 50
    auto_enhance: bool = True
    extra: dict = field(default_factory=dict)


# Every control the app knows about. A provider lists in `capabilities` only the ones
# it genuinely supports; the Studio shows exactly those and says which are missing.
ALL_CONTROLS = {
    "intensity": "Style Intensity",
    "face_consistency": "Face Consistency",
    "character_preservation": "Character Preservation",
    "motion_preservation": "Motion Preservation",
    "background_transform": "Background Transformation",
    "lighting": "Lighting Adjustment",
    "color_palette": "Color Palette",
    "detail": "Detail Enhancement",
    "temporal_smoothing": "Temporal Smoothing",
    "prompt": "Custom AI Prompt",
    "negative_prompt": "Negative Prompt",
    "auto_enhance": "AI Auto Enhancement",
}


class Provider:
    id = "base"
    name = "Base"
    is_demo = False
    max_seconds = 10.0
    max_bytes = 100 * 1024 * 1024
    capabilities: set = set()
    notes = ""

    def configured(self) -> bool:
        return True

    def run(self, req: JobRequest, report, cancelled) -> str:
        """Process the video. report(str) updates the status, cancelled() -> bool.
        Returns the path of the finished MP4. Raise ProviderError / Cancelled."""
        raise NotImplementedError
