"""Folder-opening fallbacks: ShellExecute refused -> launch explorer directly."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    from app import win32util

    failures = []

    def check(name, cond, detail=""):
        print(f"[{'ok  ' if cond else 'FAIL'}] {name}{(' — ' + detail) if not cond else ''}")
        if not cond:
            failures.append(name)

    folder = Path(tempfile.mkdtemp(prefix="mitscreen-folder-"))
    target_file = folder / "anh.png"
    target_file.write_bytes(b"x")

    real_startfile = getattr(os, "startfile", None)
    real_popen = win32util.subprocess.Popen
    calls: list[list[str]] = []

    class FakeProcess:
        pid = 4242

    def fake_popen(args, **kwargs):
        calls.append(list(args))
        return FakeProcess()

    try:
        # ---- normal path: os.startfile works, no fallback needed ----------
        used = {"startfile": 0}

        def good_startfile(path):
            used["startfile"] += 1

        os.startfile = good_startfile  # type: ignore[attr-defined]
        win32util.subprocess.Popen = fake_popen
        check("startfile path returns True", win32util.open_in_explorer(folder) is True)
        check("startfile used when allowed", used["startfile"] == 1, str(used))
        check("no fallback when startfile works", calls == [], str(calls))

        # ---- sandboxed path: access denied, explorer launched directly ----
        def denied_startfile(path):
            raise PermissionError(13, "Access is denied")

        os.startfile = denied_startfile  # type: ignore[attr-defined]
        calls.clear()
        check("fallback returns True", win32util.open_in_explorer(folder) is True)
        check("explorer was launched with the folder",
              calls and calls[0] == ["explorer", str(folder)], str(calls))

        calls.clear()
        check("reveal a file returns True",
              win32util.open_in_explorer(target_file, select=True) is True)
        check("reveal passes /select",
              calls and calls[0] == ["explorer", f"/select,{target_file}"], str(calls))

        # ---- shell target (ms-settings:) ---------------------------------
        calls.clear()
        check("shell target fallback works",
              win32util.open_shell_target("ms-settings:taskbar") is True)
        check("shell target falls back to cmd start",
              calls and calls[0][:4] == ["cmd", "/c", "start", ""], str(calls))

        # ---- everything refused ------------------------------------------
        os.startfile = denied_startfile  # type: ignore[attr-defined]

        def failing_popen(args, **kwargs):
            raise OSError("blocked")

        win32util.subprocess.Popen = failing_popen
        check("all paths blocked returns False", win32util.open_in_explorer(folder) is False)
    finally:
        if real_startfile is not None:
            os.startfile = real_startfile  # type: ignore[attr-defined]
        win32util.subprocess.Popen = real_popen

    print()
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("folder-opening checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
