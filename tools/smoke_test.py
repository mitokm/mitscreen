"""Headless smoke test: exercises the image pipeline, settings, library and editor.

Run with the project venv:
    .venv\\Scripts\\python.exe tools\\smoke_test.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = Path(tempfile.mkdtemp(prefix="Mitscreen-test-"))
os.environ["APPDATA"] = str(TMP)
os.environ["QT_QPA_PLATFORM"] = "offscreen"

failures: list[str] = []
checks = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global checks
    checks += 1
    status = "ok  " if condition else "FAIL"
    print(f"[{status}] {name}{(' — ' + detail) if detail and not condition else ''}")
    if not condition:
        failures.append(name)


def main() -> int:
    from PySide6.QtCore import QPointF, QRect
    from PySide6.QtGui import QColor, QImage, QPainter, QPen
    from PySide6.QtWidgets import QApplication

    from app import imageutil, library, theme, win32util
    from app.config import Settings

    app = QApplication(sys.argv)
    theme.apply(app, 1.0)

    # ---- build a synthetic screenshot ------------------------------------
    image = QImage(800, 500, QImage.Format.Format_RGB32)
    image.fill(QColor("#2b3442"))
    painter = QPainter(image)
    painter.setPen(QPen(QColor("#e6e8ec"), 3))
    painter.drawText(40, 60, "Mitscreen smoke test")
    painter.fillRect(60, 120, 300, 180, QColor("#1f6feb"))
    painter.end()
    check("image created", image.width() == 800 and image.height() == 500)

    # ---- encode / decode -------------------------------------------------
    for fmt in ("png", "jpg", "webp"):
        data = imageutil.encode(image, fmt, 90)
        check(f"encode {fmt}", len(data) > 500, f"{len(data)} bytes")
    png = imageutil.encode(image, "png")
    check("png magic", png[:8] == b"\x89PNG\r\n\x1a\n")

    # ---- destructive helpers --------------------------------------------
    def region_bytes(qimg, rect):
        return imageutil.qimage_to_pil(qimg).crop(
            (rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())).tobytes()

    blur_rect = QRect(50, 110, 120, 120)
    before = region_bytes(image, blur_rect)
    blurred = imageutil.blur_region(image, blur_rect, 14)
    check("blur keeps size", (blurred.width(), blurred.height()) == (800, 500))
    check("blur changed pixels", region_bytes(blurred, blur_rect) != before)

    mosaic = imageutil.pixelate_region(image, blur_rect, 10)
    check("mosaic changed pixels", region_bytes(mosaic, blur_rect) != before)

    framed = imageutil.add_pretty_frame(image)
    check("frame grows", framed.width() > image.width() and framed.height() > image.height(),
          f"{framed.width()}x{framed.height()}")

    watermarked = imageutil.add_watermark(image, "Mit", "#FFFFFF", 60)
    check("watermark size", (watermarked.width(), watermarked.height()) == (800, 500))

    resized = imageutil.resize_image(image, percent=50)
    check("resize 50%", (resized.width(), resized.height()) == (400, 250))

    thumb = imageutil.thumbnail(image, 120)
    check("thumbnail bounded", max(thumb.width(), thumb.height()) <= 120)

    # ---- settings --------------------------------------------------------
    settings = Settings.load()
    settings.save_dir = str(TMP / "shots")
    settings.library_dir = str(TMP / "library")
    settings.image_format = "png"
    settings.hotkeys["capture_region"] = "Ctrl+Alt+P"
    settings.watermark_text = "Mit"
    settings.save()
    again = Settings.load()
    check("settings persisted", again.hotkeys["capture_region"] == "Ctrl+Alt+P")
    check("settings dirs", Path(again.save_path).is_dir() and Path(again.library_path).is_dir())

    # ---- hotkey parsing ---------------------------------------------------
    parsed = win32util.parse_hotkey("Print")
    check("parse Print", parsed == (0, 0x2C), str(parsed))
    parsed = win32util.parse_hotkey("Ctrl+Shift+4")
    check("parse Ctrl+Shift+4", parsed == (0x2 | 0x4, 0x34), str(parsed))
    parsed = win32util.parse_hotkey("Alt+F9")
    check("parse Alt+F9", parsed == (0x1, 0x78), str(parsed))
    check("parse garbage", win32util.parse_hotkey("") is None)

    # ---- library ----------------------------------------------------------
    shot_path = Path(settings.save_path) / "unit-test.png"
    imageutil.save_qimage(image, shot_path, "png")
    added = library.add_capture(shot_path, settings, "unit test")
    check("library copy", added is not None and Path(added).is_file(), str(added))
    items = library.list_items(settings)
    check("library lists item", len(items) == 1, f"{len(items)} items")
    if items:
        check("library path matches", items[0].path == added)
        library.delete_path(items[0].path)
        check("library delete", len(library.list_items(settings)) == 0)

    # ---- editor -----------------------------------------------------------
    from app.editor import EditorWindow

    editor = EditorWindow(image.copy(), settings, "unit test")
    editor.show()
    app.processEvents()
    canvas = editor.canvas
    canvas.state.tool = "badge"
    canvas.state.next_badge = 1
    canvas._draw_badge(QPointF(30, 30))
    check("badge drawn", canvas.state.next_badge == 2)
    canvas.undo()
    check("undo works", canvas.state.next_badge == 2)
    canvas.redo()

    editor.apply_frame()
    check("editor frame", canvas.image().width() > 800)
    size_before = canvas.image().width()
    canvas.undo()
    check("undo frame", canvas.image().width() < size_before)

    out = Path(settings.save_path) / "from-editor.png"
    imageutil.save_qimage(canvas.image(), out, "png")
    check("editor save", out.is_file() and out.stat().st_size > 1000)
    editor._copied = True
    editor.close()
    app.processEvents()

    # ---- overlay (with a supplied image, no real grab) --------------------
    from app.overlay import RegionOverlay

    received: dict = {}

    def on_finished(rect, action, img):
        received.update(rect=rect, action=action, image=img)

    overlay = RegionOverlay("region", image=image)
    overlay.finished.connect(on_finished)
    overlay._sel = QRect(10, 10, 200, 120)
    overlay._accept("copy")
    app.processEvents()
    check("overlay emits region", received.get("rect") is not None,
          str(received.get("rect")))
    if received.get("rect") is not None:
        check("overlay region size", received["rect"].width() == 200)
        check("overlay image size", received["image"].width() == 200)

    # ---- recorder prerequisites ------------------------------------------
    from app.recorder import find_ffmpeg

    check("ffmpeg located", find_ffmpeg() is not None)

    print()
    print(f"{checks - len(failures)}/{checks} checks passed")
    if failures:
        print("failed: " + ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
