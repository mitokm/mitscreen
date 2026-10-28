"""Screen recording through ffmpeg (gdigrab)."""

from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QProcess, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from .config import Settings
from .recframe import RecordingFrame


def find_ffmpeg() -> str | None:
    # bundled copies first: next to the exe (installer layout) or in the
    # PyInstaller bundle, then PATH, then the classic fixed locations
    bundled: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundled.append(Path(meipass) / "ffmpeg.exe")
    bundled.append(Path(sys.executable).resolve().parent / "ffmpeg.exe")
    bundled.append(Path(__file__).resolve().parent.parent / "ffmpeg.exe")
    for path in bundled:
        if path.is_file():
            return str(path)
    candidate = shutil.which("ffmpeg")
    if candidate:
        return candidate
    for path in (r"C:\ffmpeg\bin\ffmpeg.exe", r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"):
        if os.path.isfile(path):
            return path
    return None


class StopBar(QWidget):
    """Small always-on-top controller shown while recording."""

    stop_clicked = Signal()

    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            """
            StopBar { background: rgba(20,22,27,0.96); border: 1px solid #3b4049; border-radius: 10px; }
            QLabel { color: #e8eaee; font-size: 13px; }
            QPushButton { background: #dc2626; color: white; border: none; border-radius: 7px;
                          padding: 6px 14px; font-weight: 600; }
            QPushButton:hover { background: #ef4444; }
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 10, 8)
        layout.setSpacing(10)
        self.dot = QLabel("●")
        self.dot.setStyleSheet("color: #ef4444; font-size: 15px;")
        self.time_label = QLabel("00:00")
        self.hint = QLabel("đang quay")
        self.hint.setStyleSheet("color: #9aa3b2; font-size: 12px;")
        button = QPushButton("Dừng")
        button.clicked.connect(self.stop_clicked.emit)
        layout.addWidget(self.dot)
        layout.addWidget(self.time_label)
        layout.addWidget(self.hint)
        layout.addWidget(button)
        self.adjustSize()
        self._blink = False
        self._timer = QTimer(self)
        self._timer.setInterval(600)
        self._timer.timeout.connect(self._toggle_dot)
        self._timer.start()

    def _toggle_dot(self) -> None:
        self._blink = not self._blink
        self.dot.setStyleSheet(
            "color: %s; font-size: 15px;" % ("#ef4444" if self._blink else "#7f1d1d"))

    def set_elapsed(self, seconds: int) -> None:
        self.time_label.setText(f"{seconds // 60:02d}:{seconds % 60:02d}")


class Recorder(QProcess):
    """Thin wrapper around an ffmpeg gdigrab capture."""

    stopped = Signal(Path)
    failure = Signal(str)

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._output: Path | None = None
        self._bar: StopBar | None = None
        self._frame: RecordingFrame | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._elapsed = 0
        self._finishing = False
        self.finished.connect(self._on_finished)
        self.errorOccurred.connect(self._on_error)
        self.readyReadStandardOutput.connect(self._drain)

    # ---------------------------------------------------------------- start
    def start_recording(self, rect: QRect) -> bool:
        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            self.failure.emit("Không tìm thấy ffmpeg. Cài ffmpeg hoặc đặt ffmpeg.exe vào PATH.")
            return False
        if self.state() != QProcess.ProcessState.NotRunning:
            return False

        width = rect.width() - (rect.width() % 2)
        height = rect.height() - (rect.height() % 2)
        if width < 16 or height < 16:
            self.failure.emit("Vùng quay quá nhỏ.")
            return False

        directory = self.settings.save_path
        directory.mkdir(parents=True, exist_ok=True)
        self._output = directory / f"rec-{datetime.now():%Y%m%d-%H%M%S}.mp4"

        args = [
            "-hide_banner", "-loglevel", "error", "-y",
            "-f", "gdigrab",
            "-draw_mouse", "1" if self.settings.show_cursor_in_recordings else "0",
            "-framerate", str(self.settings.record_fps),
            "-offset_x", str(rect.x()), "-offset_y", str(rect.y()),
            "-video_size", f"{width}x{height}",
            "-i", "desktop",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", str(self.settings.record_crf),
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(self._output),
        ]
        self.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.start(ffmpeg, args)
        if not self.waitForStarted(4000):
            self.failure.emit("Không khởi động được ffmpeg.")
            return False
        self._elapsed = 0
        self._finishing = False
        self._timer.start()
        self._show_frame(QRect(rect.x(), rect.y(), width, height))
        self._show_bar(rect)
        return True

    def _show_frame(self, rect: QRect) -> None:
        """Red border around the recorded area (drawn outside it)."""
        frame = RecordingFrame()
        frame.show_for(rect)
        self._frame = frame

    def _show_bar(self, rect: QRect) -> None:
        bar = StopBar()
        bar.stop_clicked.connect(self.stop_recording)
        bar.adjustSize()
        screen = QGuiApplication.screenAt(rect.center()) or QGuiApplication.primaryScreen()
        geometry = screen.availableGeometry() if screen else rect
        x = min(max(geometry.left() + 12, rect.right() - bar.width() - 12),
                geometry.right() - bar.width() - 12)
        below = rect.bottom() + 10
        above = rect.top() - bar.height() - 10
        if below + bar.height() < geometry.bottom():
            y = below
        elif above > geometry.top():
            y = above
        else:
            y = geometry.bottom() - bar.height() - 12
        bar.move(int(x), int(y))
        bar.show()
        bar.raise_()
        self._bar = bar

    # ----------------------------------------------------------------- stop
    def stop_recording(self) -> None:
        if self.state() == QProcess.ProcessState.NotRunning:
            return
        self._finishing = True
        try:
            self.write(b"q")
            self.closeWriteChannel()
        except Exception:
            pass
        QTimer.singleShot(4000, self._force_terminate)

    def _force_terminate(self) -> None:
        if self.state() == QProcess.ProcessState.NotRunning:
            return
        self.terminate()
        QTimer.singleShot(2500, self._force_kill)

    def _force_kill(self) -> None:
        if self.state() != QProcess.ProcessState.NotRunning:
            self.kill()

    # -------------------------------------------------------------- signals
    def _tick(self) -> None:
        self._elapsed += 1
        if self._bar is not None:
            self._bar.set_elapsed(self._elapsed)

    def _drain(self) -> None:
        self.readAllStandardOutput()

    def _on_error(self, error) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self.failure.emit("Không chạy được ffmpeg.")

    def _on_finished(self, exit_code: int, _status) -> None:
        self._timer.stop()
        if self._bar is not None:
            self._bar.close()
            self._bar = None
        if self._frame is not None:
            self._frame.close()
            self._frame = None
        output = self._output
        log = bytes(self.readAllStandardOutput()).decode("utf-8", "replace").strip()
        if output is not None and output.is_file() and output.stat().st_size > 1024:
            self.stopped.emit(output)
        else:
            self.failure.emit(log[-600:] if log else f"ffmpeg kết thúc với mã {exit_code}.")
        self._output = None
        self._finishing = False
