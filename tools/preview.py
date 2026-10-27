"""Render the overlay and editor to PNG files for visual inspection (headless)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
NATIVE = "--native" in sys.argv
if not NATIVE:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

OUT = ROOT / ".preview"


def main() -> int:
    from PySide6.QtCore import QPointF, QRect, QSize, Qt
    from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPen
    from PySide6.QtWidgets import QApplication

    from app import theme, win32util
    from app.config import Settings
    from app.editor import EditorWindow
    from app.overlay import RegionOverlay

    app = QApplication(sys.argv)
    theme.apply(app, 1.0)
    OUT.mkdir(exist_ok=True)

    # --- a fake "desktop" -------------------------------------------------
    rect = win32util.virtual_screen_rect()
    size = QSize(max(1200, rect.width()), max(800, rect.height()))
    desk = QImage(size, QImage.Format.Format_RGB32)
    grad = QLinearGradient(0, 0, size.width(), size.height())
    grad.setColorAt(0, QColor("#1f2937"))
    grad.setColorAt(1, QColor("#0f172a"))
    painter = QPainter(desk)
    painter.fillRect(desk.rect(), grad)
    painter.setPen(QPen(QColor("#334155"), 2))
    for x in range(0, size.width(), 80):
        painter.drawLine(x, 0, x, size.height())
    for y in range(0, size.height(), 80):
        painter.drawLine(0, y, size.width(), y)
    painter.setPen(QColor("#93a4bd"))
    painter.setFont(QFont("Segoe UI", 16))
    painter.drawText(80, 120, "Mitscreen — vùng chọn")
    painter.end()

    # --- overlay preview ---------------------------------------------------
    overlay = RegionOverlay("region", image=desk)
    overlay.resize(size)
    overlay._sel = QRect(240, 180, 760, 430)
    overlay._dragging = True
    overlay._cursor = QPointF(720, 380)
    overlay._show_bar(overlay._sel)
    if NATIVE:
        overlay.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    overlay.show()
    app.processEvents()
    suffix = "-native" if NATIVE else ""
    overlay.grab().save(str(OUT / f"overlay{suffix}.png"), "PNG")

    # --- editor preview ----------------------------------------------------
    shot = desk.copy(QRect(240, 180, 900, 560))
    settings = Settings()
    editor = EditorWindow(shot, settings, "preview")
    editor.resize(1240, 820)
    if NATIVE:
        editor.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    editor.show()
    app.processEvents()

    canvas = editor.canvas
    canvas.fit_to_view()

    def draw(tool: str, start, end, color: str = "#ff3b30", width: int = 5):
        canvas.state.tool = tool
        canvas.state.color = color
        canvas.state.width = width
        canvas._push_undo()
        painter = QPainter(canvas.image())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        canvas._paint_shape(painter, tool, QPointF(*start), QPointF(*end), None)
        painter.end()
        canvas.update()

    draw("rect", (60, 60), (420, 250), "#32ade6", 5)
    draw("arrow", (470, 240), (700, 90), "#ff3b30", 6)
    draw("highlight", (70, 300), (330, 320), "#ffd60a", 5)
    draw("blur", (500, 320), (700, 430), "#2563eb", 4)
    from app.imageutil import blur_region
    canvas._img = blur_region(canvas.image(), QRect(500, 320, 200, 110), 10)
    canvas.state.tool = "badge"
    canvas.state.color = "#34c759"
    canvas._draw_badge(QPointF(80, 380))
    canvas._draw_badge(QPointF(150, 380))

    editor._on_changed()
    app.processEvents()
    editor.grab().save(str(OUT / f"editor{suffix}.png"), "PNG")

    print(f"wrote {OUT / ('overlay' + suffix + '.png')}")
    print(f"wrote {OUT / ('editor' + suffix + '.png')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
