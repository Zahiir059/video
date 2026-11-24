"""Procedurally painted artwork for style cards and the hero banner (original, no image files)."""
from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF,
                           QRadialGradient)


def _lin(rect: QRectF, c1: str, c2: str, c3: str | None = None) -> QLinearGradient:
    g = QLinearGradient(rect.topLeft(), rect.bottomRight())
    g.setColorAt(0, QColor(c1))
    if c3:
        g.setColorAt(0.5, QColor(c3))
    g.setColorAt(1, QColor(c2))
    return g


def _star(p: QPainter, c: QPointF, r: float) -> None:
    pts = []
    for i in range(8):
        a = i * math.pi / 4
        rr = r if i % 2 == 0 else r * 0.28
        pts.append(QPointF(c.x() + rr * math.cos(a), c.y() + rr * math.sin(a)))
    p.drawPolygon(QPolygonF(pts))


def paint_face(p: QPainter, cx: float, cy: float, r: float, hair: str = "#2B1B4B", eye: float = 1.0) -> None:
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(hair))                                   # hair back
    p.drawEllipse(QPointF(cx, cy - r * 0.08), r * 1.08, r * 1.1)
    p.setBrush(QColor("#FFD9C2"))                              # face
    p.drawEllipse(QPointF(cx, cy + r * 0.05), r * 0.92, r * 0.95)
    p.setBrush(QColor(hair))                                   # fringe
    path = QPainterPath()
    path.moveTo(cx - r * 0.95, cy - r * 0.05)
    path.quadTo(cx - r * 0.5, cy - r * 1.25, cx + r * 0.2, cy - r * 0.55)
    path.quadTo(cx + r * 0.7, cy - r * 1.0, cx + r * 0.95, cy - r * 0.05)
    path.quadTo(cx + r * 0.6, cy - r * 0.55, cx, cy - r * 0.45)
    path.quadTo(cx - r * 0.6, cy - r * 0.55, cx - r * 0.95, cy - r * 0.05)
    p.drawPath(path)
    er = r * 0.17 * eye
    for sx in (-1, 1):
        ex, ey = cx + sx * r * 0.4, cy + r * 0.12
        p.setBrush(QColor("white"))
        p.drawEllipse(QPointF(ex, ey), er * 1.15, er * 1.4)
        p.setBrush(QColor("#4C1D95"))
        p.drawEllipse(QPointF(ex, ey + er * 0.1), er * 0.85, er * 1.15)
        p.setBrush(QColor("white"))
        p.drawEllipse(QPointF(ex - er * 0.3, ey - er * 0.35), er * 0.3, er * 0.3)
        p.setBrush(QColor(255, 120, 150, 110))
        p.drawEllipse(QPointF(cx + sx * r * 0.62, cy + r * 0.5), r * 0.16, r * 0.09)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor("#B4506E"), max(1.5, r * 0.035), Qt.SolidLine, Qt.RoundCap))
    m = QPainterPath()
    m.moveTo(cx - r * 0.16, cy + r * 0.52)
    m.quadTo(cx, cy + r * 0.68, cx + r * 0.16, cy + r * 0.52)
    p.drawPath(m)
    p.restore()


