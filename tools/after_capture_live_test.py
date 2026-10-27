"""Live end-to-end: hotkey -> drag -> auto copy + editor (no action bar)."""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "data" / "app.log"

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                               wintypes.DWORD, ctypes.c_void_p]
user32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.PostMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]

WM_HOTKEY = 0x0312
WM_CLOSE = 0x0010
LEFTDOWN = 0x0002
LEFTUP = 0x0004


def windows(pid: int):
    rows = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            title = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title, 256)
            rows.append((int(hwnd), title.value, bool(user32.IsWindowVisible(hwnd))))
        return True

    user32.EnumWindows(callback, 0)
    return rows


def log_tail(lines: int = 6) -> list[str]:
    try:
        return LOG.read_text(encoding="utf-8").splitlines()[-lines:]
    except OSError:
        return []


def main() -> int:
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if not pid:
        print("usage: after_capture_live_test.py <pid>")
        return 2

    rows = windows(pid)
    owner = next((h for h, title, _ in rows if title == "Mitscreen"), None)
    if owner is None:
        print("FAIL: app window not found")
        return 1

    user32.PostMessageW(wintypes.HWND(owner), WM_HOTKEY, wintypes.WPARAM(0xB000), wintypes.LPARAM(0))
    time.sleep(1.0)
    # drag a 520x300 region inside the overlay
    user32.SetCursorPos(400, 300)
    time.sleep(0.15)
    user32.mouse_event(LEFTDOWN, 0, 0, 0, None)
    for step in range(1, 13):
        user32.SetCursorPos(400 + step * 40, 300 + step * 25)
        time.sleep(0.03)
    user32.mouse_event(LEFTUP, 0, 0, 0, None)
    time.sleep(2.0)

    tail = log_tail(8)
    print("log tail:")
    for line in tail:
        print("   ", line.encode("ascii", "replace").decode("ascii"))

    ok = any("capture finished: auto" in line for line in tail) and \
        any("after capture: copied + editor" in line for line in tail)

    editors = [(h, t) for h, t, visible in windows(pid) if "Mitscreen" in t and "—" in t]
    print(f"editor windows: {[(h, t.encode('ascii', 'replace').decode('ascii')) for h, t in editors]}")
    ok = ok and bool(editors)

    for hwnd, _title in editors:
        user32.PostMessageW(wintypes.HWND(hwnd), WM_CLOSE, 0, 0)
    time.sleep(0.5)

    print("RESULT:", "passed" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
