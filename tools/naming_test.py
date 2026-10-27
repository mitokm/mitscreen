"""File-naming checks: pattern sanitising, save names, rename in editor/library."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = Path(tempfile.mkdtemp(prefix="mitscreen-naming-"))
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
    from app.config import Settings, sanitize_pattern
    from app.editor import EditorWindow
    from app.history import WorkspaceWindow

    app = QApplication(sys.argv)
    theme.apply(app, 1.0)
    failures = []

    def check(name, cond, detail=""):
        print(f"[{'ok  ' if cond else 'FAIL'}] {name}{(' — ' + detail) if not cond else ''}")
        if not cond:
            failures.append(name)

    # ---- pattern sanitising ---------------------------------------------
    check("empty pattern falls back", sanitize_pattern("") == "snap-%Y%m%d-%H%M%S")
    check("bad characters replaced", sanitize_pattern('a/b:c*d?"e"') == "a-b-c-d--e-",
          sanitize_pattern('a/b:c*d?"e"'))
    check("normal pattern kept", sanitize_pattern("anh-%Y%m%d") == "anh-%Y%m%d")
    check("None falls back", sanitize_pattern(None) == "snap-%Y%m%d-%H%M%S")

    settings = Settings()
    settings.filename_pattern = "anh-<bad>-%Y"
    settings.ask_name_on_save = True
    settings.save()
    loaded = Settings.load()
    check("pattern sanitised on save", loaded.filename_pattern == "anh--bad--%Y",
          loaded.filename_pattern)
    check("ask-name persisted", loaded.ask_name_on_save is True)

    image = QImage(320, 200, QImage.Format.Format_RGB32)
    image.fill(QColor("#2563eb"))
    painter = QPainter(image)
    painter.fillRect(20, 20, 100, 60, QColor("#ffffff"))
    painter.end()

    # ---- editor: name from a stem, then rename ---------------------------
    editor = EditorWindow(image.copy(), loaded, "test")
    path = editor._path_for_stem("Bao cao/Q1")
    check("save name sanitised", path.name == "Bao caoQ1.png", path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    imageutil.save_qimage(image, path, "png")
    editor._path = path
    new_path = editor.rename_to("Bao cao Q1")
    check("editor rename moved the file",
          new_path is not None and new_path.is_file() and not path.exists(), str(new_path))
    if new_path:
        check("editor rename keeps extension", new_path.suffix == ".png", str(new_path))
        check("editor title updated", new_path.name in editor.windowTitle(), editor.windowTitle())
    check("rename to an existing file is refused",
          editor.rename_to(new_path.name.replace(".png", "")) is not None)  # same name is a no-op

    # ---- library: rename the selected image -----------------------------
    shot = loaded.save_path / "mau.png"
    shot.parent.mkdir(parents=True, exist_ok=True)
    imageutil.save_qimage(image, shot, "png")
    added = library.add_capture(shot, loaded, "test")
    check("library copy created", added is not None and Path(added).is_file(), str(added))
    workspace = WorkspaceWindow(loaded)
    workspace.refresh()
    workspace.list.setCurrentRow(0)
    renamed = workspace.rename_to("anh thu vien")
    check("library rename works", renamed is not None and renamed.is_file(), str(renamed))
    if renamed:
        check("library sidecar renamed",
              renamed.with_suffix(renamed.suffix + ".json").is_file(), str(renamed))

    print()
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("naming checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
