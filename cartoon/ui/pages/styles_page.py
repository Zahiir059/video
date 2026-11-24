from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QPushButton

from ... import styles as S
from ..cards import StyleCard
from ..widgets import PrimaryButton, label
from .base import Page


class StylesPage(Page):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        head = QHBoxLayout()
        head.addWidget(label("Animation Styles", "H1"))
        head.addStretch(1)
        go = PrimaryButton("Use selected style in AI Studio")
        go.clicked.connect(lambda: ctx.navigate(1))
        head.addWidget(go)
        self.lay.addLayout(head)
        self.lay.addWidget(label(
            "Each style is a tuned prompt recipe sent to the AI model. The artwork below is an illustration "
            "of the look, not a sample of AI output.", "Muted", True))
        self.current = label("", "Badge")
        self.lay.addWidget(self.current)
        grid = QGridLayout()
        grid.setSpacing(14)
        for i, st in enumerate(S.STYLES):
            c = StyleCard(ctx, st)
            c.chosen.connect(ctx.set_style)
            grid.addWidget(c, i // 3, i % 3)
        for c in range(3):
            grid.setColumnStretch(c, 1)
        self.lay.addLayout(grid)
        self.lay.addStretch(1)
        ctx.styleChanged.connect(self._upd)
        self._upd()

    def _upd(self, *_a) -> None:
        self.current.setText("Selected style: " + S.get(self.ctx.style_id).name)
