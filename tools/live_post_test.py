"""Check the running app's hotkey plumbing by posting WM_HOTKEY to its window.

Synthetic key injection can be filtered by the OS for other processes; posting
WM_HOTKEY exercises the same handler the real key would invoke.
"""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.PostMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL

WM_HOTKEY = 0x0312
WM_CLOSE = 0x0010


def windows_of(pid: int) -> list[tuple[int, str, str, tuple[int, int, int, int]]]:
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            title = ctypes.create_unicode_buffer(512)
            cls = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title, 512)
            user32.GetClassNameW(hwnd, cls, 256)
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            found.append((int(hwnd), title.value, cls.value,
                          (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)))
        return True

    user32.EnumWindows(callback, 0)
    return found


def log_tail(path: Path, n: int = 6) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()[-n:]
    except OSError:
        return []


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: live_post_test.py <pid>")
        return 2
    pid = int(sys.argv[1])
    log_path = ROOT / "data" / "app.log"

    windows = windows_of(pid)
    print(f"{len(windows)} window(s) for pid {pid}:")
    for hwnd, title, cls, rect in windows:
        print(f"  hwnd={hwnd} class={cls!r} title={title!r} rect={rect}")

    candidates = [w for w in windows if w[2].startswith("Qt")] or windows
    if not candidates:
        print("FAIL: no window found for the app process")
        return 1
    target = candidates[0]
    print(f"posting WM_HOTKEY to hwnd={target[0]}")

    fired = False
    for hid in range(0xB000, 0xB006):
        user32.PostMessageW(wintypes.HWND(target[0]), WM_HOTKEY, wintypes.WPARAM(hid), wintypes.LPARAM(0))
        time.sleep(0.6)
        lines = log_tail(log_path, 4)
        if any("capture requested" in line for line in lines):
            print(f"WM_HOTKEY id 0x{hid:X} -> handler ran")
            fired = True
            break

    if not fired:
        print(f"FAIL: handler did not run. log tail: {log_tail(log_path, 6)}")
        return 1

    # the overlay should now exist: close it with WM_CLOSE
    time.sleep(0.8)
    overlay = [w for w in windows_of(pid) if w[1] == 'Mitscreen' and w[3][2] >= 1000]
    print(f"overlay windows: {[(w[1], w[3]) for w in overlay]}")
    ok_overlay = bool(overlay)
    for hwnd, _t, _c, _r in overlay:
        user32.PostMessageW(wintypes.HWND(hwnd), WM_CLOSE, 0, 0)
    time.sleep(0.6)
    remaining = [w for w in windows_of(pid) if w[1] == 'Mitscreen' and w[3][2] >= 1000]
    print(f"RESULT overlay={ok_overlay} remaining={len(remaining)}")
    print("log tail:", log_tail(log_path, 4))
    return 0 if ok_overlay else 1


if __name__ == "__main__":
    sys.exit(main())
