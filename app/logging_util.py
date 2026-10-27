"""Tiny append-only diagnostic log (no external logging setup)."""

from __future__ import annotations

from datetime import datetime

MAX_BYTES = 256 * 1024


def log(message: str) -> None:
    try:
        from .config import data_dir

        directory = data_dir()
        path = directory / "app.log"
        if path.is_file() and path.stat().st_size > MAX_BYTES:
            backup = directory / "app.log.1"
            try:
                if backup.is_file():
                    backup.unlink()
                path.replace(backup)
            except OSError:
                pass
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {message}\n")
    except OSError:
        pass
