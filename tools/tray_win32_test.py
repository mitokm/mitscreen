"""Add a tray icon with the raw Win32 API (no Qt) to see whether the shell accepts it."""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "data" / "tray-win32.log"

user32 = ctypes.WinDLL("user32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
NIM_ADD = 0x00000000
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NIF_STATE = 0x00000008
NIS_HIDDEN = 0x00000001
IDI_APPLICATION = 32512

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, ctypes.c_uint,
                             wintypes.WPARAM, wintypes.LPARAM)


class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", GUID),
        ("hBalloonIcon", wintypes.HICON),
    ]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", ctypes.c_uint), ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR),
    ]


class NOTIFYICONIDENTIFIER(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND),
                ("uID", wintypes.UINT), ("guidItem", GUID)]


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def main() -> int:
    lines: list[str] = []

    def report() -> None:
        text = "\n".join(lines)
        print(text)
        try:
            LOG.write_text(text, encoding="utf-8")
        except OSError:
            pass

    hinst = kernel32.GetModuleHandleW(None)

    def wndproc(hwnd, msg, wparam, lparam):
        if msg == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    proc = WNDPROC(wndproc)
    wc = WNDCLASSW()
    wc.style = 0
    wc.lpfnWndProc = proc
    wc.hInstance = hinst
    wc.lpszClassName = "MitscreenTrayProbe"
    atom = user32.RegisterClassW(ctypes.byref(wc))
    lines.append(f"RegisterClass atom={atom} err={ctypes.get_last_error()}")

    hwnd = user32.CreateWindowExW(0, "MitscreenTrayProbe", "probe", 0,
                                  0, 0, 0, 0, None, None, hinst, None)
    lines.append(f"hwnd={hwnd}")

    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = hwnd
    nid.uID = 1
    nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
    nid.uCallbackMessage = 0x0400 + 1
    nid.hIcon = user32.LoadIconW(None, ctypes.c_wchar_p(IDI_APPLICATION))
    nid.szTip = "MitscreenWin32Probe"
    ok = shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
    lines.append(f"NIM_ADD ok={bool(ok)} err={ctypes.get_last_error()}")

    # is it registered?
    ident = NOTIFYICONIDENTIFIER()
    ident.cbSize = ctypes.sizeof(NOTIFYICONIDENTIFIER)
    ident.hWnd = hwnd
    ident.uID = 1
    rect = RECT()
    result = shell32.Shell_NotifyIconGetRect(ctypes.byref(ident), ctypes.byref(rect))
    lines.append(f"GetRect result={result} rect=({rect.left},{rect.top})")

    # pump the message loop briefly so the shell can process the add
    deadline = time.time() + 4
    msg = wintypes.MSG()
    while time.time() < deadline:
        while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        time.sleep(0.02)

    result2 = shell32.Shell_NotifyIconGetRect(ctypes.byref(ident), ctypes.byref(rect))
    lines.append(f"GetRect after pump result={result2}")

    shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
    lines.append("NIM_DELETE done")
    user32.DestroyWindow(hwnd)
    report()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
