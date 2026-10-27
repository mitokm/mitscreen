"""A red frame drawn around the region being recorded.

The frame lives *outside* the captured rectangle so it never appears in the
recording: the window has a masked hole exactly where the video is taken.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QRegion
from PySide6.QtWidgets import QWidget

BORDER = 3          # thickness of the red ring
GAP = 2             # distance between the ring and the recorded area
COLOR = "#ef4444"


class RecordingFrame(QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
            | Qt.WindowType.WindowTransparentForInput,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWindowTitle("Mitscreen — vùng đang quay")
        self._area = QRect()

    # ---------------------------------------------------------------- public
    def show_for(self, area: QRect) -> None:
        """`area` is the recorded rectangle in physical screen pixels."""
        self._area = QRect(area)
        margin = BORDER + GAP
        outer = area.adjusted(-margin, -margin, margin, margin)
        self.setGeometry(outer)
        # a hole exactly over the recorded pixels keeps the video clean
        inner = QRegion(margin, margin, area.width(), area.height())
        self.setMask(QRegion(self.rect()).subtracted(inner))
        self.show()
        self.raise_()

    def refresh_geometry(self) -> None:
        if not self._area.isNull():
            self.show_for(self._area)

    # --------------------------------------------------------------- painting
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), QColor(COLOR))
        painter.end()

    # ----------------------------------------------------------------- events
    def closeEvent(self, event) -> None:  # noqa: N802
        self._area = QRect()
        super().closeEvent(event)
