"""Small Windows helpers: DPI awareness, global hotkeys, window geometry.

Everything is done with ctypes so the app has no pywin32 dependency.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QRect

advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
try:
    shcore = ctypes.WinDLL("shcore", use_last_error=True)
except OSError:  # pragma: no cover - very old Windows
    shcore = None


# --------------------------------------------------------------- constants
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

GA_ROOT = 2

_VK_NAMED = {
    "print": 0x2C, "printscreen": 0x2C, "snapshot": 0x2C,
    "insert": 0x2D, "delete": 0x2E, "del": 0x2E,
    "home": 0x24, "end": 0x23,
    "pageup": 0x21, "pgup": 0x21, "prior": 0x21,
    "pagedown": 0x22, "pgdn": 0x22, "next": 0x22,
    "space": 0x20, "tab": 0x09, "esc": 0x1B, "escape": 0x1B,
    "enter": 0x0D, "return": 0x0D, "backspace": 0x08,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "pause": 0x13, "scrolllock": 0x91, "numlock": 0x90, "capslock": 0x14,
}


# ------------------------------------------------------------------- dpi
def enable_dpi_awareness() -> float:
    """Make the process per-monitor DPI aware and return the UI scale factor.

    We deliberately run the process in *physical pixels* (Qt high-DPI scaling is
    disabled by the launcher).  Overlay geometry, mouse positions and grabbed
    bitmaps then share one coordinate space, which keeps region capture exact on
    scaled displays.  Fonts are enlarged ourselves with the returned factor.
    """
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 == -4
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            pass
        else:
            raise OSError
    except Exception:
        try:
            if shcore is not None:
                shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass

    try:
        dc = user32.GetDC(0)
        dpi = 96
        if dc:
            try:
                dpi = ctypes.WinDLL("gdi32").GetDeviceCaps(dc, 88) or 96
            finally:
                user32.ReleaseDC(0, dc)
        scale = max(1.0, dpi / 96.0)
    except Exception:
        scale = 1.0
    return round(scale, 2)


# -------------------------------------------------------------- geometry
def virtual_screen_rect() -> QRect:
    try:
        x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        if w > 0 and h > 0:
            return QRect(x, y, w, h)
    except Exception:
        pass
    return QRect(0, 0, 1920, 1080)


class _SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]


class _TOKEN_MANDATORY_LABEL(ctypes.Structure):
    _fields_ = [("Label", _SID_AND_ATTRIBUTES)]


def integrity_level() -> str:
    """Integrity level of this process: 'low', 'medium', 'high' or 'unknown'.

    A low-integrity process (sandboxed, AppContainer) cannot add a tray icon:
    the shell refuses Shell_NotifyIcon with access denied.
    """
    token = wintypes.HANDLE()
    try:
        advapi32.GetTokenInformation.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD)]
        advapi32.GetSidSubAuthorityCount.argtypes = [ctypes.c_void_p]
        advapi32.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
        advapi32.GetSidSubAuthority.argtypes = [ctypes.c_void_p, wintypes.DWORD]
        advapi32.GetSidSubAuthority.restype = ctypes.POINTER(wintypes.DWORD)
        kernel32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                              ctypes.POINTER(wintypes.HANDLE)]
        if not kernel32.OpenProcessToken(kernel32.GetCurrentProcess(), 0x0008,
                                         ctypes.byref(token)):
            return "unknown"
        size = wintypes.DWORD()
        advapi32.GetTokenInformation(token, 25, None, 0, ctypes.byref(size))
        if not size.value:
            return "unknown"
        buffer = ctypes.create_string_buffer(size.value)
        if not advapi32.GetTokenInformation(token, 25, buffer, size, ctypes.byref(size)):
            return "unknown"
        label = ctypes.cast(buffer, ctypes.POINTER(_TOKEN_MANDATORY_LABEL)).contents
        count = advapi32.GetSidSubAuthorityCount(label.Label.Sid)[0]
        rid = advapi32.GetSidSubAuthority(label.Label.Sid, count - 1)[0]
        return {0x1000: "low", 0x2000: "medium", 0x3000: "high"}.get(rid, "unknown")
    except Exception:
        return "unknown"
    finally:
        try:
            kernel32.CloseHandle(token)
        except Exception:
            pass


def cursor_pos() -> tuple[int, int]:
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


user32.WindowFromPoint.restype = wintypes.HWND
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(_RECT)]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetWindowLongW.restype = ctypes.c_long
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.PostMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.GetClassNameW.argtypes = [wintypes.HWND, ctypes.c_void_p, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.EnumWindows.restype = wintypes.BOOL
user32.EnumChildWindows.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]


def window_at(x: int, y: int, exclude_pids: set[int] | None = None) -> QRect | None:
    """Return the root window rectangle under a physical screen point."""
    exclude_pids = exclude_pids or set()
    try:
        hwnd = user32.WindowFromPoint(wintypes.POINT(int(x), int(y)))
        if not hwnd:
            return None
        hwnd = user32.GetAncestor(hwnd, GA_ROOT)
        if not hwnd or not user32.IsWindowVisible(hwnd):
            return None
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in exclude_pids:
            return None
        ex_style = user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
        if ex_style & 0x00000080:  # WS_EX_TOOLWINDOW
            return None
        rect = _RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w < 40 or h < 30:
            return None
        return QRect(rect.left, rect.top, w, h)
    except Exception:
        return None


# ------------------------------------------------- window frame detection
# Child-window classes that hold an app's *content* rather than its chrome:
# Word's document canvas, Excel's workbook window, Acrobat's page view and
# the Chromium render surface used by Chrome/Edge/Brave/Electron apps.
_CONTENT_CLASSES = ("_WwG", "EXCEL7", "AVL_AVView", "Chrome_RenderWidgetHostHWND")


def _class_name(hwnd) -> str:
    buf = ctypes.create_unicode_buffer(256)
    try:
        if user32.GetClassNameW(hwnd, buf, 256):
            return buf.value
    except Exception:
        pass
    return ""


def _rect_of(hwnd) -> QRect | None:
    rect = _RECT()
    try:
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
    except Exception:
        return None
    w, h = rect.right - rect.left, rect.bottom - rect.top
    if w <= 0 or h <= 0:
        return None
    return QRect(rect.left, rect.top, w, h)


def _enum_windows(top_level: bool, parent=None) -> list:
    """All (hwnd) from EnumWindows / EnumChildWindows, in Z order."""
    found: list = []
    proc_type = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)
    callback_type = proc_type(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _cb(hwnd, _lparam):
        found.append(hwnd)
        return True

    cb = callback_type(_cb)
    try:
        if top_level:
            user32.EnumWindows(cb, 0)
        else:
            user32.EnumChildWindows(parent, cb, 0)
    except Exception:
        return []
    return found


def _root_at(x: int, y: int, exclude_pids: set[int]) -> int | None:
    """Topmost usable top-level window containing the point (Z order)."""
    for hwnd in _enum_windows(True):
        try:
            if not user32.IsWindowVisible(hwnd):
                continue
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in exclude_pids:
                continue
            if user32.GetWindowLongW(hwnd, -20) & 0x00000080:  # tool window
                continue
            rect = _rect_of(hwnd)
            if rect is not None and rect.contains(x, y):
                return hwnd
        except Exception:
            continue
    return None


def _content_child(root, x: int, y: int) -> QRect | None:
    """The app's content area inside `root` (Word text frame, PDF view…)."""
    by_class: dict[str, list] = {}
    for hwnd in _enum_windows(False, root):
        cls = _class_name(hwnd)
        if cls in _CONTENT_CLASSES:
            try:
                if user32.IsWindowVisible(hwnd):
                    by_class.setdefault(cls, []).append(hwnd)
            except Exception:
                continue
    for cls in _CONTENT_CLASSES:
        options = []
        for hwnd in by_class.get(cls, []):
            rect = _rect_of(hwnd)
            if rect is not None and rect.width() >= 160 and rect.height() >= 120:
                options.append(rect)
        if not options:
            continue
        containing = [r for r in options if r.contains(x, y)]
        pool = containing or options
        return max(pool, key=lambda r: r.width() * r.height())
    return None


