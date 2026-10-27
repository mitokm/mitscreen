"""Render the application icon to PNG/ICO (used for the desktop shortcut)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from app import icons

    QApplication(sys.argv)  # needed for QPixmap/QIcon
    assets = ROOT / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    png_path = assets / "mitscreen.png"
    ico_path = assets / "mitscreen.ico"
    icons.pixmap("snap", size=256).save(str(png_path), "PNG")
    try:
        from PIL import Image

        with Image.open(png_path) as img:
            img.save(ico_path, format="ICO",
                     sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                            (128, 128), (256, 256)])
    except Exception as exc:  # pragma: no cover
        print(f"ico conversion failed: {exc}")
        return 1
    print(f"wrote {png_path}")
    print(f"wrote {ico_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
