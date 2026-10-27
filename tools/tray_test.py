"""Minimal tray-icon test with a self-probe of Shell_NotifyIconGetRect."""

from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
LOG = ROOT / "data" / "tray-test.log"

user32 = ctypes.WinDLL("user32")
shell32 = ctypes.WinDLL("shell32")
user32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]


class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]


class NOTIFYICONIDENTIFIER(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND),
                ("uID", wintypes.UINT), ("guidItem", GUID)]


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def report(lines: list[str]) -> None:
    text = "\n".join(lines)
    print(text)
    try:
        LOG.write_text(text, encoding="utf-8")
    except OSError:
        pass


def main() -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QSystemTrayIcon

    from app import icons

    app = QApplication(sys.argv)
    tray = QSystemTrayIcon(icons.icon("snap"))
    tray.setToolTip("Mitscreen tray test")
    tray.show()

    lines = [f"pid={os.getpid()} available={QSystemTrayIcon.isSystemTrayAvailable()} "
             f"visible={tray.isVisible()} null_icon={tray.icon().isNull()}"]

    def probe() -> None:
        rows = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def callback(hwnd, _):
            owner = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == os.getpid():
                name = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, name, 256)
                rows.append((int(hwnd), name.value))
            return True

        user32.EnumWindows(callback, 0)
        lines.append(f"windows={[(h, c) for h, c in rows]}")
        tray_windows = [(h, c) for h, c in rows if "TrayIcon" in c]
        if not tray_windows:
            lines.append("no tray message window")
            report(lines)
            app.quit()
            return
        hwnd = tray_windows[0][0]
        hit = False
        for uid in range(0, 32):
            ident = NOTIFYICONIDENTIFIER()
            ident.cbSize = ctypes.sizeof(NOTIFYICONIDENTIFIER)
            ident.hWnd = hwnd
            ident.uID = uid
            rect = RECT()
            result = shell32.Shell_NotifyIconGetRect(ctypes.byref(ident), ctypes.byref(rect))
            if result == 0:
                hit = True
                lines.append(f"uid={uid} rect=({rect.left},{rect.top},"
                             f"{rect.right - rect.left}x{rect.bottom - rect.top})")
        lines.append(f"registered={hit}")
        report(lines)
        app.quit()

    QTimer.singleShot(2500, probe)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
