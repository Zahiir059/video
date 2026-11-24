from __future__ import annotations

from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from .. import __version__
from ..widgets import card, label

TEXT = [
    ("What it is", "Cartoon AI turns short videos (up to 10 seconds) into cartoon and anime styles. "
                   "Editing, trimming, export and your library run on your PC with FFmpeg."),
    ("What needs the internet", "The AI transformation itself runs on a cloud service (Replicate by default) "
                                "and needs internet plus an API key you pay for. It cannot run offline."),
    ("Demo Mode", "With no key, the app applies a simple local colour filter and labels the result "
                  "'DEMO - not AI'. Never treat demo output as an AI result."),
    ("Honest limits", "Only controls that the connected model really supports are shown. The default model "
                      "supports a prompt and a closeness setting (Style Intensity). Face consistency, motion "
                      "preservation and similar options depend on the model and are not faked. Resolution "
                      "and aspect ratio on export are applied locally; the AI service decides the size of "
                      "the generated clip. Automatic subtitle generation is not included."),
    ("Privacy", "Projects stay on your PC. Your API key is stored in Windows Credential Manager. "
                "A video is uploaded only to the AI service when you press Generate."),
]


class AboutPage(QWidget):
    def __init__(self, ctx, win):
        super().__init__()
        self.setObjectName("Page")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        body = QWidget()
        body.setObjectName("Page")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(28, 22, 28, 28)
        lay.setSpacing(14)
        lay.addWidget(label("About Cartoon AI", "Heading"))
        lay.addWidget(label(f"Version {__version__}", "Sub"))
        for h, t in TEXT:
            c = card(False)
            cl = QVBoxLayout(c)
            cl.setContentsMargins(18, 14, 18, 14)
            cl.addWidget(label(h, "SubHeading"))
            cl.addWidget(label(t, "", wrap=True))
            lay.addWidget(c)
        lay.addStretch(1)
        scroll.setWidget(body)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
