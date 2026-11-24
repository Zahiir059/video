"""Text -> transparent PNG (drawn with Qt). Used for text overlays and the DEMO label, so we do
not depend on FFmpeg's drawtext filter (the bundled FFmpeg may not include it). Must run on the
GUI thread."""
from __future__ import annotations

import time

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QImage, QPainter

from . import paths

COLORS = {"white": "#FFFFFF", "yellow": "#FDE047", "cyan": "#22D3EE", "pink": "#F472B6"}


def render_text_png(text: str, font_px: int, color: str = "white", max_width: int = 900,
                    box_color: str = "#000000", box_alpha: int = 125, dst: str | None = None) -> str:
    font = QFont()
    font.setPixelSize(max(10, int(font_px)))
    font.setBold(True)
    pad = max(8, font_px // 3)
    fm = QFontMetrics(font)
    avail = max(60, int(max_width) - 2 * pad)
    rect = fm.boundingRect(0, 0, avail, 10000, int(Qt.TextWordWrap | Qt.AlignCenter), text)
    w, h = rect.width() + 2 * pad, rect.height() + 2 * pad
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    bc = QColor(box_color)
    bc.setAlpha(box_alpha)
    p.setPen(Qt.NoPen)
    p.setBrush(bc)
    p.drawRoundedRect(QRectF(0, 0, w, h), pad * 0.8, pad * 0.8)
    p.setFont(font)
    p.setPen(QColor(COLORS.get(color, color)))
    p.drawText(QRectF(pad, pad, rect.width(), rect.height()), int(Qt.TextWordWrap | Qt.AlignCenter), text)
    p.end()
    dst = dst or paths.work_file(f"text_{int(time.time() * 1000)}_{abs(hash(text)) % 10000}.png")
    if not img.save(dst, "PNG"):
        raise RuntimeError("Could not create the text image.")
    return dst
