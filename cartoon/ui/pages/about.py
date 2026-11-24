from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout

from ...config import APP_VERSION, MAX_SECONDS
from ..widgets import Card, label
from .base import Page


class AboutPage(Page):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.lay.addWidget(label("About Cartoon AI", "H1"))
        c = Card()
        v = QVBoxLayout(c)
        v.setContentsMargins(20, 18, 20, 18)
        v.setSpacing(10)
        v.addWidget(label(f"Version {APP_VERSION}", "Badge"))
        for title, text in [
            ("What it does",
             "Turns short real videos into cartoon and anime styles with a cloud AI video-to-video model, "
             "and includes an FFmpeg based video editor and a local library."),
            ("Honest limits",
             f"- AI transformation is limited to {MAX_SECONDS:.0f} seconds per video.\n"
             "- High-quality results need an internet connection and your own cloud AI account. "
             "Generation does not work offline.\n"
             "- Without an API key the app is in Demo Mode: the output comes from a plain FFmpeg filter and "
             "is not AI. It is always labelled as such.\n"
             "- Face identity, motion and background are preserved only as far as the chosen model manages. "
             "The app shows only the controls that the connected model actually supports.\n"
             "- Style preview pictures are illustrations painted by the app, not AI samples.\n"
             "- In-app camera recording and automatic subtitle generation are not included."),
            ("Privacy",
             "Videos stay on your PC. They are uploaded only when you press Generate in AI mode, and only to the "
             "service you connected. Your API token is kept in Windows Credential Manager. Temporary files are "
             "deleted when the app closes."),
            ("Built with", "Python, PySide6 (Qt), FFmpeg, SQLite, Replicate API."),
        ]:
            v.addWidget(label(title, "H2"))
            v.addWidget(label(text, "Muted", True))
        self.lay.addWidget(c)
        self.lay.addStretch(1)