def _deepest_at(root, x: int, y: int) -> QRect | None:
    """Deepest sizable child window of `root` that contains the point."""
    best: QRect | None = None

    def walk(parent) -> None:
        nonlocal best
        for hwnd in _enum_windows(False, parent):
            try:
                if not user32.IsWindowVisible(hwnd):
                    continue
            except Exception:
                continue
            rect = _rect_of(hwnd)
            if rect is None or not rect.contains(x, y):
                continue
            if rect.width() >= 80 and rect.height() >= 60:
                best = rect
                walk(hwnd)

    walk(root)
    return best


def window_candidates(x: int, y: int,
                      exclude_pids: set[int] | None = None) -> list[QRect]:
    """Capture frames under a screen point, innermost first.

    Order: the app's content area (Word document frame, Acrobat page view,
    browser content…), then the deepest child window, then the whole
    top-level window.  Enumeration skips our own windows, so it works while
    the fullscreen overlay is up.
    """
    exclude_pids = exclude_pids or set()
    try:
        root = _root_at(int(x), int(y), exclude_pids)
        if not root:
            return []
        root_rect = _rect_of(root)
        if root_rect is None or root_rect.width() < 40 or root_rect.height() < 30:
            return []
        found: list[QRect] = []
        for rect in (_content_child(root, int(x), int(y)),
                     _deepest_at(root, int(x), int(y))):
            if rect is not None and rect != root_rect and rect not in found:
                found.append(rect)
        found.append(root_rect)
        return found
    except Exception:
        return []


