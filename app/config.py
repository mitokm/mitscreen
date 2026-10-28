"""Persistent settings for Mitscreen.

Settings live in %APPDATA%\\Mitscreen\\settings.json.  Unknown keys are kept so
that a newer/older build does not delete a user's configuration.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any


APP_DIR_NAME = "Mitscreen"
APP_ROOT = Path(__file__).resolve().parent.parent

_DATA_DIR: Path | None = None


def home_dir() -> Path:
    raw = os.environ.get("USERPROFILE") or os.environ.get("HOME") or str(Path.home())
    return Path(raw)


def appdata_dir() -> Path:
    base = os.environ.get("APPDATA")
    root = Path(base) if base else home_dir() / "AppData" / "Roaming"
    return root / APP_DIR_NAME


def localappdata_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else home_dir() / "AppData" / "Local"
    return root / APP_DIR_NAME


def portable_dir() -> Path:
    return APP_ROOT / "data"


def _writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def data_dir() -> Path:
    """Roaming AppData when possible, else LocalAppData, else a portable folder.

    The fallback matters when the process runs under a restricted account or a
    sandbox that denies writes to the roaming profile.
    """
    global _DATA_DIR
    if _DATA_DIR is not None:
        return _DATA_DIR
    override = os.environ.get("MITSCREEN_HOME", "").strip()
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override).expanduser())
    candidates += [appdata_dir(), localappdata_dir(), portable_dir()]
    for candidate in candidates:
        if _writable(candidate):
            _DATA_DIR = candidate
            return candidate
    _DATA_DIR = portable_dir()
    return _DATA_DIR


def default_save_dir() -> Path:
    pictures = home_dir() / "Pictures" / APP_DIR_NAME
    if _writable(pictures):
        return pictures
    return data_dir() / "shots"


DEFAULT_HOTKEYS: dict[str, str] = {
    "capture_region": "Print",
    "capture_previous": "Ctrl+Shift+2",
    "capture_screen": "Ctrl+Shift+3",
    "capture_window": "Ctrl+Shift+4",
    "record_region": "Ctrl+Shift+5",
    "open_history": "Ctrl+Shift+6",
}

HOTKEY_LABELS: dict[str, str] = {
    "capture_region": "Chụp vùng chọn",
    "capture_previous": "Chụp lại vùng trước",
    "capture_screen": "Chụp toàn màn hình",
    "capture_window": "Chụp cửa sổ",
    "record_region": "Quay vùng màn hình",
    "open_history": "Mở bảng điều khiển ảnh",
}

# What happens right after a region/window capture.
AFTER_CAPTURE_OPTIONS: dict[str, str] = {
    "copy_edit": "Copy vào clipboard + mở trình sửa",
    "edit": "Chỉ mở trình sửa",
    "save": "Lưu file ngay (không mở trình sửa)",
    "menu": "Hiện thanh chọn (Sửa / Copy / Lưu / Quay / Huỷ)",
}


def sanitize_pattern(pattern: str | None) -> str:
    """Make a file-name pattern safe; empty or invalid input falls back to default."""
    default = "snap-%Y%m%d-%H%M%S"
    if not isinstance(pattern, str) or not pattern.strip():
        return default
    text = pattern.strip()
    for bad in '<>:"/\\|?*':
        text = text.replace(bad, "-")
    text = text.replace("\t", " ").strip(" .")
    return text or default


@dataclass
class Settings:
    save_dir: str = ""
    library_dir: str = ""
    image_format: str = "png"          # png | jpg | webp
    jpg_quality: int = 92
    export_dpi: int = 96               # metadata DPI written into the file
    export_scale: int = 100            # percent, resize on save
    png_compress: int = 6              # 1..9 (9 = smallest PNG)
    auto_copy: bool = True             # copy to clipboard after a capture
    auto_save: bool = False            # write a file without asking when saving
    after_capture: str = "copy_edit"   # copy_edit | edit | save | menu
    keep_library: bool = True          # also keep a copy in the history library
    filename_pattern: str = "snap-%Y%m%d-%H%M%S"
    ask_name_on_save: bool = False     # ask for a file name before saving
    hotkeys: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_HOTKEYS))
    watermark_enabled: bool = False
    watermark_text: str = ""
    watermark_color: str = "#FFFFFF"
    watermark_opacity: int = 55        # percent
    pretty_frame: bool = False         # padding + rounded corners + shadow
    show_quickbar: bool = True         # floating quick-access bar
    quickbar_autohide: bool = True     # fold into a small hanging spider when idle
    show_cursor_in_recordings: bool = True
    record_fps: int = 30
    record_crf: int = 23
    ui_scale: float = 1.0
    autostart: bool = False
    theme: str = "dark"
    extra: dict[str, Any] = field(default_factory=dict)

    # ---------------------------------------------------------------- paths
    @property
    def save_path(self) -> Path:
        return Path(self.save_dir).expanduser() if self.save_dir else default_save_dir()

    @property
    def library_path(self) -> Path:
        return Path(self.library_dir).expanduser() if self.library_dir else data_dir() / "library"

    def ensure_dirs(self) -> None:
        for p in (self.save_path, self.library_path, data_dir()):
            try:
                p.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass

    # ---------------------------------------------------------------- io
    @classmethod
    def path(cls) -> Path:
        return data_dir() / "settings.json"

    @classmethod
    def load(cls) -> "Settings":
        raw: dict[str, Any] = {}
        path = cls.path()
        try:
            if path.is_file():
                raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = {}

        known = {f.name for f in fields(cls)}
        extra = {k: v for k, v in raw.items() if k not in known}
        data = {k: v for k, v in raw.items() if k in known}
        data.pop("extra", None)

        settings = cls(**{k: v for k, v in data.items() if k != "extra"})
        settings.extra = extra
        settings._sanitize()
        settings.ensure_dirs()
        return settings

    def _sanitize(self) -> None:
        if self.image_format not in {"png", "jpg", "jpeg", "webp"}:
            self.image_format = "png"
        if self.after_capture not in AFTER_CAPTURE_OPTIONS:
            self.after_capture = "copy_edit"
        self.jpg_quality = max(10, min(100, int(self.jpg_quality)))
        self.record_fps = max(5, min(60, int(self.record_fps)))
        self.record_crf = max(0, min(51, int(self.record_crf)))
        if self.export_dpi not in (72, 96, 150, 300):
            self.export_dpi = 96
        self.export_scale = max(10, min(100, int(self.export_scale)))
        self.png_compress = max(1, min(9, int(self.png_compress)))
        self.filename_pattern = sanitize_pattern(self.filename_pattern)
        self.watermark_opacity = max(0, min(100, int(self.watermark_opacity)))
        merged = dict(DEFAULT_HOTKEYS)
        if isinstance(self.hotkeys, dict):
            for key, value in self.hotkeys.items():
                if key in DEFAULT_HOTKEYS and isinstance(value, str):
                    merged[key] = value
        self.hotkeys = merged
        if not isinstance(self.extra, dict):
            self.extra = {}

    def save(self) -> None:
        payload = {f.name: getattr(self, f.name) for f in fields(self) if f.name != "extra"}
        payload.update(self.extra)
        path = self.path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
