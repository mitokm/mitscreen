"""Workspace window checks: thumbnails, sidebar, action bar, signals."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = Path(tempfile.mkdtemp(prefix="mitscreen-workspace-"))
os.environ["MITSCREEN_HOME"] = str(TMP)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtWidgets import QApplication

    from app import imageutil, library, theme
    from app.config import Settings
    from app.history import WorkspaceWindow

    app = QApplication(sys.argv)
    theme.apply(app, 1.0)
    failures = []

    def check(name, cond, detail=""):
        print(f"[{'ok  ' if cond else 'FAIL'}] {name}{(' — ' + detail) if not cond else ''}")
        if not cond:
            failures.append(name)

    settings = Settings()
    settings.ensure_dirs()
    library_root = settings.library_path
    library_root.mkdir(parents=True, exist_ok=True)

    colors = ["#2563eb", "#e5484d", "#30a46c"]
    for index, color in enumerate(colors):
        image = QImage(320, 200, QImage.Format.Format_RGB32)
        image.fill(QColor(color))
        painter = QPainter(image)
        painter.fillRect(20, 20, 120, 60, QColor("#ffffff"))
        painter.end()
        path = settings.save_path / f"sample-{index}.png"
        imageutil.save_qimage(image, path, "png")
        library.add_capture(path, settings, "test")

    window = WorkspaceWindow(settings)
    window.show()
    app.processEvents()

    check("grid lists the library", window.list.count() == len(colors), str(window.list.count()))
    check("count label updated", "ảnh" in window.count_label.text(), window.count_label.text())
    check("thumbnails rendered", not window.list.item(0).icon().isNull())

    captured: list[str] = []
    window.capture_requested.connect(captured.append)
    window.btn_region.click()
    window.btn_record.click()
    app.processEvents()
    check("region action emits", "region" in captured, str(captured))
    check("record action emits", "record" in captured, str(captured))

    edited: list[Path] = []
    window.edit_requested.connect(edited.append)
    window.list.setCurrentRow(0)
    window.btn_edit.click()
    app.processEvents()
    check("edit uses the selected image", len(edited) == 1 and edited[0].suffix == ".png", str(edited))

    shared: list[tuple] = []
    window.share_requested.connect(lambda action, path: shared.append((action, path)))
    window._share("copy_image")
    window._share("copy_path")
    window._share("reveal")
    app.processEvents()
    check("share actions wired",
          [action for action, _ in shared] == ["copy_image", "copy_path", "reveal"], str(shared))

    settings_signals: list[int] = []
    window.settings_requested.connect(lambda: settings_signals.append(1))
    window.btn_close.click()  # closing must not raise
    check("close action works", not window.isVisible())

    fresh = WorkspaceWindow(settings)
    check("empty selection returns None", fresh.selected_path() is None)

    print()
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("workspace checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