# --------------------------------------------------------------- hotkeys
def _vk_for(token: str) -> int | None:
    low = token.lower()
    if low in _VK_NAMED:
        return _VK_NAMED[low]
    if len(token) == 1:
        ch = token.upper()
        if "A" <= ch <= "Z" or "0" <= ch <= "9":
            return ord(ch)
        try:
            scan = user32.VkKeyScanW(ctypes.c_wchar(ch))
            if scan != -1:
                return scan & 0xFF
        except Exception:
            pass
    if low.startswith("f") and low[1:].isdigit():
        n = int(low[1:])
        if 1 <= n <= 24:
            return 0x70 + n - 1
    return None


def parse_hotkey(spec: str) -> tuple[int, int] | None:
    """'Ctrl+Shift+4' -> (modifiers, virtual-key).  None when unparseable."""
    if not spec or not spec.strip():
        return None
    tokens = [t for t in spec.replace("+", " ").split() if t]
    mods = 0
    key_token = None
    for tok in tokens:
        low = tok.lower()
        if low in ("ctrl", "control"):
            mods |= MOD_CONTROL
        elif low == "shift":
            mods |= MOD_SHIFT
        elif low == "alt":
            mods |= MOD_ALT
        elif low in ("win", "meta", "super", "windows"):
            mods |= MOD_WIN
        else:
            key_token = tok
    if not key_token:
        return None
    vk = _vk_for(key_token)
    if vk is None:
        return None
    return mods, vk


