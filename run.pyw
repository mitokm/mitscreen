#!/usr/bin/env pythonw
"""Mitscreen launcher (no console window)."""

from __future__ import annotations

import os
import sys
import traceback

# Physical-pixel coordinate space: disable Qt's own scaling before Qt loads.
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _log_crash(exc_text: str) -> None:
    from app.config import data_dir

    try:
        path = data_dir() / "crash.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(exc_text + "\n")
    except OSError:
        pass


def main() -> int:
    from app import win32util

    scale = win32util.enable_dpi_awareness()

    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from PySide6.QtWidgets import QApplication

    from app import icons, theme
    from app.config import Settings
    from app.tray import MitscreenApp

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Mitscreen")
    app.setApplicationDisplayName("Mitscreen")
    app.setWindowIcon(icons.icon("snap"))
    theme.apply(app, scale)

    # ---- single instance -------------------------------------------------
    server_name = "Mitscreen-single-instance"
    probe = QLocalSocket()
    probe.connectToServer(server_name)
    if probe.waitForConnected(250):
        probe.write(b"ping")
        probe.flush()
        probe.waitForBytesWritten(250)
        probe.disconnectFromServer()
        return 0
    QLocalServer.removeServer(server_name)
    server = QLocalServer()
    server.listen(server_name)

    settings = Settings.load()

    from app import __version__
    from app.logging_util import log
    from app.win32util import integrity_level, virtual_screen_rect

    rect = virtual_screen_rect()
    level = integrity_level()
    log(f"--- Mitscreen {__version__} started (dpi scale {scale}, screen {rect.width()}x{rect.height()}"
        f" at {rect.x()},{rect.y()}, integrity {level}, data {settings.path().parent})")
    if level == "low":
        log("tray icon is blocked: a low-integrity (sandboxed) process cannot add one. "
            "Start Mitscreen from its desktop shortcut instead.")

    controller = MitscreenApp(app, settings)

    def _on_new_connection() -> None:
        conn = server.nextPendingConnection()
        if conn is not None:
            conn.readyRead.connect(lambda: (conn.readAll(), controller.ping()))
            conn.disconnected.connect(conn.deleteLater)

    server.newConnection.connect(_on_new_connection)

    if settings.autostart:
        pass  # already registered by the settings dialog; nothing to do at boot

    if not settings.extra.get("welcome_shown"):
        settings.extra["welcome_shown"] = True
        settings.save()
        controller.ping()

    return app.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        _log_crash(traceback.format_exc())
        raise
