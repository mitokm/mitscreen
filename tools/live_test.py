"""Live test against the running tray app: drive it with synthetic key input.

Verifies the full path hotkey -> overlay -> cancel, and hotkey -> full-screen
capture -> editor window.  It flashes the overlay briefly and closes what it
opens, so it should be run while you are not typing elsewhere.
"""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_void_p]
user32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.IsWindowVisible.argtypes = [wintypes.HWND]

VK_PRINTSCREEN = 0x2C
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_3 = 0x33
VK_ESCAPE = 0x1B
KEYEVENTF_KEYUP = 0x2


def key(vk: int) -> None:
    user32.keybd_event(vk, 0, 0, None)
    time.sleep(0.02)
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, None)
    time.sleep(0.05)


def combo(*vks: int) -> None:
    for vk in vks:
        user32.keybd_event(vk, 0, 0, None)
        time.sleep(0.02)
    for vk in reversed(vks):
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, None)
        time.sleep(0.02)


def windows_of(pid: int) -> list[tuple[int, str, tuple[int, int, int, int]]]:
    found: list[tuple[int, str, tuple[int, int, int, int]]] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _lparam):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, buf, 512)
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            found.append((int(hwnd), buf.value,
                          (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)))
        return True

    user32.EnumWindows(callback, 0)
    return found


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: live_test.py <pid>")
        return 2
    pid = int(sys.argv[1])
    failures = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"[{'ok  ' if ok else 'FAIL'}] {name}{(' — ' + detail) if not ok else ''}")
        if not ok:
            failures.append(name)

    before = windows_of(pid)
    print(f"windows before: {[(t, s) for _, t, s in before]}")

    # 1) Print -> selection overlay should appear, then Esc cancels it
    key(VK_PRINTSCREEN)
    time.sleep(1.2)
    during = windows_of(pid)
    overlay = [w for w in during if w[2][2] >= 1000 and w[2][3] >= 700]
    check("overlay window appeared", bool(overlay), str([(t, s) for _, t, s in during]))
    if overlay:
        check("overlay covers the screen", overlay[0][2][2] >= 1920, str(overlay[0][2]))
        key(VK_ESCAPE)  # the overlay holds keyboard focus, so a real key is enough
        time.sleep(0.9)
        after_cancel = [w for w in windows_of(pid) if w[2][2] >= 1000 and w[2][3] >= 700]
        check("overlay closed on Esc", not after_cancel, str([(t, s) for _, t, s in after_cancel]))

    # 2) Ctrl+Shift+3 -> full-screen capture opens the editor
    combo(VK_CONTROL, VK_SHIFT, VK_3)
    time.sleep(2.0)
    editors = [w for w in windows_of(pid) if "Mitscreen" in w[1]]
    check("editor window opened", bool(editors), str([(t, s) for _, t, s in windows_of(pid)]))
    for hwnd, _title, _rect in editors:
        user32.PostMessageW(wintypes.HWND(hwnd), 0x0010, 0, 0)  # WM_CLOSE
    time.sleep(0.6)

    print()
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("live test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
