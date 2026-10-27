"""End-to-end checks against the real desktop: screen grab + ffmpeg recording."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = Path(tempfile.mkdtemp(prefix="Mitscreen-e2e-"))


def main() -> int:
    from PySide6.QtCore import QEventLoop, QRect, QTimer
    from PySide6.QtWidgets import QApplication

    from app import imageutil, win32util
    from app.config import Settings
    from app.recorder import Recorder, find_ffmpeg

    QApplication(sys.argv)
    failures = []

    def check(name, cond, detail=""):
        print(f"[{'ok  ' if cond else 'FAIL'}] {name}{'' if cond else ' — ' + detail}")
        if not cond:
            failures.append(name)

    # ---- desktop grab -----------------------------------------------------
    rect = win32util.virtual_screen_rect()
    image = imageutil.grab_desktop()
    check("virtual rect positive", rect.width() > 0 and rect.height() > 0, str(rect))
    check("grab matches virtual screen", (image.width(), image.height()) == (rect.width(), rect.height()),
          f"{image.width()}x{image.height()} vs {rect.width()}x{rect.height()}")

    pil = imageutil.qimage_to_pil(image).convert("RGB")
    colors = pil.resize((32, 32)).getcolors(4096) or []
    check("grab is not blank", len(colors) > 8, f"{len(colors)} distinct downsampled colors")

    region = imageutil.grab_rect(QRect(rect.x(), rect.y(), 300, 200))
    check("region grab size", (region.width(), region.height()) == (300, 200))

    # ---- recording --------------------------------------------------------
    ffmpeg = find_ffmpeg()
    check("ffmpeg present", ffmpeg is not None, str(ffmpeg))
    if ffmpeg:
        settings = Settings()
        settings.save_dir = str(TMP)
        settings.record_fps = 15
        recorder = Recorder(settings)
        result = {"path": None, "error": None, "done": False}

        loop = QEventLoop()

        def on_stopped(path):
            result["path"] = path
            result["done"] = True
            loop.quit()

        def on_failure(message):
            result["error"] = message
            result["done"] = True
            loop.quit()

        recorder.stopped.connect(on_stopped)
        recorder.failure.connect(on_failure)

        started = recorder.start_recording(QRect(rect.x() + 40, rect.y() + 40, 320, 240))
        check("recorder started", started)
        if started:
            QTimer.singleShot(2500, recorder.stop_recording)
            QTimer.singleShot(20000, loop.quit)
            loop.exec()
            check("recording finished", result["done"], str(result))
            check("recording produced file", result["path"] is not None and Path(result["path"]).is_file(),
                  str(result))
            if result["path"]:
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-select_streams", "v:0",
                     "-show_entries", "stream=width,height,nb_frames,codec_name",
                     "-of", "default=nw=1", str(result["path"])],
                    capture_output=True, text=True, timeout=30)
                info = probe.stdout.strip().replace("\n", " ")
                print(f"      ffprobe: {info}")
                check("video has size", "width=320" in info and "height=240" in info, info)
                check("video is h264", "codec_name=h264" in info, info)
                check("video has frames", "nb_frames=" in info and not info.endswith("nb_frames=N/A"), info)
                size_kb = Path(result["path"]).stat().st_size / 1024
                check("video non-trivial", size_kb > 2, f"{size_kb:.1f} KB")
            if result["error"]:
                print(f"      error: {result['error']}")

    print()
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("all end-to-end checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
