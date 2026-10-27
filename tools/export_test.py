"""Export settings checks: DPI metadata, downscaling, PNG/JPEG weight."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
TMP = Path(tempfile.mkdtemp(prefix="mitscreen-export-"))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    from PIL import Image
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtWidgets import QApplication

    from app import imageutil, theme
    from app.config import Settings

    app = QApplication(sys.argv)  # noqa: F841
    theme.apply(app, 1.0)
    failures = []

    def check(name, cond, detail=""):
        print(f"[{'ok  ' if cond else 'FAIL'}] {name}{(' — ' + detail) if not cond else ''}")
        if not cond:
            failures.append(name)

    # noisy picture so compression levels actually differ
    image = QImage(900, 640, QImage.Format.Format_RGB32)
    image.fill(QColor("#1f2937"))
    painter = QPainter(image)
    for index in range(0, 900, 7):
        painter.fillRect(index, 0, 3, 640, QColor((index * 7) % 255, (index * 13) % 255, 90))
    painter.end()

    # ---- DPI metadata ----------------------------------------------------
    png_path = TMP / "dpi-150.png"
    imageutil.save_qimage(image, png_path, "png", dpi=150, compress_level=6)
    with Image.open(png_path) as saved:
        dpi = saved.info.get("dpi")
    check("png stores the DPI", dpi is not None and round(dpi[0]) == 150, str(dpi))

    jpg_path = TMP / "dpi-300.jpg"
    imageutil.save_qimage(image, jpg_path, "jpg", quality=90, dpi=300)
    with Image.open(jpg_path) as saved:
        dpi = saved.info.get("dpi")
    check("jpeg stores the DPI", dpi is not None and round(dpi[0]) == 300, str(dpi))

    # ---- PNG compression level ------------------------------------------
    light = imageutil.encode(image, "png", compress_level=1)
    small = imageutil.encode(image, "png", compress_level=9)
    check("png level 9 is not bigger", len(small) <= len(light),
          f"{len(light)} -> {len(small)} bytes")

    # ---- JPEG quality ----------------------------------------------------
    low = imageutil.encode(image, "jpg", quality=45)
    high = imageutil.encode(image, "jpg", quality=95)
    check("lower quality is lighter", len(low) < len(high), f"{len(low)} vs {len(high)}")

    # ---- downscaling -----------------------------------------------------
    half = imageutil.scale_image(image, 50)
    check("scale 50 halves the pixels", (half.width(), half.height()) == (450, 320),
          f"{half.width()}x{half.height()}")
    check("scale 100 is untouched", imageutil.scale_image(image, 100) is image)
    encoded_small = len(imageutil.encode(half, "png", compress_level=9))
    check("scaled png is lighter",
          encoded_small < len(imageutil.encode(image, "png", compress_level=9)),
          f"{encoded_small} vs full")

    # ---- settings sanitising --------------------------------------------
    settings = Settings()
    settings.export_dpi = 123
    settings.export_scale = 5
    settings.png_compress = 42
    settings._sanitize()
    check("dpi falls back to 96", settings.export_dpi == 96, str(settings.export_dpi))
    check("scale clamped to 10", settings.export_scale == 10, str(settings.export_scale))
    check("png level clamped to 9", settings.png_compress == 9, str(settings.png_compress))

    print()
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("export checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
