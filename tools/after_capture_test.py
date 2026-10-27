"""Verify the post-capture behaviour: copy + editor by default, action bar optional."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = Path(tempfile.mkdtemp(prefix="mitscreen-after-"))
os.environ["MITSCREEN_HOME"] = str(TMP)
os.environ["QT_QPA_PLATFORM"] = "offscreen"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from PySide6.QtCore import QEvent, QPointF, QRect, Qt
    from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter
    from PySide6.QtWidgets import QApplication

    from app import theme
    from app.config import AFTER_CAPTURE_OPTIONS, Settings
    from app.overlay import RegionOverlay

    app = QApplication(sys.argv)
    theme.apply(app, 1.0)
    failures = []

    def check(name, cond, detail=""):
        print(f"[{'ok  ' if cond else 'FAIL'}] {name}{(' — ' + detail) if not cond else ''}")
        if not cond:
            failures.append(name)

    image = QImage(1200, 800, QImage.Format.Format_RGB32)
    image.fill(QColor("#22304a"))
    painter = QPainter(image)
    painter.fillRect(200, 150, 500, 300, QColor("#2f6fd0"))
    painter.end()

    def drag(overlay, start, end):
        press = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(*start), QPointF(*start),
                            Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                            Qt.KeyboardModifier.NoModifier)
        move = QMouseEvent(QEvent.Type.MouseMove, QPointF(*end), QPointF(*end),
                           Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
                           Qt.KeyboardModifier.NoModifier)
        release = QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(*end), QPointF(*end),
                              Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
                              Qt.KeyboardModifier.NoModifier)
        overlay.mousePressEvent(press)
        overlay.mouseMoveEvent(move)
        overlay.mouseReleaseEvent(release)

    # ---- default: auto capture, no action bar ----------------------------
    settings = Settings()
    check("default is copy_edit", settings.after_capture == "copy_edit", settings.after_capture)
    check("four behaviours offered", len(AFTER_CAPTURE_OPTIONS) == 4, str(len(AFTER_CAPTURE_OPTIONS)))

    got: dict = {}
    overlay = RegionOverlay("region", image=image, auto_action="auto")
    overlay.finished.connect(lambda rect, action, img: got.update(rect=rect, action=action, img=img))
    drag(overlay, (100, 100), (460, 330))
    app.processEvents()
    check("auto mode finishes immediately", got.get("action") == "auto", str(got.get("action")))
    check("auto mode has no action bar", overlay._bar.isHidden())
    if got.get("rect"):
        width, height = got["rect"].width(), got["rect"].height()
        check("auto region size", 359 <= width <= 361 and 229 <= height <= 231, f"{width}x{height}")
        check("auto crop matches region",
              got["img"].width() == width and got["img"].height() == height,
              f"{got['img'].width()}x{got['img'].height()}")

    # ---- menu mode keeps the action bar ---------------------------------
    seen: list = []
    overlay2 = RegionOverlay("region", image=image)
    overlay2.finished.connect(lambda rect, action, img: seen.append(action))
    drag(overlay2, (120, 120), (400, 320))
    app.processEvents()
    check("menu mode does not finish yet", not seen, str(seen))
    check("menu mode shows the action bar", not overlay2._bar.isHidden())
    overlay2._on_action("copy")
    app.processEvents()
    check("menu mode finishes on click", seen == ["copy"], str(seen))

    # ---- controller wiring ----------------------------------------------
    from app.tray import MitscreenApp

    settings = Settings.load()
    settings.hotkeys = {key: "" for key in settings.hotkeys}  # do not grab real keys in the test
    settings.show_quickbar = False
    controller = MitscreenApp(app, settings)

    clip = QApplication.clipboard()
    clip.clear()
    controller._on_overlay_finished(QRect(10, 10, 360, 230), "auto", got["img"].copy())
    app.processEvents()
    check("copy_edit puts image on clipboard", not clip.image().isNull())
    editors = controller._editors
    check("copy_edit opens the editor", len(editors) == 1, str(len(editors)))
    if editors:
        check("editor knows it was copied", editors[0]._copied is True)
        editors[0].close()

    settings.after_capture = "edit"
    clip.clear()
    controller._on_overlay_finished(QRect(10, 10, 360, 230), "auto", got["img"].copy())
    app.processEvents()
    editors = controller._editors
    check("edit mode opens the editor", len(editors) == 1, str(len(editors)))
    if editors:
        check("edit mode does not copy", clip.image().isNull())
        check("editor is not marked copied", editors[0]._copied is False)
        editors[0].close()

    settings.after_capture = "save"
    saved_before = len(list(settings.save_path.glob("*"))) if settings.save_path.is_dir() else 0
    controller._on_overlay_finished(QRect(10, 10, 360, 230), "auto", got["img"].copy())
    app.processEvents()
    saved_after = len(list(settings.save_path.glob("*"))) if settings.save_path.is_dir() else 0
    check("save mode writes a file", saved_after == saved_before + 1,
          f"{saved_before} -> {saved_after}")
    check("save mode opens no editor", not controller._editors)

    controller._tray.hide()
    print()
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("post-capture checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
