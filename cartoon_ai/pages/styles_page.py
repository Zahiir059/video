from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QScrollArea, QVBoxLayout, QWidget

from ..styles_data import STYLES
from ..widgets import StyleCard, label


class StylesPage(QWidget):
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
        lay.addWidget(label("Animation Styles", "Heading"))
        lay.addWidget(label("Pick a look. Your choice is sent to the AI model as a style description.", "Sub"))
        grid = QGridLayout()
        grid.setSpacing(16)
        cols = 3
        for i, s in enumerate(STYLES):
            sc = StyleCard(s)
            sc.selected.connect(win.choose_style)
            grid.addWidget(sc, i // cols, i % cols)
        grid.setColumnStretch(cols, 1)
        lay.addLayout(grid)
        lay.addStretch(1)
        scroll.setWidget(body)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
