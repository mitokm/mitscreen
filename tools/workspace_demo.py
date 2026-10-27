"""Render the workspace window for the docs (native fonts)."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
NATIVE = "--native" in sys.argv
if not NATIVE:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TMP = Path(tempfile.mkdtemp(prefix="mitscreen-workspace-demo-"))
os.environ["MITSCREEN_HOME"] = str(TMP)
OUT = ROOT / "docs" / "screenshots"


def sample(path: Path, accent: str, title: str) -> None:
    from PySide6.QtGui import QColor, QFont, QImage, QPainter

    from app import imageutil

    image = QImage(520, 320, QImage.Format.Format_RGB32)
    image.fill(QColor("#101826"))
    painter = QPainter(image)
    painter.fillRect(0, 0, 520, 40, QColor("#1b2740"))
    painter.setPen(QColor("#e6e8ec"))
    painter.setFont(QFont("Segoe UI", 11))
    painter.drawText(16, 26, title)
    painter.fillRect(24, 62, 200, 78, QColor(accent))
    painter.setPen(QColor("#9aa7bd"))
    painter.setFont(QFont("Segoe UI", 9))
    for row in range(4):
        y = 170 + row * 28
        painter.fillRect(24, y, 470, 1, QColor("#22304a"))
        painter.drawText(24, y + 19, f"Dòng dữ liệu {row + 1}")
    painter.end()
    imageutil.save_qimage(image, path, "png")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from app import library, theme
    from app.config import Settings
    from app.history import WorkspaceWindow

    app = QApplication(sys.argv)
    theme.apply(app, 1.0)

    settings = Settings()
    settings.ensure_dirs()
    samples = [
        ("Bảng điều khiển", "#2563eb"),
        ("Đơn hàng", "#30a46c"),
        ("Báo cáo tháng", "#e5484d"),
        ("Cài đặt", "#8e4ec6"),
        ("Hồ sơ khách hàng", "#f5a524"),
        ("Hoá đơn", "#0ea5e9"),
    ]
    for index, (title, accent) in enumerate(samples):
        path = settings.save_path / f"mau-{index + 1}.png"
        sample(path, accent, title)
        library.add_capture(path, settings, "demo")

    window = WorkspaceWindow(settings)
    window.resize(1020, 660)
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.show()
    app.processEvents()
    if window.list.count() > 1:
        window.list.setCurrentRow(1)
    app.processEvents()

    OUT.mkdir(parents=True, exist_ok=True)
    window.grab().save(str(OUT / "workspace.png"), "PNG")
    print(f"wrote {OUT / 'workspace.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