def _motif(p: QPainter, r: QRectF, motif: str, rnd: random.Random) -> None:
    w, h = r.width(), r.height()
    p.setPen(Qt.NoPen)
    if motif == "stars":
        p.setBrush(QColor(255, 255, 255, 190))
        for _ in range(14):
            _star(p, QPointF(r.x() + rnd.random() * w, r.y() + rnd.random() * h), 3 + rnd.random() * 8)
    elif motif == "clay":
        for _ in range(6):
            p.setBrush(QColor(255, 255, 255, 38))
            p.drawEllipse(QPointF(r.x() + rnd.random() * w, r.y() + rnd.random() * h), 25 + rnd.random() * 35, 25 + rnd.random() * 30)
    elif motif == "retro":
        p.setBrush(QColor(255, 255, 255, 34))
        c = QPointF(r.center().x(), r.bottom())
        for i in range(12):
            a = math.pi + i * math.pi / 12
            poly = QPolygonF([c, QPointF(c.x() + math.cos(a) * w * 2, c.y() + math.sin(a) * w * 2),
                              QPointF(c.x() + math.cos(a + 0.12) * w * 2, c.y() + math.sin(a + 0.12) * w * 2)])
            if i % 2 == 0:
                p.drawPolygon(poly)
    elif motif == "manga":
        p.setPen(QPen(QColor(20, 20, 30, 150), 1.6))
        c = r.center()
        for i in range(40):
            a = i * math.pi / 20
            p.drawLine(QPointF(c.x() + math.cos(a) * w * 0.38, c.y() + math.sin(a) * h * 0.38),
                       QPointF(c.x() + math.cos(a) * w, c.y() + math.sin(a) * w))
    elif motif == "halftone":
        p.setBrush(QColor(0, 0, 0, 60))
        step = 12
        for gx in range(0, int(w), step):
            for gy in range(0, int(h), step):
                d = math.hypot(gx - w, gy) / math.hypot(w, h)
                rad = (1 - d) * step * 0.48
                if rad > 0.8:
                    p.drawEllipse(QPointF(r.x() + gx, r.y() + gy), rad, rad)
    elif motif == "grid":
        p.setPen(QPen(QColor(34, 211, 238, 170), 1.2))
        hy = r.y() + h * 0.55
        for i in range(-8, 9):
            p.drawLine(QPointF(r.center().x(), hy), QPointF(r.center().x() + i * w * 0.25, r.bottom()))
        for j in range(1, 6):
            y = hy + (r.bottom() - hy) * (j / 5) ** 1.8
            p.drawLine(QPointF(r.x(), y), QPointF(r.right(), y))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(236, 72, 153, 120))
        p.drawRect(QRectF(r.x() + w * 0.08, r.y() + h * 0.18, w * 0.1, h * 0.4))
        p.drawRect(QRectF(r.x() + w * 0.8, r.y() + h * 0.1, w * 0.08, h * 0.5))
    elif motif == "moon":
        p.setBrush(QColor(255, 255, 255, 220))
        p.drawEllipse(QPointF(r.x() + w * 0.8, r.y() + h * 0.22), h * 0.13, h * 0.13)
        p.setBrush(QColor(255, 255, 255, 170))
        for _ in range(12):
            p.drawEllipse(QPointF(r.x() + rnd.random() * w, r.y() + rnd.random() * h * 0.6), 1.6, 1.6)
    elif motif == "wash":
        cols = ["#F9A8D4", "#93C5FD", "#A7F3D0", "#FDE68A"]
        for i in range(7):
            c = QColor(cols[i % 4])
            c.setAlpha(90)
            p.setBrush(c)
            p.drawEllipse(QPointF(r.x() + rnd.random() * w, r.y() + rnd.random() * h), 30 + rnd.random() * 40, 24 + rnd.random() * 30)
    elif motif == "pixels":
        s = 14
        for gx in range(0, int(w), s):
            for gy in range(int(h * 0.55), int(h), s):
                if rnd.random() < 0.45:
                    p.setBrush(QColor(255, 255, 255, 30 + rnd.randint(0, 50)))
                    p.drawRect(QRectF(r.x() + gx, r.y() + gy, s - 1, s - 1))
    elif motif == "sketch":
        p.setPen(QPen(QColor(60, 60, 70, 95), 1.1))
        for i in range(-int(h), int(w), 9):
            p.drawLine(QPointF(r.x() + i, r.bottom()), QPointF(r.x() + i + h, r.y()))
    elif motif == "lowpoly":
        for _ in range(16):
            x, y = r.x() + rnd.random() * w, r.y() + rnd.random() * h
            s = 28 + rnd.random() * 40
            p.setBrush(QColor(255, 255, 255, rnd.randint(20, 70)))
            p.drawPolygon(QPolygonF([QPointF(x, y), QPointF(x + s, y + s * 0.3), QPointF(x + s * 0.4, y + s)]))
    elif motif == "sun":
        p.setBrush(QColor(255, 190, 90, 210))
        p.drawEllipse(QPointF(r.x() + w * 0.2, r.y() + h * 0.7), h * 0.28, h * 0.28)
        p.setBrush(QColor(0, 0, 0, 190))
        p.drawRect(QRectF(r.x(), r.y(), w, h * 0.1))
        p.drawRect(QRectF(r.x(), r.bottom() - h * 0.1, w, h * 0.1))


def paint_style_art(p: QPainter, rect: QRectF, style) -> None:
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    clip = QPainterPath()
    clip.addRoundedRect(rect, 14, 14)
    p.setClipPath(clip)
    p.fillRect(rect, QBrush(_lin(rect, style.c1, style.c2)))
    _motif(p, rect, style.motif, random.Random(style.id))
    r = min(rect.width(), rect.height()) * 0.27
    paint_face(p, rect.center().x(), rect.center().y() + rect.height() * 0.05, r, "#2B1B4B", style.eye)
    p.restore()


def paint_hero(p: QPainter, rect: QRectF) -> None:
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    clip = QPainterPath()
    clip.addRoundedRect(rect, 22, 22)
    p.setClipPath(clip)
    g = QLinearGradient(rect.topLeft(), rect.bottomRight())
    g.setColorAt(0, QColor("#5425D6"))
    g.setColorAt(0.55, QColor("#3B82F6"))
    g.setColorAt(1, QColor("#EC4899"))
    p.fillRect(rect, QBrush(g))
    rnd = random.Random(7)
    p.setPen(Qt.NoPen)
    for col, cx, cy, rad in (("#22D3EE", 0.62, 0.2, 130), ("#EC4899", 0.95, 0.9, 160), ("#8B5CF6", 0.3, 1.0, 140)):
        rg = QRadialGradient(QPointF(rect.x() + rect.width() * cx, rect.y() + rect.height() * cy), rad)
        c = QColor(col)
        c.setAlpha(150)
        rg.setColorAt(0, c)
        c.setAlpha(0)
        rg.setColorAt(1, c)
        p.setBrush(QBrush(rg))
        p.drawEllipse(QPointF(rect.x() + rect.width() * cx, rect.y() + rect.height() * cy), rad, rad)
    p.setBrush(QColor(255, 255, 255, 200))
    for _ in range(26):
        _star(p, QPointF(rect.x() + rect.width() * (0.45 + rnd.random() * 0.55), rect.y() + rnd.random() * rect.height()), 2 + rnd.random() * 7)
    # character, right side
    r = min(rect.height() * 0.36, rect.width() * 0.17)
    paint_face(p, rect.x() + rect.width() * 0.8, rect.center().y() + 4, r, "#FF6FB5", 1.35)
    paint_face(p, rect.x() + rect.width() * 0.6, rect.center().y() + rect.height() * 0.18, r * 0.62, "#22D3EE", 1.5)
    p.restore()
