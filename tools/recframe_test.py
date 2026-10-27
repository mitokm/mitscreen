"""Recording-frame checks: geometry, mask hole, and a visual preview."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
NATIVE = "--native" in sys.argv
if not NATIVE:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
TMP = Path(tempfile.mkdtemp(prefix="mitscreen-rec-"))
OUT = ROOT / "docs" / "screenshots"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    from PySide6.QtCore import QEventLoop, QPoint, QRect, QTimer, Qt
    from PySide6.QtGui import QColor, QFont, QImage, QPainter
    from PySide6.QtWidgets import QApplication

    from app import theme
    from app.config import Settings
    from app.recframe import GAP, BORDER, RecordingFrame
    from app.recorder import Recorder

    app = QApplication(sys.argv)
    theme.apply(app, 1.0)
    failures = []

    def check(name, cond, detail=""):
        print(f"[{'ok  ' if cond else 'FAIL'}] {name}{(' — ' + detail) if not cond else ''}")
        if not cond:
            failures.append(name)

    area = QRect(320, 220, 400, 260)
    frame = RecordingFrame()
    if NATIVE:
        frame.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    frame.show_for(area)
    app.processEvents()

    margin = BORDER + GAP
    check("frame surrounds the area",
          frame.geometry() == area.adjusted(-margin, -margin, margin, margin),
          str(frame.geometry()))
    mask = frame.mask()
    check("hole covers the recorded area",
          not mask.contains(QPoint(margin + 5, margin + 5)), "mask covers the video area")
    check("ring is visible",
          mask.contains(QPoint(1, 1)) and mask.contains(QPoint(margin + area.width() + 1, margin + 1)),
          "mask missing the border ring")

    # ---- visual preview --------------------------------------------------
    # the widget itself paints a full rectangle and is then masked into a ring,
    # so draw the ring the same way instead of grabbing the unmasked widget
    preview = QImage(980, 560, QImage.Format.Format_RGB32)
    preview.fill(QColor("#0e1013"))
    painter = QPainter(preview)
    painter.fillRect(40, 40, 900, 480, QColor("#1b2740"))
    painter.setPen(QColor("#9aa7bd"))
    painter.setFont(QFont("Segoe UI", 12))
    painter.drawText(60, 80, "Màn hình đang được quay — phần trong khung đỏ là video")
    local = QRect(area.x() - 40, area.y() - 40, area.width(), area.height())
    # dim everything except the recorded area
    painter.fillRect(QRect(40, 40, 900, 480), QColor(0, 0, 0, 90))
    painter.fillRect(local, QColor("#223052"))
    painter.fillRect(local.adjusted(20, 20, -20, -20), QColor("#2c3d63"))
    # red ring, drawn outside the area exactly like RecordingFrame does
    ring_outer = local.adjusted(-margin, -margin, margin, margin)
    painter.fillRect(ring_outer, QColor("#ef4444"))
    painter.fillRect(local, QColor("#223052"))
    painter.setPen(QColor("#e8eaee"))
    painter.setFont(QFont("Segoe UI", 10))
    painter.drawText(local.x(), local.y() + local.height() + 34,
                     "● REC  ·  khung đỏ nằm ngoài vùng ghi")
    painter.end()
    OUT.mkdir(parents=True, exist_ok=True)
    preview.save(str(OUT / "recording-frame.png"), "PNG")
    print("      wrote docs/screenshots/recording-frame.png")
    frame.close()

    # ---- real recording with the frame ----------------------------------
    settings = Settings()
    settings.save_dir = str(TMP)
    settings.record_fps = 15
    recorder = Recorder(settings)
    result = {"path": None, "error": None, "done": False}
    loop = QEventLoop()
    recorder.stopped.connect(lambda path: (result.update(path=path, done=True), loop.quit()))
    recorder.failure.connect(lambda message: (result.update(error=message, done=True), loop.quit()))

    started = recorder.start_recording(area)
    check("recorder started", started)
    if started:
        app.processEvents()
        live_frame = recorder._frame
        check("frame shown while recording", live_frame is not None)
        if live_frame is not None:
            check("live frame geometry", live_frame.geometry() == frame.geometry(),
                  str(live_frame.geometry()))
        QTimer.singleShot(2200, recorder.stop_recording)
        QTimer.singleShot(20000, loop.quit)
        loop.exec()
        check("recording finished", result["done"], str(result))
        check("frame removed after stop", recorder._frame is None)
        if result["path"] and Path(result["path"]).is_file():
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height", "-of", "default=nw=1", str(result["path"])],
                capture_output=True, text=True, timeout=30)
            info = probe.stdout.strip().replace("\n", " ")
            check("video has the recorded size", "width=400" in info and "height=260" in info, info)
        else:
            check("video produced", False, str(result))

    print()
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("recording-frame checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
