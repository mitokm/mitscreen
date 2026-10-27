"""Verify that global hotkeys are delivered through Qt's native event filter.

Runs on the real Windows platform (hidden helper window, no visible UI).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.pop("QT_QPA_PLATFORM", None)

from ctypes import wintypes  # noqa: E402

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from app import win32util  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    owner = QWidget()
    owner.setWindowTitle("Mitscreen hotkey owner")
    owner.resize(8, 8)
    owner.show()  # creates the native HWND
    app.processEvents()

    manager = win32util.HotkeyManager(owner)
    manager.install()

    fired: list[int] = []
    ok = manager.register("probe", "Ctrl+Alt+F9", lambda: fired.append(1))
    print(f"register Ctrl+Alt+F9: {ok}  failures={manager.failed}")

    # a second, everyday probe: PrintScreen on its own
    print_ok = manager.register("print", "Print", lambda: fired.append(2))
    print(f"register Print: {print_ok}  failures={manager.failed}")

    if not ok:
        print("FAIL: hotkey could not be registered")
        return 1

    hwnd = manager.hwnd()
    hotkey_id = next(iter(manager._callbacks))
    print(f"hwnd={hwnd} id=0x{hotkey_id:X}")
    posted = win32util.user32.PostMessageW(wintypes.HWND(hwnd), win32util.WM_HOTKEY,
                                           wintypes.WPARAM(hotkey_id), wintypes.LPARAM(0))
    print(f"PostMessage WM_HOTKEY -> {bool(posted)}")
    deadline = time.time() + 3
    while time.time() < deadline and not fired:
        app.processEvents()
        time.sleep(0.01)

    manager.unregister_all()
    owner.close()
    if fired:
        print(f"PASS: callback fired {len(fired)} time(s)")
        return 0
    print("FAIL: callback never fired (native event filter did not receive WM_HOTKEY)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
