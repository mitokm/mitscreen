"""Check whether the tray icon of the running app is really registered.

Uses Shell_NotifyIconGetRect, which only succeeds when Windows owns an icon for
the given window/uID pair.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

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


def tray_windows(pid: int) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buf, 256)
            rows.append((int(hwnd), buf.value))
        return True

    user32.EnumWindows(callback, 0)
    return rows


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: tray_probe.py <pid>")
        return 2
    pid = int(sys.argv[1])
    rows = tray_windows(pid)
    candidates = [(h, c) for h, c in rows if "TrayIcon" in c]
    print("windows:", [(h, c) for h, c in rows])
    if not candidates:
        print("FAIL: no Qt tray message window")
        return 1

    hwnd, cls = candidates[0]
    found = False
    for uid in range(0, 16):
        ident = NOTIFYICONIDENTIFIER()
        ident.cbSize = ctypes.sizeof(NOTIFYICONIDENTIFIER)
        ident.hWnd = hwnd
        ident.uID = uid
        rect = RECT()
        result = shell32.Shell_NotifyIconGetRect(ctypes.byref(ident), ctypes.byref(rect))
        if result == 0:
            found = True
            print(f"icon uID={uid} registered, rect=({rect.left},{rect.top},"
                  f"{rect.right - rect.left}x{rect.bottom - rect.top})")
    if not found:
        print("FAIL: no tray icon registered for this window")
        return 1
    print("tray icon is registered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
