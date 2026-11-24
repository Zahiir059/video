"""Original vector artwork drawn with QPainter (no image files needed)."""
from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap, QPolygonF, QRadialGradient)


def _grad(w, h, c1, c2, vertical=False):
    g = QLinearGradient(0, 0, 0 if vertical else w, h if vertical else h)
    g.setColorAt(0, QColor(c1))
    g.setColorAt(1, QColor(c2))
    return g


def _motif(p: QPainter, kind: str, w: float, h: float, c1: str, c2: str) -> None:
    rnd = random.Random(kind)
    white = QColor(255, 255, 255, 215)
    p.setPen(Qt.NoPen)
    if kind == "sakura":
        p.setBrush(QColor(255, 255, 255, 235))
        p.drawEllipse(QPointF(w * .72, h * .38), h * .24, h * .24)
        for _ in range(16):
            x, y, r = rnd.random() * w, rnd.random() * h, rnd.uniform(4, 9)
            p.setBrush(QColor(255, 200, 225, 210))
            p.drawEllipse(QPointF(x, y), r, r * .65)
    elif kind == "cube":
        cx, cy, s = w * .5, h * .52, h * .26
        top = QPolygonF([QPointF(cx, cy - s), QPointF(cx + s, cy - s / 2), QPointF(cx, cy), QPointF(cx - s, cy - s / 2)])
        left = QPolygonF([QPointF(cx - s, cy - s / 2), QPointF(cx, cy), QPointF(cx, cy + s), QPointF(cx - s, cy + s / 2)])
        right = QPolygonF([QPointF(cx + s, cy - s / 2), QPointF(cx, cy), QPointF(cx, cy + s), QPointF(cx + s, cy + s / 2)])
        for poly, a in ((top, 245), (left, 190), (right, 140)):
            p.setBrush(QColor(255, 255, 255, a))
            p.drawPolygon(poly)
    elif kind == "toon2d":
        p.setPen(QPen(QColor("#10111B"), 5))
        p.setBrush(QColor("#FDE68A"))
        p.drawEllipse(QPointF(w * .5, h * .5), h * .27, h * .27)
        p.setBrush(QColor("#10111B"))
        p.drawEllipse(QPointF(w * .43, h * .46), 6, 9)
        p.drawEllipse(QPointF(w * .57, h * .46), 6, 9)
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(w * .42, h * .5, w * .16, h * .13), 200 * 16, 140 * 16)
    elif kind == "manga":
        p.setPen(QPen(QColor(255, 255, 255, 190), 2))
        for i in range(34):
            a = i / 34 * 2 * math.pi
            p.drawLine(QPointF(w / 2 + math.cos(a) * h * .22, h / 2 + math.sin(a) * h * .22),
                       QPointF(w / 2 + math.cos(a) * w, h / 2 + math.sin(a) * w))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QPointF(w / 2, h / 2), h * .17, h * .17)
    elif kind == "halftone":
        for yi in range(0, int(h) + 12, 12):
            for xi in range(0, int(w) + 12, 12):
                r = max(0.5, 5.5 * (xi / w))
                p.setBrush(QColor(255, 255, 255, 120))
                p.drawEllipse(QPointF(xi + (6 if (yi // 12) % 2 else 0), yi), r, r)
    elif kind == "city":
        x = 0.0
        while x < w:
            bw, bh = rnd.uniform(18, 38), rnd.uniform(h * .25, h * .7)
            p.setBrush(QColor(10, 10, 30, 235))
            p.drawRect(QRectF(x, h - bh, bw, bh))
            for _ in range(5):
                p.setBrush(QColor(rnd.choice(["#22D3EE", "#EC4899", "#FDE047"])))
                p.drawRect(QRectF(x + rnd.uniform(3, bw - 6), h - rnd.uniform(6, bh - 4), 3, 3))
            x += bw + 3
    elif kind == "stars":
        for _ in range(26):
            x, y, r = rnd.random() * w, rnd.random() * h, rnd.uniform(2, 8)
            path = QPainterPath()
            for k in range(8):
                rr = r if k % 2 == 0 else r * .35
                a = k * math.pi / 4
                pt = QPointF(x + math.cos(a) * rr, y + math.sin(a) * rr)
                path.moveTo(pt) if k == 0 else path.lineTo(pt)
            path.closeSubpath()
            p.setBrush(white)
            p.drawPath(path)
    elif kind == "wash":
        for _ in range(7):
            col = QColor(rnd.choice([c1, c2, "#FFFFFF"]))
            col.setAlpha(95)
            p.setBrush(col)
            p.drawEllipse(QPointF(rnd.random() * w, rnd.random() * h), rnd.uniform(25, 60), rnd.uniform(20, 45))
    elif kind == "clay":
        for i in range(5):
            col = QColor(rnd.choice(["#FDE68A", "#FCA5A5", "#A7F3D0", "#BFDBFE", "#FFFFFF"]))
            p.setBrush(col)
            p.drawRoundedRect(QRectF(w * (.08 + i * .18), h * rnd.uniform(.3, .55), w * .15, h * rnd.uniform(.3, .5)), 16, 16)
    elif kind == "pixel":
        s = 14
        for yi in range(0, int(h), s):
            for xi in range(0, int(w), s):
                if rnd.random() < .22:
                    col = QColor(255, 255, 255, rnd.choice([70, 130, 200]))
                    p.setBrush(col)
                    p.drawRect(xi, yi, s - 1, s - 1)
    elif kind == "retro":
        for i in range(7):
            p.setPen(QPen(QColor(255, 255, 255, 70 + i * 20), 4))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(w / 2, h / 2), 20 + i * 18, 20 + i * 18)
    elif kind == "chibi":
        p.setBrush(QColor("#FFE4D6"))
        p.drawEllipse(QPointF(w / 2, h * .46), h * .3, h * .3)
        p.setBrush(QColor("#2B1B4D"))
        p.drawEllipse(QPointF(w * .4, h * .5), 11, 15)
        p.drawEllipse(QPointF(w * .6, h * .5), 11, 15)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QPointF(w * .4 + 3, h * .5 - 5), 4, 4)
        p.drawEllipse(QPointF(w * .6 + 3, h * .5 - 5), 4, 4)
        p.setBrush(QColor(255, 120, 160, 150))
        p.drawEllipse(QPointF(w * .33, h * .6), 8, 5)
        p.drawEllipse(QPointF(w * .67, h * .6), 8, 5)
    elif kind == "cinema":
        p.setBrush(QColor(255, 255, 255, 235))
        p.drawEllipse(QPointF(w * .3, h * .5), h * .1, h * .1)
        g = QLinearGradient(0, h * .5, w, h * .5)
        g.setColorAt(0, QColor(255, 255, 255, 160))
        g.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(g))
        p.drawRect(QRectF(0, h * .485, w, h * .03))
        p.setBrush(QColor(0, 0, 0, 255))
        p.drawRect(QRectF(0, 0, w, h * .12))
        p.drawRect(QRectF(0, h * .88, w, h * .12))
    elif kind == "pencil":
        p.setPen(QPen(QColor(60, 60, 70, 150), 1.4))
        for i in range(-int(h), int(w), 9):
            p.drawLine(QPointF(i, h), QPointF(i + h, 0))
        p.setPen(QPen(QColor(40, 40, 50, 220), 3))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(w / 2, h / 2), h * .24, h * .24)
    elif kind == "lowpoly":
        pts = [[QPointF(xi * w / 6 + rnd.uniform(-12, 12), yi * h / 4 + rnd.uniform(-12, 12)) for xi in range(7)] for yi in range(5)]
        for yi in range(4):
            for xi in range(6):
                for tri in ([pts[yi][xi], pts[yi][xi + 1], pts[yi + 1][xi]],
                            [pts[yi][xi + 1], pts[yi + 1][xi + 1], pts[yi + 1][xi]]):
                    p.setBrush(QColor(255, 255, 255, rnd.randint(10, 90)))
                    p.setPen(QPen(QColor(255, 255, 255, 60), 1))
                    p.drawPolygon(QPolygonF(tri))


