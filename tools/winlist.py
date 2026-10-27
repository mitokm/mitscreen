"""List top-level windows of a process (read-only diagnostic helper)."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

user32 = ctypes.WinDLL("user32")
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: winlist.py <pid>")
        return 2
    pid = int(sys.argv[1])
    rows = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            title = ctypes.create_unicode_buffer(256)
            cls = ctypes.create_unicode_buffer(128)
            user32.GetWindowTextW(hwnd, title, 256)
            user32.GetClassNameW(hwnd, cls, 128)
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            rows.append((title.value, cls.value,
                         rect.right - rect.left, rect.bottom - rect.top,
                         bool(user32.IsWindowVisible(hwnd))))
        return True

    user32.EnumWindows(callback, 0)
    for title, cls, width, height, visible in rows:
        print(f"{title!r:16} {cls[:34]:36} {width}x{height} visible={visible}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
