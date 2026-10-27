"""Cutout checks: remove a strip and join the remaining halves."""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RED = (192, 57, 43)
GREEN = (39, 174, 96)
BLUE = (41, 128, 185)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from PIL import Image
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter
    from PySide6.QtWidgets import QApplication

    from app import imageutil, theme
    from app.editor import Canvas, ToolState

    app = QApplication(sys.argv)
    theme.apply(app, 1.0)
    failures = []

    def check(name, cond, detail=""):
        print(f"[{'ok  ' if cond else 'FAIL'}] {name}{(' — ' + detail) if not cond else ''}")
        if not cond:
            failures.append(name)

    def bands(width: int, height: int, horizontal: bool) -> QImage:
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(QColor("#1f2937"))
        painter = QPainter(image)
        if horizontal:
            painter.fillRect(0, 0, width, height // 3, QColor(*RED))
            painter.fillRect(0, height // 3, width, height // 3, QColor(*GREEN))
            painter.fillRect(0, 2 * height // 3, width, height - 2 * height // 3, QColor(*BLUE))
        else:
            painter.fillRect(0, 0, width // 3, height, QColor(*RED))
            painter.fillRect(width // 3, 0, width // 3, height, QColor(*GREEN))
            painter.fillRect(2 * width // 3, 0, width - 2 * width // 3, height, QColor(*BLUE))
        painter.end()
        return image

    def mouse(kind, x, y, button, buttons):
        return QMouseEvent(kind, QPointF(x, y), QPointF(x, y), button, buttons,
                           Qt.KeyboardModifier.NoModifier)

    def rgb(color):
        return (color.red(), color.green(), color.blue())

    def drag(canvas, start, end):
        canvas.mousePressEvent(mouse(QEvent.Type.MouseButtonPress, *start,
                                     Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton))
        canvas.mouseMoveEvent(mouse(QEvent.Type.MouseMove, *end,
                                    Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton))
        canvas.mouseReleaseEvent(mouse(QEvent.Type.MouseButtonRelease, *end,
                                       Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton))
        app.processEvents()

    # ---- horizontal band: image gets shorter, bottom moves up --------------
    canvas = Canvas(bands(400, 300, horizontal=True), ToolState(tool="cutout"))
    canvas.resize(400, 300)
    drag(canvas, (10, 100), (390, 200))
    cut = canvas.image()
    check("height shrank by the band", cut.height() == 200, f"{cut.width()}x{cut.height()}")
    check("width unchanged", cut.width() == 400, str(cut.width()))
    check("top half untouched", rgb(cut.pixelColor(20, 50)) == RED, str(rgb(cut.pixelColor(20, 50))))
    check("bottom half joined up", rgb(cut.pixelColor(20, 150)) == BLUE,
          str(rgb(cut.pixelColor(20, 150))))
    check("green band is gone",
          all(rgb(cut.pixelColor(x, y)) != GREEN for x in (5, 200, 395) for y in (95, 100, 105)))

    canvas.undo()
    app.processEvents()
    check("undo restores height", canvas.image().height() == 300)
    check("undo restores green", rgb(canvas.image().pixelColor(200, 150)) == GREEN)

    # ---- vertical band: image gets narrower, right side moves left --------
    canvas = Canvas(bands(300, 200, horizontal=False), ToolState(tool="cutout"))
    canvas.resize(300, 200)
    drag(canvas, (100, 10), (200, 190))
    cut = canvas.image()
    check("width shrank by the band", cut.width() == 200, f"{cut.width()}x{cut.height()}")
    check("height unchanged", cut.height() == 200, str(cut.height()))
    check("left part untouched", rgb(cut.pixelColor(50, 100)) == RED, str(rgb(cut.pixelColor(50, 100))))
    check("right part joined left", rgb(cut.pixelColor(150, 100)) == BLUE,
          str(rgb(cut.pixelColor(150, 100))))
    check("green column is gone",
          all(rgb(cut.pixelColor(x, 100)) != GREEN for x in (95, 100, 105)))

    # ---- a tiny drag is ignored (no empty undo step) ----------------------
    canvas = Canvas(bands(300, 200, horizontal=False), ToolState(tool="cutout"))
    canvas.resize(300, 200)
    before = canvas.image().size()
    drag(canvas, (10, 10), (14, 14))
    check("tiny selection ignored", canvas.image().size() == before, str(canvas.image().size()))

    # ---- alpha export still behaves ---------------------------------------
    canvas = Canvas(bands(400, 300, horizontal=True), ToolState(tool="cutout"))
    canvas.resize(400, 300)
    drag(canvas, (0, 100), (399, 200))
    jpg = Image.open(io.BytesIO(imageutil.encode(canvas.image(), "jpg"))).convert("RGB")
    check("jpeg export works after cut", jpg.size == (400, 200), str(jpg.size))

    print()
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("cutout checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
