"""Render the cutout tool for the docs: the band preview and the joined result."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
NATIVE = "--native" in sys.argv
if not NATIVE:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
OUT = ROOT / "docs" / "screenshots"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QColor, QFont, QImage, QMouseEvent, QPainter, QPen
    from PySide6.QtWidgets import QApplication

    from app import theme
    from app.config import Settings
    from app.editor import EditorWindow

    app = QApplication(sys.argv)
    theme.apply(app, 1.0)

    image = QImage(760, 520, QImage.Format.Format_ARGB32)
    image.fill(QColor("#101826"))
    painter = QPainter(image)
    painter.fillRect(0, 0, 760, 52, QColor("#1b2740"))
    painter.setPen(QPen(QColor("#2c3b57"), 1))
    painter.drawLine(0, 52, 760, 52)
    painter.setPen(QColor("#e6e8ec"))
    painter.setFont(QFont("Segoe UI", 14))
    painter.drawText(20, 34, "Bảng điều khiển")
    painter.setFont(QFont("Segoe UI", 10))
    painter.setPen(QColor("#9aa7bd"))
    painter.drawText(20, 96, "Doanh thu tháng 10")
    painter.fillRect(20, 110, 300, 130, QColor("#2563eb"))
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
    painter.drawText(38, 185, "1.284.000.000 đ")
    painter.setPen(QColor("#9aa7bd"))
    painter.setFont(QFont("Segoe UI", 10))
    painter.drawText(20, 275, "Chi tiết đơn hàng")
    for row in range(5):
        y = 300 + row * 40
        painter.fillRect(20, y, 720, 1, QColor("#22304a"))
        painter.drawText(20, y + 26, f"Đơn hàng #{1024 + row}   ·   đã thanh toán")
    painter.fillRect(420, 110, 320, 130, QColor("#12203a"))
    painter.setPen(QColor("#57d38c"))
    painter.drawText(440, 150, "Tăng trưởng +18%")
    painter.end()

    settings = Settings()
    window = EditorWindow(image, settings, "cutout demo")
    window.resize(1040, 760)
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.show()
    app.processEvents()

    canvas = window.canvas
    canvas.fit_to_view()
    window._select_tool("cutout")
    app.processEvents()

    def ev(kind, point, button, buttons):
        local = canvas._to_widget(QPointF(*point))
        return QMouseEvent(kind, local, local, button, buttons, Qt.KeyboardModifier.NoModifier)

    canvas.mousePressEvent(ev(QEvent.Type.MouseButtonPress, (2, 246),
                              Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton))
    canvas.mouseMoveEvent(ev(QEvent.Type.MouseMove, (758, 292),
                             Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton))
    app.processEvents()

    OUT.mkdir(parents=True, exist_ok=True)
    window.grab().save(str(OUT / "cutout.png"), "PNG")
    print("wrote docs/screenshots/cutout.png")

    canvas.mouseReleaseEvent(ev(QEvent.Type.MouseButtonRelease, (758, 292),
                                Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton))
    app.processEvents()
    window.grab().save(str(OUT / "cutout-result.png"), "PNG")
    print("wrote docs/screenshots/cutout-result.png")
    print(f"result size: {canvas.image().width()}x{canvas.image().height()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
