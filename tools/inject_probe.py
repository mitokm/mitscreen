"""Diagnostic: can this session inject synthetic key events that trigger hotkeys?

If this fails, input injection is blocked in the current environment; it does not
mean the app's hotkey handling is broken (tools/hotkey_test.py proves dispatch).
"""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes

from PySide6.QtWidgets import QApplication, QWidget

sys.path.insert(0, __file__.rsplit("\\tools", 1)[0])

from app import win32util  # noqa: E402

user32 = ctypes.WinDLL("user32")
user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_void_p]
KEYUP = 0x2


def press(vk: int) -> None:
    user32.keybd_event(vk, 0, 0, None)
    time.sleep(0.02)
    user32.keybd_event(vk, 0, KEYUP, None)


def main() -> int:
    app = QApplication(sys.argv)
    owner = QWidget()
    owner.setWindowTitle("Mitscreen inject probe")
    owner.show()
    app.processEvents()

    manager = win32util.HotkeyManager(owner)
    manager.install()
    fired: list[int] = []
    ok = manager.register("probe", "Ctrl+Alt+F10", lambda: fired.append(1))
    print(f"register Ctrl+Alt+F10: {ok}")
    time.sleep(0.3)

    ctypes.windll.user32.keybd_event(0x11, 0, 0, None)   # Ctrl down
    ctypes.windll.user32.keybd_event(0x12, 0, 0, None)   # Alt down
    press(0x79)                                          # F10
    ctypes.windll.user32.keybd_event(0x12, 0, KEYUP, None)
    ctypes.windll.user32.keybd_event(0x11, 0, KEYUP, None)

    deadline = time.time() + 2.5
    while time.time() < deadline and not fired:
        app.processEvents()
        time.sleep(0.01)
    manager.unregister_all()
    print("fired:", len(fired))
    print("RESULT:", "injection works" if fired else "injection blocked or ignored")
    return 0 if fired else 1


if __name__ == "__main__":
    sys.exit(main())
