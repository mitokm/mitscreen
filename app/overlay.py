"""Region selection overlay: frozen desktop, dimming, magnifier, action bar."""

from __future__ import annotations

import os

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QImage, QKeyEvent,
                           QMouseEvent, QPainter, QPen, QWheelEvent)
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from . import win32util


class ActionBar(QWidget):
    """Floating toolbar shown once a region has been selected."""

    action = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            """
            ActionBar { background: rgba(24,26,31,0.96); border: 1px solid #3a3f4a; border-radius: 10px; }
            QPushButton {
                color: #e8eaee; background: transparent; border: none; padding: 6px 10px;
                font-size: 13px; border-radius: 7px;
            }
            QPushButton:hover { background: #2f3542; }
            QPushButton#primary { background: #2563eb; color: white; font-weight: 600; }
            QPushButton#primary:hover { background: #3b7bff; }
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(2)
        for key, label, primary in (
            ("edit", "Sửa", True),
            ("copy", "Copy", False),
            ("save", "Lưu", False),
            ("record", "Quay", False),
            ("cancel", "Huỷ", False),
        ):
            btn = QPushButton(label)
            if primary:
                btn.setObjectName("primary")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, k=key: self.action.emit(k))
            layout.addWidget(btn)
        self.adjustSize()


class RegionOverlay(QWidget):
    """Full-virtual-screen selection window.

    Signals:
        finished(QRect, str, QImage) -- region in absolute screen pixels,
        requested action ('edit'|'copy'|'save'|'record'), and the desktop image.
        cancelled()
    """

    finished = Signal(QRect, str, QImage)
    cancelled = Signal()
    colorPicked = Signal(QColor)

    def __init__(self, mode: str = "region", image: QImage | None = None,
                 auto_action: str | None = None):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.mode = mode
        self.auto_action = auto_action
        self._desktop_rect = win32util.virtual_screen_rect()
        self._image = image if image is not None else self._grab()
        self._origin = QRect(self._desktop_rect)
        self._sel: QRect | None = None
        self._drag_origin: QPoint | None = None
        self._dragging = False
        self._cursor = QPointF(self._desktop_rect.center())
        self._hover_window: QRect | None = None
        self._action_bar: ActionBar | None = None
        self._done = False

        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setGeometry(self._desktop_rect)
        self.setWindowTitle("Mitscreen")
        self._bar = ActionBar(self)
        self._bar.action.connect(self._on_action)
        self._bar.hide()

    # ------------------------------------------------------------- helpers
    def _grab(self) -> QImage:
        from .imageutil import grab_desktop

        return grab_desktop()

    def _local(self, pos: QPointF) -> QPointF:
        return pos - QPointF(self._desktop_rect.topLeft())

    def _global(self, pt: QPointF) -> QPoint:
        return QPoint(int(pt.x() + self._desktop_rect.x()), int(pt.y() + self._desktop_rect.y()))

    def _selection_from(self, a: QPoint, b: QPoint) -> QRect:
        return QRect(a, b).normalized()

    # ---------------------------------------------------------------- show
    def begin(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        try:
            self.grabKeyboard()
        except Exception:
            pass

    # ---------------------------------------------------------------- paint
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(self.rect(), self._image)

        if self.mode == "color":
            self._draw_color_hint(painter)
            self._draw_magnifier(painter)
            return

        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))

        sel = self._sel
        if sel is not None and sel.width() > 0 and sel.height() > 0:
            painter.save()
            painter.setClipRect(sel)
            painter.drawImage(self.rect(), self._image)
            painter.restore()

            pen = QPen(QColor("#4f9cff"))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawRect(sel.adjusted(0, 0, -1, -1))

            if self._dragging:
                self._draw_size_badge(painter, sel)
                self._draw_guides(painter, sel)

        if self.mode == "window" and self._hover_window and not self._dragging:
            rect = self._hover_window.translated(-self._desktop_rect.topLeft())
            painter.save()
            painter.setPen(QPen(QColor("#4f9cff"), 2))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
            painter.fillRect(rect, QColor(79, 156, 255, 26))
            painter.restore()
            painter.setPen(QColor("#cfe0ff"))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(rect.adjusted(6, 4, -6, -4),
                             Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                             f"{rect.width()} × {rect.height()}")

        self._draw_hint(painter)
        self._draw_magnifier(painter)

    def _draw_hint(self, painter: QPainter) -> None:
        text = ("Chọn cửa sổ: di chuột rồi bấm" if self.mode == "window"
                else "Kéo để chọn vùng • bấm vào cửa sổ để chụp cửa sổ • Esc để huỷ")
        painter.setFont(QFont("Segoe UI", 9))
        metrics = painter.fontMetrics()
        w = metrics.horizontalAdvance(text) + 24
        h = metrics.height() + 12
        rect = QRectF((self.width() - w) / 2, 14, w, h)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 170))
        painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(QColor("#dbe3ee"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_color_hint(self, painter: QPainter) -> None:
        text = "Bấm để lấy mã màu • Esc để huỷ"
        painter.setFont(QFont("Segoe UI", 9))
        metrics = painter.fontMetrics()
        w = metrics.horizontalAdvance(text) + 24
        h = metrics.height() + 12
        rect = QRectF((self.width() - w) / 2, 14, w, h)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 180))
        painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(QColor("#dbe3ee"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_size_badge(self, painter: QPainter, sel: QRect) -> None:
        text = f"{sel.width()} × {sel.height()}"
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        metrics = painter.fontMetrics()
        w = metrics.horizontalAdvance(text) + 16
        h = metrics.height() + 8
        y = sel.top() - h - 6
        if y < 4:
            y = sel.top() + 6
        rect = QRectF(sel.left(), y, w, h)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(37, 99, 235, 235))
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_guides(self, painter: QPainter, sel: QRect) -> None:
        pen = QPen(QColor(255, 255, 255, 60))
        pen.setWidth(1)
        painter.setPen(pen)
        cursor = self._cursor.toPoint()
        painter.drawLine(QPoint(sel.left(), cursor.y()), QPoint(sel.right(), cursor.y()))
        painter.drawLine(QPoint(cursor.x(), sel.top()), QPoint(cursor.x(), sel.bottom()))

    def _draw_magnifier(self, painter: QPainter) -> None:
        if self._sel is not None and not self._dragging:
            return
        zoom_box = 140
        src = 15
        center = self._cursor.toPoint()
        half = src // 2
        x = center.x() - half
        y = center.y() - half
        x = max(0, min(self._image.width() - src, x))
        y = max(0, min(self._image.height() - src, y))
        sample = self._image.copy(x, y, src, src)

        bx = center.x() + 18
        by = center.y() + 18
        if bx + zoom_box + 12 > self.width():
            bx = center.x() - zoom_box - 18
        if by + zoom_box + 40 > self.height():
            by = center.y() - zoom_box - 40

        box = QRectF(bx, by, zoom_box, zoom_box)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.fillRect(box, QColor(15, 17, 21, 235))
        inner = box.adjusted(6, 6, -6, -6)
        painter.drawImage(inner, sample)
        painter.setPen(QPen(QColor("#4f9cff"), 2))
        painter.drawRect(box)
        # crosshair inside the loupe
        painter.setPen(QPen(QColor(79, 156, 255, 200), 1))
        cx, cy = inner.center().x(), inner.center().y()
        painter.drawLine(QPointF(inner.left(), cy), QPointF(inner.right(), cy))
        painter.drawLine(QPointF(cx, inner.top()), QPointF(cx, inner.bottom()))
        painter.restore()

        color = self._image.pixelColor(center)
        gx = int(center.x() + self._desktop_rect.x())
        gy = int(center.y() + self._desktop_rect.y())
        label = f"{gx}, {gy}   #{color.red():02X}{color.green():02X}{color.blue():02X}"
        painter.setFont(QFont("Consolas", 9))
        lbl_rect = QRectF(box.left(), box.bottom() + 6, zoom_box, 26)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 190))
        painter.drawRoundedRect(lbl_rect, 5, 5)
        painter.setPen(QColor("#e8eaee"))
        painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, label)

    # ---------------------------------------------------------------- mouse
    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.mode == "color":
            point = event.position().toPoint()
            color = self._image.pixelColor(point)
            self._done = True
            self._teardown()
            self.colorPicked.emit(color)
            return
        if self._sel is not None:
            # clicking outside a finished selection restarts it
            self._hide_bar()
            self._sel = None
            self.update()
            return
        self._drag_origin = event.position().toPoint()
        self._dragging = True
        self._sel = QRect(self._drag_origin, self._drag_origin)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._cursor = event.position()
        if self._dragging and self._drag_origin is not None:
            current = event.position().toPoint()
            self._sel = self._selection_from(self._drag_origin, current)
        elif self.mode == "window":
            gp = self._global(event.position())
            rect = win32util.window_at(int(gp.x()), int(gp.y()), {os.getpid()})
            if rect is not None:
                local = rect.translated(-self._desktop_rect.topLeft())
                if local.width() > 0 and local.height() > 0:
                    self._hover_window = local
                    self._sel = QRect(local)
                self.update()
                return
            self._hover_window = None
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton or not self._dragging:
            return
        self._dragging = False
        if self._drag_origin is None:
            return
        release = event.position().toPoint()
        moved = (release - self._drag_origin).manhattanLength()

        if moved < 6:
            gp = self._global(event.position())
            rect = win32util.window_at(int(gp.x()), int(gp.y()), {os.getpid()})
            if rect is not None:
                local = rect.translated(-self._desktop_rect.topLeft())
                self._sel = local
            else:
                self._sel = None
                self.update()
                return
        else:
            self._sel = self._selection_from(self._drag_origin, release)

        self._drag_origin = None
        if self._sel is None or self._sel.width() < 4 or self._sel.height() < 4:
            self._sel = None
            self.update()
            return
        self._hover_window = None
        if self.auto_action:
            # "capture and go": no extra click on an action bar
            self._accept(self.auto_action)
            return
        self._show_bar(self._sel)
        self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._sel is not None:
            self._accept(self.auto_action or "edit")

    # --------------------------------------------------------------- wheel
    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        # no zooming needed; swallow so the desktop behind never scrolls
        event.accept()

    # ------------------------------------------------------------- action bar
    def _show_bar(self, sel: QRect) -> None:
        bar = self._bar
        bar.adjustSize()
        w, h = bar.width(), bar.height()
        x = sel.left() + sel.width() - w
        y = sel.top() + sel.height() + 10
        if y + h > self.height() - 10:
            y = sel.top() - h - 10
        if y < 10:
            y = sel.top() + 10
        x = max(8, min(self.width() - w - 8, x))
        bar.move(int(x), int(y))
        bar.show()
        bar.raise_()

    def _hide_bar(self) -> None:
        self._bar.hide()

    def _on_action(self, action: str) -> None:
        if action == "cancel":
            self._cancel()
        else:
            self._accept(action)

    # ------------------------------------------------------------- keyboard
    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        if key == Qt.Key.Key_Escape:
            if self._sel is not None:
                self._sel = None
                self._hide_bar()
                self.update()
            else:
                self._cancel()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._sel is not None:
                self._accept(self.auto_action or "edit")
            return
        if key == Qt.Key.Key_A and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._sel = QRect(0, 0, self.width(), self.height())
            if self.auto_action:
                self._accept(self.auto_action)
                return
            self._show_bar(self._sel)
            self.update()
            return
        if self._sel is not None and key in (Qt.Key.Key_Left, Qt.Key.Key_Right,
                                             Qt.Key.Key_Up, Qt.Key.Key_Down):
            step = 10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            dx = (-step if key == Qt.Key.Key_Left else step if key == Qt.Key.Key_Right else 0)
            dy = (-step if key == Qt.Key.Key_Up else step if Qt.Key.Key_Down else 0)
            self._sel = self._sel.translated(dx, dy).intersected(self.rect())
            if not self.auto_action:
                self._show_bar(self._sel)
            self.update()
            return
        super().keyPressEvent(event)

    # ---------------------------------------------------------------- finish
    def _accept(self, action: str) -> None:
        if self._done or self._sel is None:
            return
        self._done = True
        rect = QRect(self._sel)
        rect = rect.intersected(QRect(0, 0, self.width(), self.height()))
        if rect.width() < 2 or rect.height() < 2:
            self._cancel()
            return
        absolute = rect.translated(self._desktop_rect.topLeft())
        image = self._image.copy(rect)
        self._teardown()
        self.finished.emit(absolute, action, image)

    def _cancel(self) -> None:
        if self._done:
            return
        self._done = True
        self._teardown()
        self.cancelled.emit()

    def _teardown(self) -> None:
        try:
            self.releaseKeyboard()
        except Exception:
            pass
        self._bar.hide()
        self.hide()
        self.deleteLater()

    def closeEvent(self, event) -> None:  # noqa: N802
        """Closing the overlay (Alt+F4, posted WM_CLOSE) must behave like Esc."""
        self._cancel()
        super().closeEvent(event)
