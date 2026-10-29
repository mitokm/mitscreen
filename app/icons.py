"""Vector icons drawn at runtime (no external asset files, no third-party icons)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap)

SIZE = 64


def _pen(color: str, width: float = 5.0) -> QPen:
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _arrow(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 5))
    p.drawLine(QPointF(16, 50), QPointF(46, 18))
    head = QPainterPath(QPointF(46, 18))
    head.lineTo(30, 20)
    head.moveTo(46, 18)
    head.lineTo(44, 34)
    p.drawPath(head)


def _line(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 5))
    p.drawLine(QPointF(14, 50), QPointF(50, 14))


def _rect(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 5))
    p.drawRoundedRect(QRectF(12, 16, 40, 32), 4, 4)


def _ellipse(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 5))
    p.drawEllipse(QRectF(12, 16, 40, 32))


def _pen_tool(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 5))
    path = QPainterPath(QPointF(14, 44))
    path.cubicTo(22, 18, 32, 54, 42, 26)
    p.drawPath(path)


def _highlighter(p: QPainter, c: str) -> None:
    color = QColor(c)
    color.setAlpha(150)
    pen = _pen(color.name(QColor.NameFormat.HexArgb), 14)
    p.setPen(pen)
    p.drawLine(QPointF(16, 46), QPointF(48, 18))


def _text(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 5))
    p.drawLine(QPointF(18, 18), QPointF(46, 18))
    p.drawLine(QPointF(32, 18), QPointF(32, 48))
    p.drawLine(QPointF(24, 48), QPointF(40, 48))


def _blur(p: QPainter, c: str) -> None:
    color = QColor(c)
    color.setAlpha(90)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawRoundedRect(QRectF(12, 16, 40, 32), 6, 6)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(c, 3))
    p.drawEllipse(QRectF(23, 25, 18, 14))


def _mosaic(p: QPainter, c: str) -> None:
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(c))
    for row in range(3):
        for col in range(3):
            if (row + col) % 2 == 0:
                p.drawRect(QRectF(14 + col * 12, 18 + row * 10, 10, 8))


def _badge(p: QPainter, c: str) -> None:
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(c))
    p.drawEllipse(QRectF(12, 12, 40, 40))
    p.setPen(_pen("#ffffff", 5))
    p.drawLine(QPointF(30, 24), QPointF(35, 20))
    p.drawLine(QPointF(35, 20), QPointF(35, 44))
    p.drawLine(QPointF(28, 44), QPointF(42, 44))


def _crop(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 5))
    p.drawLine(QPointF(20, 10), QPointF(20, 44))
    p.drawLine(QPointF(10, 20), QPointF(44, 20))
    p.drawLine(QPointF(44, 20), QPointF(44, 54))
    p.drawLine(QPointF(20, 44), QPointF(54, 44))


def _undo(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 5))
    p.drawLine(QPointF(44, 18), QPointF(24, 18))
    p.drawLine(QPointF(24, 18), QPointF(24, 42))
    p.drawLine(QPointF(24, 42), QPointF(15, 33))
    p.drawLine(QPointF(24, 42), QPointF(33, 33))
    p.drawLine(QPointF(44, 18), QPointF(50, 24))


def _redo(p: QPainter, c: str) -> None:
    p.save()
    p.translate(SIZE, 0)
    p.scale(-1, 1)
    _undo(p, c)
    p.restore()


def _copy(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 5))
    p.drawRoundedRect(QRectF(12, 12, 26, 30), 3, 3)
    p.drawRoundedRect(QRectF(26, 24, 26, 30), 3, 3)


def _save(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 5))
    path = QPainterPath(QPointF(14, 14))
    path.lineTo(44, 14)
    path.lineTo(50, 20)
    path.lineTo(50, 50)
    path.lineTo(14, 50)
    path.closeSubpath()
    p.drawPath(path)
    p.drawRect(QRectF(22, 14, 18, 12))
    p.drawRect(QRectF(22, 36, 20, 14))


def _print(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 5))
    p.drawRect(QRectF(18, 12, 28, 14))
    p.drawRoundedRect(QRectF(12, 26, 40, 18), 3, 3)
    p.drawRect(QRectF(20, 40, 24, 12))


def _close(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 6))
    p.drawLine(QPointF(18, 18), QPointF(46, 46))
    p.drawLine(QPointF(46, 18), QPointF(18, 46))


def _settings(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 5))
    p.drawEllipse(QRectF(22, 22, 20, 20))
    for angle in range(0, 360, 45):
        p.save()
        p.translate(32, 32)
        p.rotate(angle)
        p.drawLine(QPointF(0, -20), QPointF(0, -13))
        p.restore()


def _history(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 5))
    p.drawEllipse(QRectF(12, 12, 40, 40))
    p.drawLine(QPointF(32, 20), QPointF(32, 34))
    p.drawLine(QPointF(32, 34), QPointF(42, 40))


def _record(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 4))
    p.drawEllipse(QRectF(10, 10, 44, 44))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(c))
    p.drawEllipse(QRectF(22, 22, 20, 20))


def _fullscreen(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 5))
    for (x, y, dx, dy) in ((14, 14, 1, 1), (50, 14, -1, 1), (14, 50, 1, -1), (50, 50, -1, -1)):
        p.drawLine(QPointF(x, y), QPointF(x + 12 * dx, y))
        p.drawLine(QPointF(x, y), QPointF(x, y + 12 * dy))


def _window(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 5))
    p.drawRoundedRect(QRectF(10, 14, 44, 36), 4, 4)
    p.drawLine(QPointF(10, 26), QPointF(54, 26))


def _region(p: QPainter, c: str) -> None:
    pen = _pen(c, 5)
    pen.setStyle(Qt.PenStyle.DashLine)
    pen.setDashPattern([1.6, 1.4])
    p.setPen(pen)
    p.drawRect(QRectF(12, 16, 40, 32))


def _folder(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 4))
    path = QPainterPath(QPointF(12, 46))
    path.lineTo(12, 20)
    path.lineTo(26, 20)
    path.lineTo(31, 26)
    path.lineTo(52, 26)
    path.lineTo(52, 46)
    path.closeSubpath()
    p.drawPath(path)


def _chevron(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 6))
    p.drawLine(QPointF(20, 26), QPointF(32, 40))
    p.drawLine(QPointF(32, 40), QPointF(44, 26))


def _cutout(p: QPainter, c: str) -> None:
    """Remove a strip and join the remaining halves."""
    p.setPen(_pen(c, 4))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(QRectF(10, 9, 40, 11))
    p.drawRect(QRectF(10, 44, 40, 11))
    dash = _pen(c, 3)
    dash.setStyle(Qt.PenStyle.DashLine)
    dash.setDashPattern([1.3, 1.3])
    p.setPen(dash)
    p.drawRect(QRectF(10, 26, 40, 12))
    p.setPen(_pen(c, 4))
    p.drawLine(QPointF(27, 22), QPointF(31, 27))
    p.drawLine(QPointF(36, 22), QPointF(32, 27))
    p.drawLine(QPointF(27, 42), QPointF(31, 37))
    p.drawLine(QPointF(36, 42), QPointF(32, 37))


def _timer(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 4))
    p.drawEllipse(QRectF(15, 18, 34, 34))
    p.drawLine(QPointF(32, 26), QPointF(32, 36))
    p.drawLine(QPointF(32, 36), QPointF(40, 40))
    p.drawLine(QPointF(26, 10), QPointF(38, 10))
    p.drawLine(QPointF(32, 10), QPointF(32, 18))


def _magnifier(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(28, 28), 15, 15)
    p.drawLine(QPointF(39, 39), QPointF(52, 52))
    p.setPen(_pen(c, 4))
    p.drawLine(QPointF(21, 28), QPointF(35, 28))
    p.drawLine(QPointF(28, 21), QPointF(28, 35))


def _eyedropper(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 5))
    p.drawLine(QPointF(17, 47), QPointF(35, 29))
    p.drawLine(QPointF(31, 25), QPointF(39, 33))
    p.save()
    p.translate(40, 24)
    p.rotate(45)
    p.drawRoundedRect(QRectF(-7, -16, 14, 20), 4, 4)
    p.restore()


def _share(p: QPainter, c: str) -> None:
    p.setPen(_pen(c, 4))
    p.drawLine(QPointF(32, 38), QPointF(32, 12))
    p.drawLine(QPointF(32, 12), QPointF(23, 21))
    p.drawLine(QPointF(32, 12), QPointF(41, 21))
    p.drawLine(QPointF(13, 32), QPointF(13, 51))
    p.drawLine(QPointF(13, 51), QPointF(51, 51))
    p.drawLine(QPointF(51, 51), QPointF(51, 32))


def _snap(p: QPainter, c: str) -> None:
    """Application icon: blue gradient tile with a bold "M"."""
    gradient = QLinearGradient(6, 6, 58, 58)
    gradient.setColorAt(0.0, QColor("#4f9dff"))
    gradient.setColorAt(0.55, QColor("#2563eb"))
    gradient.setColorAt(1.0, QColor("#1e3fb8"))

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(gradient)
    p.drawRoundedRect(QRectF(3, 3, 58, 58), 15, 15)

    # soft top light that fades out, so there is no hard seam in the tile
    highlight = QLinearGradient(0, 3, 0, 46)
    highlight.setColorAt(0.0, QColor(255, 255, 255, 70))
    highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.setBrush(highlight)
    p.drawRoundedRect(QRectF(3, 3, 58, 58), 15, 15)

    pen = QPen(QColor("#ffffff"))
    pen.setWidthF(8.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    letter = QPainterPath(QPointF(19, 46))
    letter.lineTo(19, 21)
    letter.lineTo(32, 38)
    letter.lineTo(45, 21)
    letter.lineTo(45, 46)
    p.drawPath(letter)


_PAINTERS = {
    "arrow": _arrow, "line": _line, "rect": _rect, "ellipse": _ellipse,
    "pen": _pen_tool, "highlight": _highlighter, "text": _text,
    "blur": _blur, "mosaic": _mosaic, "badge": _badge, "crop": _crop,
    "magnify": _magnifier,
    "cutout": _cutout, "timer": _timer, "eyedropper": _eyedropper, "share": _share,
    "undo": _undo, "redo": _redo, "copy": _copy, "save": _save,
    "print": _print, "close": _close, "settings": _settings,
    "history": _history, "record": _record, "fullscreen": _fullscreen,
    "window": _window, "region": _region, "snap": _snap,
    "folder": _folder, "chevron": _chevron,
}


def pixmap(name: str, color: str = "#e6e8ec", size: int = SIZE) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    if size != SIZE:
        painter.scale(size / SIZE, size / SIZE)
    fn = _PAINTERS.get(name)
    if fn:
        fn(painter, color)
    painter.end()
    return pm


def icon(name: str, color: str = "#e6e8ec") -> QIcon:
    return QIcon(pixmap(name, color))
