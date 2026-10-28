"""Quick-bar checks: sizes, signals, pause/resume, and a visual composite."""

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
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter
    from PySide6.QtWidgets import QApplication

    from app import theme
    from app.config import Settings
    from app.quickbar import QuickBar

    app = QApplication(sys.argv)
    theme.apply(app, 1.0)
    failures = []

    def check(name, cond, detail=""):
        print(f"[{'ok  ' if cond else 'FAIL'}] {name}{(' — ' + detail) if not cond else ''}")
        if not cond:
            failures.append(name)

    settings = Settings()
    settings.extra.pop("quickbar_x", None)
    settings.extra.pop("quickbar_y", None)
    bar = QuickBar(settings)
    if NATIVE:
        bar.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    bar.show()
    app.processEvents()

    expanded = bar.geometry()
    check("expanded size sane", expanded.width() >= 300 and expanded.height() >= 55, str(expanded))

    fired: list[str] = []
    bar.action.connect(fired.append)
    bar.btn_region.click()
    bar.btn_record.click()
    bar.btn_folder.click()
    bar.btn_close.click()
    app.processEvents()
    check("signals emitted", fired == ["region", "record", "folder", "hide"], str(fired))

    bar._apply_geometry(False, animate=False)
    app.processEvents()
    collapsed = bar.geometry()
    check("collapsed is the hanging spider", collapsed.width() == 72 and collapsed.height() == 78
          and collapsed.width() < expanded.width(), str(collapsed))
    check("collapsed keeps centre", abs(collapsed.center().x() - expanded.center().x()) <= 2,
          f"{collapsed.center().x()} vs {expanded.center().x()}")

    bar.pause()
    check("pause hides", not bar.isVisible())
    bar.resume()
    check("resume shows", bar.isVisible())

    # ---- the dropdown menu carries the capture functions -----------------
    menu = bar.btn_menu.menu()
    labels = [action.text() for action in menu.actions() if not action.isSeparator()]
    joined = " | ".join(labels)
    for expected in ("Chụp vùng", "Chụp lại vùng trước", "Chụp toàn màn hình",
                     "Chụp cửa sổ", "hẹn giờ", "Bút lấy màu", "Bảng điều khiển ảnh", "Cài đặt"):
        check(f"menu has {expected}", any(expected in label for label in labels), joined)
    check("menu separators", any(action.isSeparator() for action in menu.actions()))

    # render the menu itself for the docs
    OUT.mkdir(parents=True, exist_ok=True)
    menu.popup(QPoint(60, 60))
    app.processEvents()
    pixmap = menu.grab()
    if not pixmap.isNull():
        canvas_image = QImage(pixmap.size(), QImage.Format.Format_RGB32)
        canvas_image.fill(QColor("#e8eef8"))
        painter = QPainter(canvas_image)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        canvas_image.save(str(OUT / "quickbar-menu.png"), "PNG")
        print("      wrote docs/screenshots/quickbar-menu.png")
    menu.hide()

    # ---- visual composite over a fake desktop ----------------------------
    OUT.mkdir(parents=True, exist_ok=True)
    backdrop = QImage(1000, 260, QImage.Format.Format_RGB32)
    painter = QPainter(backdrop)
    grad = QLinearGradient(0, 0, 1000, 260)
    grad.setColorAt(0, QColor("#e8eef8"))
    grad.setColorAt(1, QColor("#c9d8ee"))
    painter.fillRect(backdrop.rect(), grad)
    painter.setPen(QColor("#9fb3cf"))
    painter.setFont(QFont("Segoe UI", 11))
    painter.drawText(24, 240, "Mitscreen — thanh truy cập nhanh")
    painter.end()

    def composite(expanded_state: bool, name: str) -> None:
        bar._apply_geometry(expanded_state, animate=False)
        app.processEvents()
        pixmap = bar.grab()
        canvas = backdrop.copy()
        p = QPainter(canvas)
        x = (canvas.width() - pixmap.width()) // 2
        y = 12 if expanded_state else 40
        p.drawPixmap(QPoint(x, y), pixmap)
        p.end()
        path = OUT / name
        canvas.save(str(path), "PNG")
        print(f"      wrote {path}")

    composite(True, "quickbar.png")
    composite(False, "quickbar-collapsed.png")

    print()
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("quick-bar checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
