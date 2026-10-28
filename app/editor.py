"""The screenshot editor: crop, annotate, effects, save / copy / print."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, QSizeF, Qt, Signal
from PySide6.QtGui import (QAction, QActionGroup, QBrush, QColor, QFont, QImage,
                           QKeySequence, QPainter, QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import (QApplication, QColorDialog, QDialog, QDialogButtonBox,
                               QFileDialog, QFormLayout, QInputDialog, QLabel, QLineEdit,
                               QMainWindow, QMenu, QMessageBox, QSlider, QSpinBox,
                               QStatusBar, QToolBar, QToolButton, QWidget)

from . import icons, imageutil, library
from .config import Settings

TOOLS: list[tuple[str, str, str]] = [
    ("crop", "Cắt ảnh", "C"),
    ("cutout", "Cắt bỏ & nối", "U"),
    ("arrow", "Mũi tên", "A"),
    ("line", "Đường thẳng", "L"),
    ("rect", "Hình chữ nhật", "R"),
    ("ellipse", "Hình tròn / elip", "E"),
    ("pen", "Bút vẽ", "P"),
    ("highlight", "Bút dạ quang", "H"),
    ("text", "Chữ", "T"),
    ("blur", "Làm mờ", "B"),
    ("mosaic", "Mosaic", "X"),
    ("badge", "Số thứ tự", "N"),
]

PALETTE = ["#ff3b30", "#ff9500", "#ffd60a", "#34c759", "#32ade6",
           "#2563eb", "#af52de", "#ffffff", "#000000"]

ACCENT = "#2563eb"


@dataclass
class ToolState:
    tool: str = "arrow"
    color: str = "#ff3b30"
    width: int = 4
    font_size: int = 24
    next_badge: int = 1


# --------------------------------------------------------------------------
# canvas
# --------------------------------------------------------------------------
class Canvas(QWidget):
    changed = Signal()
    viewChanged = Signal()
    toolChanged = Signal(str)

    TOOL_KEYS = {
        "c": "crop", "u": "cutout", "a": "arrow", "l": "line", "r": "rect", "e": "ellipse",
        "p": "pen", "h": "highlight", "t": "text", "b": "blur", "x": "mosaic",
        "n": "badge",
    }

    def __init__(self, image: QImage, state: ToolState, parent=None):
        super().__init__(parent)
        self._img = image.convertToFormat(QImage.Format.Format_ARGB32)
        self.state = state
        self._undo: list[QImage] = []
        self._redo: list[QImage] = []
        self._zoom = 1.0
        self._offset = QPointF(0, 0)
        self._drag_start: QPointF | None = None
        self._drag_cur: QPointF | None = None
        self._points: list[QPointF] = []
        self._panning = False
        self._pan_anchor = QPointF()
        self._pan_offset = QPointF()
        self._space_down = False
        self._text_edit: QLineEdit | None = None
        self._text_pos = QPointF()
        self._text_committing = False
        self._fitted = False
        self._checker: QBrush | None = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMinimumSize(320, 240)

    # ------------------------------------------------------------ geometry
    def image(self) -> QImage:
        return self._img

    def set_image(self, image: QImage) -> None:
        self._img = image.convertToFormat(QImage.Format.Format_ARGB32)
        self.fit_to_view()
        self.update()

    def _to_image(self, pos: QPointF) -> QPointF:
        if self._zoom <= 0:
            return QPointF()
        return (pos - self._offset) / self._zoom

    def _to_widget(self, pt: QPointF) -> QPointF:
        return pt * self._zoom + self._offset

    def fit_to_view(self) -> None:
        if self.width() < 10 or self.height() < 10:
            return
        self._zoom = min(self.width() / self._img.width(), self.height() / self._img.height()) * 0.96
        self._zoom = max(0.02, min(8.0, self._zoom))
        self._center()

    def _center(self) -> None:
        w = self._img.width() * self._zoom
        h = self._img.height() * self._zoom
        self._offset = QPointF((self.width() - w) / 2, (self.height() - h) / 2)

    def zoom_to(self, zoom: float, anchor: QPointF | None = None) -> None:
        anchor = anchor if anchor is not None else QPointF(self.width() / 2, self.height() / 2)
        img_pt = self._to_image(anchor)
        self._zoom = max(0.02, min(16.0, zoom))
        self._offset = anchor - img_pt * self._zoom
        self.update()

    def zoom_fit(self) -> None:
        self.fit_to_view()
        self.update()

    def zoom_100(self) -> None:
        self.zoom_to(1.0)

    # --------------------------------------------------------------- undo
    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def _push_undo(self) -> None:
        self._undo.append(self._img.copy())
        if len(self._undo) > 24:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self) -> None:
        if not self._undo:
            return
        self._redo.append(self._img.copy())
        self._img = self._undo.pop()
        self.update()
        self.changed.emit()

    def redo(self) -> None:
        if not self._redo:
            return
        self._undo.append(self._img.copy())
        self._img = self._redo.pop()
        self.update()
        self.changed.emit()

    # --------------------------------------------------------------- paint
    def _checker_brush(self) -> QBrush:
        if self._checker is None:
            tile = QPixmap(16, 16)
            tile.fill(QColor("#4a5059"))
            painter = QPainter(tile)
            painter.fillRect(0, 0, 8, 8, QColor("#3a4048"))
            painter.fillRect(8, 8, 8, 8, QColor("#3a4048"))
            painter.end()
            self._checker = QBrush(tile)
        return self._checker

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0e1013"))
        target = QRectF(self._offset, QSizeF(self._img.width() * self._zoom,
                                             self._img.height() * self._zoom))
        # checkerboard shows through transparent pixels left by a cutout
        painter.fillRect(target, self._checker_brush())
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self._zoom < 2.0)
        painter.drawImage(target, self._img)

        # subtle 1px frame around the picture
        painter.setPen(QPen(QColor("#333842"), 1))
        painter.drawRect(target.adjusted(-0.5, -0.5, 0.5, 0.5))

        if self._drag_start is not None and self._drag_cur is not None:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.translate(self._offset)
            painter.scale(self._zoom, self._zoom)
            self._paint_shape(painter, self.state.tool, self._drag_start, self._drag_cur,
                              self._points, preview=True)
            painter.restore()

    # ------------------------------------------------------------- shapes
    def _shape_pen(self, preview: bool = False) -> QPen:
        color = QColor(self.state.color)
        pen = QPen(color)
        pen.setWidthF(max(1.0, self.state.width))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return pen

    def _paint_shape(self, painter: QPainter, tool: str, p1: QPointF, p2: QPointF,
                     points: list[QPointF] | None = None, preview: bool = False) -> None:
        rect = QRectF(p1, p2).normalized()
        if tool == "arrow":
            self._paint_arrow(painter, p1, p2)
        elif tool == "line":
            painter.setPen(self._shape_pen(preview))
            painter.drawLine(p1, p2)
        elif tool == "rect":
            painter.setPen(self._shape_pen(preview))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            radius = min(6.0, rect.width() / 6, rect.height() / 6)
            painter.drawRoundedRect(rect, radius, radius)
        elif tool == "ellipse":
            painter.setPen(self._shape_pen(preview))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(rect)
        elif tool == "pen":
            pts = points or [p1, p2]
            if len(pts) >= 2:
                path = QPainterPath(pts[0])
                for pt in pts[1:]:
                    path.lineTo(pt)
                painter.setPen(self._shape_pen(preview))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)
        elif tool == "highlight":
            color = QColor(self.state.color)
            color.setAlpha(90)
            pen = QPen(color)
            pen.setWidthF(max(6.0, self.state.width * 4))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(p1, p2)
        elif tool == "crop":
            painter.setPen(QPen(QColor(255, 255, 255, 210), 1, Qt.PenStyle.DashLine))
            painter.drawRect(rect)
            painter.fillRect(rect, QColor(255, 255, 255, 26))
            # darken outside
            painter.setBrush(Qt.BrushStyle.NoBrush)
        elif tool == "cutout":
            band, _horizontal = self._cutout_band(p1, p2)
            painter.setPen(QPen(QColor(229, 72, 77, 235), 1.6, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(229, 72, 77, 60))
            painter.drawRect(band)
            # the two edges that will be joined
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255, 220), 2))
            if band.width() >= band.height():
                painter.drawLine(band.left(), band.top(), band.right(), band.top())
            else:
                painter.drawLine(band.left(), band.top(), band.left(), band.bottom())
        elif tool in ("blur", "mosaic"):
            painter.setPen(QPen(QColor(ACCENT), 1.4))
            painter.setBrush(QColor(37, 99, 235, 40))
            painter.drawRect(rect)

    def _paint_arrow(self, painter: QPainter, p1: QPointF, p2: QPointF) -> None:
        pen = self._shape_pen()
        painter.setPen(pen)
        painter.setBrush(QColor(self.state.color))
        dx, dy = p2.x() - p1.x(), p2.y() - p1.y()
        length = math.hypot(dx, dy)
        if length < 1:
            return
        head = max(12.0, self.state.width * 4.2)
        if head > length:
            head = length
        ux, uy = dx / length, dy / length
        base = QPointF(p2.x() - ux * head, p2.y() - uy * head)
        painter.drawLine(p1, base)
        half = head * 0.52
        left = QPointF(base.x() - uy * half, base.y() + ux * half)
        right = QPointF(base.x() + uy * half, base.y() - ux * half)
        head_path = QPainterPath(p2)
        head_path.lineTo(left)
        head_path.lineTo(right)
        head_path.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(head_path)

    # ---------------------------------------------------------- committing
    def _commit(self) -> None:
        if self._drag_start is None or self._drag_cur is None:
            return
        tool = self.state.tool
        p1, p2 = self._drag_start, self._drag_cur
        self._push_undo()

        if tool == "crop":
            rect = QRectF(p1, p2).normalized().toRect()
            rect = rect.intersected(QRect(0, 0, self._img.width(), self._img.height()))
            if rect.width() > 4 and rect.height() > 4:
                self._img = self._img.copy(rect)
                self.fit_to_view()
        elif tool == "cutout":
            band, horizontal = self._cutout_band(p1, p2)
            thickness = band.height() if horizontal else band.width()
            if thickness >= 6:
                self._apply_cutout(band, horizontal)
            else:
                self._undo.pop()  # nothing to cut, drop the empty undo step
        elif tool in ("blur", "mosaic"):
            rect = QRectF(p1, p2).normalized().toRect()
            if rect.width() > 3 and rect.height() > 3:
                if tool == "blur":
                    radius = max(6, min(30, int(min(rect.width(), rect.height()) / 6)))
                    self._img = imageutil.blur_region(self._img, rect, radius)
                else:
                    block = max(6, min(24, int(min(rect.width(), rect.height()) / 12)))
                    self._img = imageutil.pixelate_region(self._img, rect, block)
        else:
            painter = QPainter(self._img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            self._paint_shape(painter, tool, p1, p2, self._points)
            painter.end()

        self._drag_start = None
        self._drag_cur = None
        self._points = []
        self.update()
        self.changed.emit()
        self.setFocus()

    # --------------------------------------------------------------- cutout
    def _cutout_band(self, p1: QPointF, p2: QPointF) -> tuple[QRect, bool]:
        """Return the band that a cutout removes and whether it is horizontal.

        A cut removes a strip and the remaining halves are joined together, so the
        strip always spans the full width (join vertically) or the full height
        (join horizontally).  The drag's wider dimension decides the direction.
        """
        rect = QRectF(p1, p2).normalized().toRect()
        rect = rect.intersected(QRect(0, 0, self._img.width(), self._img.height()))
        if rect.width() >= rect.height():
            return QRect(0, rect.top(), self._img.width(), rect.height()), True
        return QRect(rect.left(), 0, rect.width(), self._img.height()), False

    def _apply_cutout(self, band: QRect, horizontal: bool) -> None:
        """Remove the band and pull the remaining parts together."""
        img = self._img
        width, height = img.width(), img.height()
        if horizontal:
            top, thickness = band.top(), band.height()
            if thickness <= 0 or thickness >= height:
                return
            out = QImage(width, height - thickness, QImage.Format.Format_ARGB32)
            out.fill(QColor(0, 0, 0, 0))
            painter = QPainter(out)
            painter.drawImage(0, 0, img, 0, 0, width, top)
            painter.drawImage(0, top, img, 0, top + thickness, width, height - top - thickness)
            painter.end()
        else:
            left, thickness = band.left(), band.width()
            if thickness <= 0 or thickness >= width:
                return
            out = QImage(width - thickness, height, QImage.Format.Format_ARGB32)
            out.fill(QColor(0, 0, 0, 0))
            painter = QPainter(out)
            painter.drawImage(0, 0, img, 0, 0, left, height)
            painter.drawImage(left, 0, img, left + thickness, 0, width - left - thickness, height)
            painter.end()
        self._img = out
        self.fit_to_view()

    # ----------------------------------------------------------------- text
    def _begin_text(self, pos: QPointF) -> None:
        self._end_text(commit=True)
        editor = QLineEdit(self)
        editor.setPlaceholderText("Nhập chữ rồi Enter…")
        editor.setStyleSheet(
            "QLineEdit { background: rgba(20,22,27,235); color: %s; border: 1px solid %s;"
            " border-radius: 6px; padding: 4px 6px; }" % (self.state.color, ACCENT)
        )
        editor.setFont(QFont("Segoe UI", max(9, int(self.state.font_size * self._zoom * 0.6))))
        editor.adjustSize()
        widget_pos = self._to_widget(pos)
        editor.move(int(widget_pos.x()), int(widget_pos.y()) - editor.height() - 2)
        editor.resize(max(180, editor.width()), editor.height())
        editor.returnPressed.connect(lambda: self._end_text(commit=True))
        editor.editingFinished.connect(lambda: self._end_text(commit=True))
        editor.show()
        editor.setFocus()
        self._text_edit = editor
        self._text_pos = pos

    def _end_text(self, commit: bool) -> None:
        if self._text_edit is None or self._text_committing:
            return
        self._text_committing = True
        editor = self._text_edit
        text = editor.text().strip()
        pos = self._text_pos
        self._text_edit = None
        editor.hide()
        editor.deleteLater()
        self._text_committing = False
        if not commit or not text:
            self.setFocus()
            return
        self._push_undo()
        painter = QPainter(self._img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        font = QFont("Segoe UI", self.state.font_size)
        font.setPixelSize(max(10, int(self.state.font_size)))
        font.setWeight(QFont.Weight.DemiBold)
        path = QPainterPath()
        path.addText(pos, font, text)
        painter.setPen(QPen(QColor(0, 0, 0, 160), max(2.0, self.state.width * 0.7)))
        painter.drawPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.state.color))
        painter.drawPath(path)
        painter.end()
        self.update()
        self.changed.emit()
        self.setFocus()

    # ---------------------------------------------------------------- mouse
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton and self._space_down
        ):
            self._panning = True
            self._pan_anchor = event.position()
            self._pan_offset = QPointF(self._offset)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._end_text(commit=True)
        pos = self._to_image(event.position())
        if self.state.tool == "text":
            self._begin_text(pos)
            return
        if self.state.tool == "badge":
            self._draw_badge(pos)
            return
        self._drag_start = pos
        self._drag_cur = pos
        self._points = [pos]
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._panning:
            delta = event.position() - self._pan_anchor
            self._offset = self._pan_offset + delta
            self.update()
            return
        if self._drag_start is None:
            return
        pos = self._to_image(event.position())
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier and self.state.tool in ("line", "arrow"):
            start = self._drag_start
            dx, dy = pos.x() - start.x(), pos.y() - start.y()
            angle = round(math.atan2(dy, dx) / (math.pi / 4)) * (math.pi / 4)
            length = math.hypot(dx, dy)
            pos = QPointF(start.x() + math.cos(angle) * length, start.y() + math.sin(angle) * length)
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier and self.state.tool in ("rect", "ellipse", "crop"):
            start = self._drag_start
            side = max(abs(pos.x() - start.x()), abs(pos.y() - start.y()))
            pos = QPointF(start.x() + math.copysign(side, pos.x() - start.x()),
                          start.y() + math.copysign(side, pos.y() - start.y()))
        self._drag_cur = pos
        if self.state.tool == "pen":
            if not self._points or (pos - self._points[-1]).manhattanLength() > 0.6:
                self._points.append(pos)
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.CrossCursor)
            return
        if event.button() != Qt.MouseButton.LeftButton or self._drag_start is None:
            return
        self._commit()

    def wheelEvent(self, event) -> None:  # noqa: N802
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
            self.zoom_to(self._zoom * factor, event.position())
        else:
            self._offset = self._offset + QPointF(0, event.angleDelta().y() * 0.6)
            self.update()
        self.viewChanged.emit()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._fitted:
            self._fitted = True
            self.fit_to_view()
            self.viewChanged.emit()

    # ------------------------------------------------------------- badge
    def _draw_badge(self, pos: QPointF) -> None:
        self._push_undo()
        radius = max(12.0, self.state.width * 4.0)
        painter = QPainter(self._img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor("#ffffff"), max(2.0, radius * 0.12)))
        painter.setBrush(QColor(self.state.color))
        center = QPointF(pos.x() + radius, pos.y() + radius)
        painter.drawEllipse(center, radius, radius)
        font = QFont("Segoe UI", 10)
        font.setPixelSize(int(radius * 1.15))
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2),
                         Qt.AlignmentFlag.AlignCenter, str(self.state.next_badge))
        painter.end()
        self.state.next_badge += 1
        self.update()
        self.changed.emit()

    # ------------------------------------------------------------- keyboard
    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Space:
            self._space_down = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            return
        if event.key() == Qt.Key.Key_Escape:
            if self._text_edit is not None:
                self._end_text(commit=False)
                return
            if self._drag_start is not None:
                self._drag_start = None
                self._drag_cur = None
                self._points = []
                self.update()
                return
        modifiers = event.modifiers()
        if not (modifiers & (Qt.KeyboardModifier.ControlModifier
                             | Qt.KeyboardModifier.AltModifier
                             | Qt.KeyboardModifier.MetaModifier)):
            key = event.text().lower()
            if key in self.TOOL_KEYS:
                self.toolChanged.emit(self.TOOL_KEYS[key])
                return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Space:
            self._space_down = False
            self.setCursor(Qt.CursorShape.CrossCursor)
            return
        super().keyReleaseEvent(event)


# --------------------------------------------------------------------------
# small dialogs
# --------------------------------------------------------------------------
class ResizeDialog(QDialog):
    def __init__(self, width: int, height: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Đổi kích thước")
        self._w, self._h = width, height
        form = QFormLayout(self)
        self.mode = QSpinBox()
        self.mode.setRange(1, 400)
        self.mode.setValue(100)
        self.mode.setSuffix(" %")
        self.width_box = QSpinBox()
        self.width_box.setRange(16, 20000)
        self.width_box.setValue(width)
        self.width_box.setSuffix(" px")
        self.height_box = QSpinBox()
        self.height_box.setRange(16, 20000)
        self.height_box.setValue(height)
        self.height_box.setSuffix(" px")
        form.addRow("Theo phần trăm:", self.mode)
        form.addRow("Chiều rộng:", self.width_box)
        form.addRow("Chiều cao:", self.height_box)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self.mode.valueChanged.connect(self._from_percent)

    def _from_percent(self, value: int) -> None:
        self.width_box.blockSignals(True)
        self.height_box.blockSignals(True)
        self.width_box.setValue(max(16, int(self._w * value / 100)))
        self.height_box.setValue(max(16, int(self._h * value / 100)))
        self.width_box.blockSignals(False)
        self.height_box.blockSignals(False)

    def result_size(self) -> tuple[int, int]:
        return self.width_box.value(), self.height_box.value()


# --------------------------------------------------------------------------
# main editor window
# --------------------------------------------------------------------------
class EditorWindow(QMainWindow):
    saved = Signal(Path)
    closed = Signal()

    def __init__(self, image: QImage, settings: Settings, origin: str = "",
                 already_copied: bool = False, path: Path | None = None):
        super().__init__()
        self.settings = settings
        self.origin = origin
        self.state = ToolState(color=PALETTE[0], width=4, font_size=24)
        self.canvas = Canvas(image, self.state, self)
        self.setCentralWidget(self.canvas)
        self._path: Path | None = path
        self._dirty = False
        self._copied = already_copied
        self._tool_actions: dict[str, QAction] = {}

        self.setWindowTitle(f"Mitscreen — {path.name}" if path else "Mitscreen — Ảnh mới")
        self.resize(1180, 780)
        self.setWindowIcon(icons.icon("snap"))
        self._build_toolbars()
        self._build_status()
        self.canvas.changed.connect(self._on_changed)
        self.canvas.viewChanged.connect(self._refresh_status)
        self.canvas.toolChanged.connect(self._on_tool_from_canvas)
        self.canvas.fit_to_view()
        self.canvas.setFocus()
        if already_copied:
            self.statusBar().showMessage("Đã copy vào clipboard — chỉnh sửa rồi Ctrl+S để lưu", 5000)
        elif path is not None:
            self.statusBar().showMessage(
                f"Đã tự lưu: {path} — sửa xong bấm Ctrl+S để ghi đè lên bản này", 6000)

    # ------------------------------------------------------------ toolbars
    def _build_toolbars(self) -> None:
        top = QToolBar("Chính", self)
        top.setMovable(False)
        top.setIconSize(QSize(20, 20))
        top.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, top)

        self.act_undo = QAction(icons.icon("undo"), "Hoàn tác (Ctrl+Z)", self)
        self.act_undo.triggered.connect(self.canvas.undo)
        self.act_redo = QAction(icons.icon("redo"), "Làm lại (Ctrl+Y)", self)
        self.act_redo.triggered.connect(self.canvas.redo)
        self.act_copy = QAction(icons.icon("copy"), "Copy (Ctrl+C)", self)
        self.act_copy.triggered.connect(self.copy_to_clipboard)
        self.act_save = QAction(icons.icon("save"), "Lưu (Ctrl+S)", self)
        self.act_save.triggered.connect(lambda: self.save())
        self.act_save_as = QAction("Lưu thành…", self)
        self.act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.act_save_as.triggered.connect(lambda: self.save(save_as=True))
        self.act_print = QAction(icons.icon("print"), "In (Ctrl+P)", self)
        self.act_print.triggered.connect(self.print_image)
        self.act_rename = QAction(icons.icon("text"), "Đổi tên tệp (F2)", self)
        self.act_rename.setShortcut(QKeySequence("F2"))
        self.act_rename.triggered.connect(self.rename_prompt)
        self.act_close = QAction(icons.icon("close"), "Đóng (Esc)", self)
        self.act_close.triggered.connect(self.close)

        for action in (self.act_undo, self.act_redo):
            top.addAction(action)
        top.addSeparator()
        for action in (self.act_copy, self.act_save, self.act_save_as, self.act_rename,
                       self.act_print):
            top.addAction(action)
        top.addSeparator()

        # effects menu
        effects_btn = QToolButton()
        effects_btn.setText("Hiệu ứng")
        effects_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self)
        menu.setTitle("Hiệu ứng")
        act_frame = QAction("Khung viền + bóng đổ", self)
        act_frame.triggered.connect(self.apply_frame)
        act_watermark = QAction("Đóng dấu watermark", self)
        act_watermark.triggered.connect(self.apply_watermark)
        act_resize = QAction("Đổi kích thước…", self)
        act_resize.triggered.connect(self.resize_dialog)
        for a in (act_frame, act_watermark, act_resize):
            menu.addAction(a)
        effects_btn.setMenu(menu)
        top.addWidget(effects_btn)

        top.addSeparator()
        act_fit = QAction("Vừa cửa sổ", self)
        act_fit.triggered.connect(self.canvas.zoom_fit)
        act_100 = QAction("100%", self)
        act_100.triggered.connect(self.canvas.zoom_100)
        top.addAction(act_fit)
        top.addAction(act_100)
        top.addSeparator()
        top.addAction(self.act_close)

        # tool palette on the left
        tools = QToolBar("Công cụ", self)
        tools.setMovable(False)
        tools.setOrientation(Qt.Orientation.Vertical)
        tools.setIconSize(QSize(22, 22))
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, tools)
        group = QActionGroup(self)
        group.setExclusive(True)
        for key, label, shortcut in TOOLS:
            action = QAction(icons.icon(key), f"{label} ({shortcut})", self)
            action.setCheckable(True)
            action.setToolTip(f"{label}  ({shortcut})")
            action.triggered.connect(lambda _=False, k=key: self._select_tool(k))
            group.addAction(action)
            tools.addAction(action)
            self._tool_actions[key] = action
        self._tool_actions["arrow"].setChecked(True)
        self._select_tool("arrow")

        # options row
        options = QToolBar("Tuỳ chọn", self)
        options.setMovable(False)
        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, options)

        options.addWidget(QLabel("  Màu: "))
        for color in PALETTE:
            btn = QToolButton()
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(22, 22)
            btn.setStyleSheet(
                f"QToolButton {{ background: {color}; border: 2px solid #1b1e24; border-radius: 11px; }}"
                f"QToolButton:hover {{ border: 2px solid #8fb4ff; }}"
            )
            btn.setToolTip(color)
            btn.clicked.connect(lambda _=False, c=color: self._set_color(c))
            options.addWidget(btn)
        custom = QToolButton()
        custom.setText("…")
        custom.setToolTip("Màu tuỳ chọn")
        custom.clicked.connect(self._pick_color)
        options.addWidget(custom)
        options.addSeparator()
        options.addWidget(QLabel(" Nét: "))
        self.width_slider = QSlider(Qt.Orientation.Horizontal)
        self.width_slider.setRange(1, 20)
        self.width_slider.setValue(self.state.width)
        self.width_slider.setFixedWidth(110)
        self.width_slider.valueChanged.connect(self._set_width)
        options.addWidget(self.width_slider)
        self.width_label = QLabel(f" {self.state.width}px ")
        options.addWidget(self.width_label)
        options.addSeparator()
        options.addWidget(QLabel(" Cỡ chữ: "))
        self.font_spin = QSpinBox()
        self.font_spin.setRange(10, 160)
        self.font_spin.setValue(self.state.font_size)
        self.font_spin.setSuffix(" px")
        self.font_spin.valueChanged.connect(self._set_font)
        options.addWidget(self.font_spin)

    def _build_status(self) -> None:
        bar = QStatusBar(self)
        self.setStatusBar(bar)
        self.size_label = QLabel()
        self.zoom_label = QLabel()
        bar.addPermanentWidget(self.size_label)
        bar.addPermanentWidget(self.zoom_label)
        self._refresh_status()

    def _refresh_status(self) -> None:
        img = self.canvas.image()
        self.size_label.setText(f"  {img.width()} × {img.height()} px  ")
        zoom = self.canvas._zoom * 100
        self.zoom_label.setText(f"  Zoom {zoom:.0f}%  ")

    def _on_changed(self) -> None:
        self._dirty = True
        self._refresh_status()
        self.setWindowTitle(f"Mitscreen — {self._path.name if self._path else 'Ảnh mới'} *")

    # ------------------------------------------------------------- options
    def _select_tool(self, key: str) -> None:
        self.state.tool = key
        if key == "badge":
            self.state.next_badge = 1
        if key in self._tool_actions:
            self._tool_actions[key].setChecked(True)
        self.canvas.setFocus()

    def _set_color(self, color: str) -> None:
        self.state.color = color
        self.canvas.setFocus()

    def _on_tool_from_canvas(self, key: str) -> None:
        self._select_tool(key)

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.state.color), self, "Chọn màu")
        if color.isValid():
            self.state.color = color.name()

    def _set_width(self, value: int) -> None:
        self.state.width = value
        self.width_label.setText(f" {value}px ")

    def _set_font(self, value: int) -> None:
        self.state.font_size = value

    # -------------------------------------------------------------- actions
    def apply_frame(self) -> None:
        self.canvas._push_undo()
        self.canvas.set_image(imageutil.add_pretty_frame(self.canvas.image()))
        self._on_changed()
        self.statusBar().showMessage("Đã thêm khung viền", 2500)

    def apply_watermark(self) -> None:
        if not self.settings.watermark_text.strip():
            text, ok = QInputDialog.getText(self, "Watermark", "Nội dung watermark:")
            if not ok or not text.strip():
                return
            self.settings.watermark_text = text.strip()
            self.settings.save()
        self.canvas._push_undo()
        self.canvas.set_image(imageutil.add_watermark(
            self.canvas.image(), self.settings.watermark_text,
            self.settings.watermark_color, self.settings.watermark_opacity))
        self._on_changed()
        self.statusBar().showMessage("Đã đóng watermark", 2500)

    def resize_dialog(self) -> None:
        img = self.canvas.image()
        dialog = ResizeDialog(img.width(), img.height(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        width, height = dialog.result_size()
        if (width, height) == (img.width(), img.height()):
            return
        self.canvas._push_undo()
        from PIL import Image
        pil = imageutil.qimage_to_pil(img).resize((width, height), Image.Resampling.LANCZOS)
        self.canvas.set_image(imageutil.pil_to_qimage(pil))
        self._on_changed()

    # ---------------------------------------------------------------- files
    def _path_for_stem(self, stem: str) -> Path:
        """Build a unique save path from a user-supplied name."""
        safe = "".join(ch for ch in stem if ch not in '<>:"/\\|?*').strip(" .")
        if not safe:
            safe = datetime.now().strftime(self.settings.filename_pattern)
        ext = "jpg" if self.settings.image_format in ("jpg", "jpeg") else self.settings.image_format
        directory = self.settings.save_path
        directory.mkdir(parents=True, exist_ok=True)
        candidate = directory / f"{safe}.{ext}"
        index = 2
        while candidate.exists():
            candidate = directory / f"{safe}-{index}.{ext}"
            index += 1
        return candidate

    def rename_prompt(self) -> Path | None:
        if self._path is None:
            self.statusBar().showMessage("Lưu ảnh trước rồi mới đổi tên được.", 3000)
            return None
        name, ok = QInputDialog.getText(self, "Đổi tên ảnh", "Tên mới (không cần đuôi):",
                                        text=self._path.stem)
        if not ok or not name.strip():
            return None
        return self.rename_to(name)

    def rename_to(self, new_stem: str) -> Path | None:
        """Rename the saved file (and its library sidecar)."""
        if self._path is None:
            return None
        safe = "".join(ch for ch in new_stem.strip() if ch not in '<>:"/\\|?*').strip(" .")
        if not safe:
            return None
        target = self._path.with_name(safe + self._path.suffix)
        if target == self._path:
            return self._path
        if target.exists():
            QMessageBox.warning(self, "Trùng tên", f"Tệp đã tồn tại:\n{target.name}")
            return None
        try:
            old_sidecar = self._path.with_suffix(self._path.suffix + ".json")
            self._path.rename(target)
            if old_sidecar.is_file():
                old_sidecar.rename(target.with_suffix(target.suffix + ".json"))
        except OSError as exc:
            QMessageBox.warning(self, "Không đổi tên được", str(exc))
            return None
        self._path = target
        self.setWindowTitle(f"Mitscreen — {target.name}")
        self.statusBar().showMessage(f"Đã đổi tên: {target.name}", 3000)
        return target

    def _default_path(self) -> Path:
        stamp = datetime.now().strftime(self.settings.filename_pattern)
        ext = "jpg" if self.settings.image_format in ("jpg", "jpeg") else self.settings.image_format
        directory = self.settings.save_path
        directory.mkdir(parents=True, exist_ok=True)
        candidate = directory / f"{stamp}.{ext}"
        index = 2
        while candidate.exists():
            candidate = directory / f"{stamp}-{index}.{ext}"
            index += 1
        return candidate

    def save(self, save_as: bool = False, ask_path: bool = False) -> Path | None:
        path = self._path
        if path is None and self.settings.ask_name_on_save and not save_as:
            default_name = datetime.now().strftime(self.settings.filename_pattern)
            name, ok = QInputDialog.getText(self, "Lưu ảnh", "Tên tệp (không cần đuôi):",
                                            text=default_name)
            if ok and name.strip():
                path = self._path_for_stem(name.strip())
        if path is None or save_as or ask_path:
            suggested = path or self._default_path()
            chosen, _ = QFileDialog.getSaveFileName(
                self, "Lưu ảnh", str(suggested),
                "PNG (*.png);;JPEG (*.jpg);;WebP (*.webp);;Tất cả (*.*)")
            if not chosen:
                return None
            path = Path(chosen)
            if not path.suffix:
                path = path.with_suffix(".png")
        fmt = path.suffix.lstrip(".").lower()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            image = imageutil.scale_image(self.canvas.image(), self.settings.export_scale)
            imageutil.save_qimage(image, path, fmt, self.settings.jpg_quality,
                                  dpi=self.settings.export_dpi,
                                  compress_level=self.settings.png_compress)
        except OSError as exc:
            QMessageBox.warning(self, "Không lưu được", f"Không ghi được tệp:\n{exc}")
            return None
        self._path = path
        self._dirty = False
        self.setWindowTitle(f"Mitscreen — {path.name}")
        if self.settings.keep_library and not str(path).startswith(str(self.settings.library_path)):
            library.add_capture(path, self.settings, self.origin)
        self.saved.emit(path)
        self.statusBar().showMessage(f"Đã lưu: {path}", 4000)
        return path

    def copy_to_clipboard(self) -> None:
        image = self.canvas.image()
        QApplication.clipboard().setImage(image)
        if self._path and self._path.is_file():
            from PySide6.QtCore import QMimeData, QUrl
            mime = QMimeData()
            mime.setImageData(image)
            mime.setUrls([QUrl.fromLocalFile(str(self._path))])
            QApplication.clipboard().setMimeData(mime)
        self._copied = True
        self.statusBar().showMessage("Đã copy vào clipboard", 2500)

    def print_image(self) -> None:
        try:
            from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        except Exception:
            QMessageBox.information(self, "In ấn", "Bản PySide6 này không có QtPrintSupport.")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("In ảnh")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        painter = QPainter(printer)
        image = self.canvas.image()
        page = printer.pageRect(QPrinter.Unit.DevicePixel)
        scale = min(page.width() / image.width(), page.height() / image.height())
        painter.translate(page.x(), page.y())
        painter.scale(scale, scale)
        painter.drawImage(0, 0, image)
        painter.end()
        self.statusBar().showMessage("Đã gửi tới máy in", 3000)

    # ---------------------------------------------------------------- close
    def closeEvent(self, event) -> None:  # noqa: N802
        self.canvas._end_text(commit=True)
        if self._dirty and not self._copied:
            answer = QMessageBox.question(
                self, "Chưa lưu",
                "Ảnh có thay đổi chưa lưu. Lưu lại?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.StandardButton.Save:
                if self.save() is None:
                    event.ignore()
                    return
        self.closed.emit()
        super().closeEvent(event)

    def wheelEvent(self, event) -> None:  # noqa: N802
        self._refresh_status()
        super().wheelEvent(event)