class HotkeyManager(QAbstractNativeEventFilter):
    """Registers global hotkeys on a hidden Qt window and dispatches WM_HOTKEY."""

    def __init__(self, owner_widget):
        super().__init__()
        self._owner = owner_widget
        self._callbacks: dict[int, callable] = {}
        self._next_id = 0xB000
        self.failed: dict[str, str] = {}
        self.registered: dict[str, str] = {}

    def install(self) -> None:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            app.installNativeEventFilter(self)

    def hwnd(self) -> int:
        try:
            return int(self._owner.winId())
        except Exception:
            return 0

    def register(self, name: str, spec: str, callback) -> bool:
        parsed = parse_hotkey(spec)
        if parsed is None:
            self.failed[name] = "Không đọc được tổ hợp phím"
            return False
        mods, vk = parsed
        hwnd = self.hwnd()
        if not hwnd:
            self.failed[name] = "Chưa có cửa sổ nhận phím"
            return False
        hid = self._next_id
        ok = False
        for _ in range(20):
            if user32.RegisterHotKey(wintypes.HWND(hwnd), hid, mods | MOD_NOREPEAT, vk):
                ok = True
                break
            hid += 1
        if not ok:
            err = ctypes.get_last_error()
            self.failed[name] = (
                "Tổ hợp đang bị chương trình khác chiếm" if err == 1409 else f"Lỗi {err}"
            )
            return False
        self._next_id = hid + 1
        self._callbacks[hid] = callback
        self.registered[name] = spec
        return True

    def unregister_all(self) -> None:
        hwnd = self.hwnd()
        for hid in list(self._callbacks):
            try:
                user32.UnregisterHotKey(wintypes.HWND(hwnd), hid)
            except Exception:
                pass
        self._callbacks.clear()
        self.registered.clear()

    def nativeEventFilter(self, event_type, message):  # noqa: N802 (Qt naming)
        try:
            if event_type in (b"windows_generic_MSG", b"windows_dispatcher_MSG", "windows_generic_MSG"):
                try:
                    address = int(message)
                except (TypeError, ValueError):
                    address = message.__int__()  # PySide6 exposes void* as PyObject
                msg = ctypes.cast(address, ctypes.POINTER(wintypes.MSG)).contents
                if msg.message == WM_HOTKEY:
                    cb = self._callbacks.get(int(msg.wParam))
                    if cb is not None:
                        cb()
                        return True, 0
        except Exception:
            pass
        return False, 0


# ------------------------------------------------------------ autostart
def autostart_command() -> str:
    script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "run.pyw")
    pyw = sys.executable
    if pyw.lower().endswith("python.exe"):
        candidate = pyw[:-len("python.exe")] + "pythonw.exe"
        if os.path.isfile(candidate):
            pyw = candidate
    return f'"{pyw}" "{script}"'


def set_autostart(enabled: bool) -> None:
    import winreg

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, "Mitscreen", 0, winreg.REG_SZ, autostart_command())
            else:
                try:
                    winreg.DeleteValue(key, "Mitscreen")
                except FileNotFoundError:
                    pass
    except OSError:
        pass


def is_autostart_enabled() -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            value, _ = winreg.QueryValueEx(key, "Mitscreen")
            return bool(value)
    except OSError:
        return False


# ------------------------------------------------------------- shell helpers
def open_shell_target(target: str) -> bool:
    """Open a shell target such as `ms-settings:taskbar`, with a fallback."""
    try:
        os.startfile(target)  # type: ignore[attr-defined]
        return True
    except OSError:
        pass
    try:
        subprocess.Popen(["cmd", "/c", "start", "", target], close_fds=True)
        return True
    except OSError:
        return False


def open_in_explorer(target, select: bool = False) -> bool:
    """Open a folder, or reveal a file, with fallbacks that work when sandboxed.

    `os.startfile` goes through ShellExecute and is refused for a low-integrity
    process (error 5), so launching explorer.exe directly is the fallback.
    """
    from pathlib import Path

    path = Path(target)
    try:
        if not select:
            os.startfile(str(path))  # type: ignore[attr-defined]
            return True
    except OSError:
        pass

    arguments = ["explorer", f"/select,{path}" if select else str(path)]
    try:
        subprocess.Popen(arguments, close_fds=True)
        return True
    except OSError:
        pass

    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtWidgets import QApplication

        if QApplication.instance() is None:
            return False
        return bool(QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))))
    except Exception:
        return False
