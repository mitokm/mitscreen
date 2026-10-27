"""The screenshot history library (plain folder + JSON sidecars)."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image

from .config import Settings

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


@dataclass
class LibraryItem:
    path: Path
    created: datetime
    width: int
    height: int


def _sidecar(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".json")


def add_capture(path: Path, settings: Settings, origin: str = "") -> Path | None:
    """Copy a saved capture into the library folder and write its metadata."""
    if not settings.keep_library:
        return None
    path = Path(path)
    if not path.is_file():
        return None
    month_dir = settings.library_path / datetime.now().strftime("%Y-%m")
    try:
        month_dir.mkdir(parents=True, exist_ok=True)
        target = month_dir / path.name
        if target.exists():
            stamp = datetime.now().strftime("%H%M%S-%f")[:-3]
            target = month_dir / f"{path.stem}-{stamp}{path.suffix}"
        shutil.copy2(path, target)
        width = height = 0
        try:
            with Image.open(target) as pil:
                width, height = pil.size
        except Exception:
            pass
        meta = {
            "created": datetime.now().isoformat(timespec="seconds"),
            "origin": origin,
            "source": str(path),
            "name": target.name,
            "width": width,
            "height": height,
        }
        _sidecar(target).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return target
    except OSError:
        return None


def list_items(settings: Settings, limit: int = 400) -> list[LibraryItem]:
    root = settings.library_path
    if not root.is_dir():
        return []
    files: list[Path] = []
    try:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                files.append(path)
    except OSError:
        return []
    files.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    items: list[LibraryItem] = []
    for path in files[:limit]:
        try:
            stat = path.stat()
            meta = {}
            sc = _sidecar(path)
            if sc.is_file():
                try:
                    meta = json.loads(sc.read_text(encoding="utf-8"))
                except ValueError:
                    meta = {}
            created = datetime.fromisoformat(meta["created"]) if meta.get("created") else datetime.fromtimestamp(stat.st_mtime)
            items.append(LibraryItem(path=path, created=created,
                                     width=int(meta.get("width") or 0),
                                     height=int(meta.get("height") or 0)))
        except (OSError, ValueError):
            continue
    return items


def delete_item(item: LibraryItem) -> None:
    delete_path(item.path)


def delete_path(path: Path) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass
    try:
        _sidecar(Path(path)).unlink(missing_ok=True)
    except OSError:
        pass