def style_pixmap(style: dict, w: int = 280, h: int = 160, radius: int = 16) -> QPixmap:
    pm = QPixmap(w, h)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
    p.setClipPath(clip)
    p.fillRect(0, 0, w, h, QBrush(_grad(w, h, style["c1"], style["c2"])))
    _motif(p, style["motif"], w, h, style["c1"], style["c2"])
    p.end()
    return pm


def hero_paint(p: QPainter, w: float, h: float) -> None:
    """Large cartoon scene for the dashboard banner (original artwork)."""
    p.setRenderHint(QPainter.Antialiasing)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, w, h), 24, 24)
    p.setClipPath(clip)
    g = QLinearGradient(0, 0, w, h)
    g.setColorAt(0, QColor("#5425D6"))
    g.setColorAt(.55, QColor("#8B5CF6"))
    g.setColorAt(1, QColor("#EC4899"))
    p.fillRect(0, 0, w, h, QBrush(g))
    rnd = random.Random(7)
    p.setPen(Qt.NoPen)
    for _ in range(30):  # sparkles
        p.setBrush(QColor(255, 255, 255, rnd.randint(60, 190)))
        r = rnd.uniform(1.5, 4)
        p.drawEllipse(QPointF(rnd.random() * w, rnd.random() * h), r, r)
    # sun / moon glow on the right
    cx, cy = w * .80, h * .42
    rg = QRadialGradient(cx, cy, h * .75)
    rg.setColorAt(0, QColor(34, 211, 238, 200))
    rg.setColorAt(1, QColor(34, 211, 238, 0))
    p.setBrush(QBrush(rg))
    p.drawEllipse(QPointF(cx, cy), h * .75, h * .75)
    p.setBrush(QColor(255, 255, 255, 240))
    p.drawEllipse(QPointF(cx, cy), h * .2, h * .2)
    # film strip -> cartoon: three frames
    fx = w * .55
    for i, (a, b) in enumerate([("#3B82F6", "#22D3EE"), ("#EC4899", "#8B5CF6"), ("#F59E0B", "#EC4899")]):
        r = QRectF(fx + i * 118, h * .52 + (i % 2) * -26, 104, 128)
        p.setBrush(QColor(16, 17, 27, 160))
        p.drawRoundedRect(r.adjusted(-5, -5, 5, 5), 14, 14)
        gg = QLinearGradient(r.topLeft(), r.bottomRight())
        gg.setColorAt(0, QColor(a))
        gg.setColorAt(1, QColor(b))
        p.setBrush(QBrush(gg))
        p.drawRoundedRect(r, 11, 11)
        p.setBrush(QColor(255, 255, 255, 235))
        p.drawEllipse(QPointF(r.center().x(), r.center().y() - 12), 24, 24)
        p.setBrush(QColor("#10111B"))
        p.drawEllipse(QPointF(r.center().x() - 9, r.center().y() - 15), 3.5, 5)
        p.drawEllipse(QPointF(r.center().x() + 9, r.center().y() - 15), 3.5, 5)
        p.setBrush(QColor(255, 255, 255, 235))
        p.drawRoundedRect(QRectF(r.center().x() - 28, r.center().y() + 20, 56, 34), 14, 14)


def logo_pixmap(size: int = 40) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor("#22D3EE"))
    g.setColorAt(.5, QColor("#8B5CF6"))
    g.setColorAt(1, QColor("#EC4899"))
    p.setBrush(QBrush(g))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, size, size), size * .3, size * .3)
    p.setBrush(QColor("white"))
    path = QPainterPath()
    path.moveTo(size * .38, size * .28)
    path.lineTo(size * .74, size * .5)
    path.lineTo(size * .38, size * .72)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return pm
