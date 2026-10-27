"""Live check: the quick bar exists, hides during a capture, and comes back."""

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
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.PostMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL

WM_HOTKEY = 0x0312
WM_CLOSE = 0x0010


def windows(pid: int):
    rows = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            title = ctypes.create_unicode_buffer(256)
            cls = ctypes.create_unicode_buffer(128)
            user32.GetWindowTextW(hwnd, title, 256)
            user32.GetClassNameW(hwnd, cls, 128)
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            rows.append({
                "hwnd": int(hwnd), "title": title.value, "class": cls.value,
                "w": rect.right - rect.left, "h": rect.bottom - rect.top,
                "x": rect.left, "y": rect.top,
                "visible": bool(user32.IsWindowVisible(hwnd)),
            })
        return True

    user32.EnumWindows(cb, 0)
    return rows


def main() -> int:
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if not pid:
        print("usage: quickbar_live_test.py <pid>")
        return 2
    failures = []

    def check(name, cond, detail=""):
        print(f"[{'ok  ' if cond else 'FAIL'}] {name}{(' — ' + detail) if not cond else ''}")
        if not cond:
            failures.append(name)

    rows = windows(pid)
    for row in rows:
        print(f"  {row['title']!r:16} class={row['class']:36} {row['w']}x{row['h']} at {row['x']},{row['y']} visible={row['visible']}")

    bar = next((r for r in rows if r["title"] == "Mitscreen" and r["w"] < 600 and r["h"] < 140), None)
    owner = next((r for r in rows if r["title"] == "Mitscreen" and r["w"] >= 600), None)
    check("quick bar window exists", bar is not None, "no small Mitscreen window")
    check("quick bar visible", bool(bar and bar["visible"]), str(bar))
    if bar:
        check("quick bar sits near the top", bar["y"] <= 40, str(bar))

    # screenshot the top strip as visual evidence
    if bar:
        from PIL import ImageGrab

        image = ImageGrab.grab(all_screens=True)
        left = max(0, bar["x"] - 220)
        top = 0
        crop = image.crop((left, top, min(image.width, bar["x"] + bar["w"] + 220), 90))
        out = ROOT / "data" / "quickbar-live.png"
        crop.save(out)
        print(f"      wrote {out}")

    if owner and bar:
        user32.PostMessageW(wintypes.HWND(owner["hwnd"]), WM_HOTKEY, wintypes.WPARAM(0xB000), wintypes.LPARAM(0))
        time.sleep(1.2)
        during = windows(pid)
        overlay = [r for r in during if r["w"] >= 1000 and r["h"] >= 700 and r["title"] == "Mitscreen"]
        bar_during = next((r for r in during if r["hwnd"] == bar["hwnd"]), None)
        check("overlay opened", bool(overlay), str([(r['title'], r['w'], r['h']) for r in during]))
        check("bar hidden during capture", bool(bar_during) and not bar_during["visible"],
              str(bar_during))
        for item in overlay:
            user32.PostMessageW(wintypes.HWND(item["hwnd"]), WM_CLOSE, 0, 0)
        time.sleep(1.0)
        after = windows(pid)
        bar_after = next((r for r in after if r["hwnd"] == bar["hwnd"]), None)
        check("bar restored after capture", bool(bar_after) and bar_after["visible"], str(bar_after))
    else:
        print("      skipping capture check (owner window not found)")

    print()
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("quick bar live check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
