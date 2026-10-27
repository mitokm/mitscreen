"""Colour-picker overlay check."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter
    from PySide6.QtWidgets import QApplication

    from app import theme
    from app.overlay import RegionOverlay

    app = QApplication(sys.argv)
    theme.apply(app, 1.0)
    failures = []

    def check(name, cond, detail=""):
        print(f"[{'ok  ' if cond else 'FAIL'}] {name}{(' — ' + detail) if not cond else ''}")
        if not cond:
            failures.append(name)

    image = QImage(200, 120, QImage.Format.Format_RGB32)
    image.fill(QColor("#123456"))
    painter = QPainter(image)
    painter.fillRect(40, 40, 20, 20, QColor("#a1b2c3"))
    painter.end()

    picked: list = []
    overlay = RegionOverlay("color", image=image)
    overlay.colorPicked.connect(picked.append)
    overlay.show()
    app.processEvents()

    point = QPointF(50, 50)
    event = QMouseEvent(QEvent.Type.MouseButtonPress, point, point,
                        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                        Qt.KeyboardModifier.NoModifier)
    overlay.mousePressEvent(event)
    app.processEvents()

    check("colour emitted", len(picked) == 1, str(len(picked)))
    if picked:
        color = picked[0]
        check("colour matches the pixel",
              color.name() == "#a1b2c3",
              f"{color.name()}")
    check("overlay closed after picking", not overlay.isVisible())

    print()
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("colour picker checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
