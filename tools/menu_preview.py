"""Render the quick-bar dropdown menu for the docs (native fonts)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
NATIVE = "--native" in sys.argv
if not NATIVE:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtWidgets import QApplication

    from app import theme
    from app.config import Settings
    from app.quickbar import QuickBar

    app = QApplication(sys.argv)
    theme.apply(app, 1.0)

    bar = QuickBar(Settings())
    bar.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True) if NATIVE else None
    bar.show()
    app.processEvents()

    menu = bar.btn_menu.menu()
    menu.popup(QPoint(80, 40))
    app.processEvents()
    pixmap = menu.grab()
    menu.hide()
    bar.hide()

    if pixmap.isNull():
        print("FAIL: menu did not render")
        return 1

    canvas = QImage(pixmap.width() + 40, pixmap.height() + 40, QImage.Format.Format_RGB32)
    canvas.fill(QColor("#dfe7f2"))
    painter = QPainter(canvas)
    painter.drawPixmap(20, 20, pixmap)
    painter.end()
    out = ROOT / "docs" / "screenshots" / "quickbar-menu.png"
    canvas.save(str(out), "PNG")
    print(f"wrote {out} ({pixmap.width()}x{pixmap.height()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
