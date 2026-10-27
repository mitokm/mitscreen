"""A floating quick-access bar: screenshot / record, with more actions behind a menu.

Behaves like a small dock: it sits against the top edge, stays expanded while the
mouse is over it, and folds into a thin sliver when idle (optional).  It can be
dragged anywhere on screen and remembers its position.
"""

from __future__ import annotations

from PySide6.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, QRect, QRectF,
                            QSize, Qt, QTimer, Signal)
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLayout, QMenu, QToolButton, QWidget)

from . import icons
from .config import Settings

ACCENT = "#2563eb"
BODY = QColor(22, 26, 33, 246)
BORDER = QColor(62, 69, 82, 230)

BUTTON_QSS = """
QToolButton {
    color: #e6e8ec; background: transparent; border: 1px solid transparent;
    border-radius: 9px; padding: 3px;
}
QToolButton:hover { background: #2b323c; border-color: #3b4451; }
QToolButton:pressed { background: #1f2530; }
QToolButton::menu-indicator { image: none; }
"""


class QuickBar(QWidget):
    action = Signal(str)

    NOTCH = 7
    RADIUS = 12

    def __init__(self, settings: Settings):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.settings = settings
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
        self.setWindowTitle("Mitscreen")
        self.setCursor(Qt.CursorShape.SizeAllCursor)

        self._expanded = True
        self._paused = False
        self._drag_offset: QPoint | None = None
        self._menu_open = False
        self._click_through_guard = False

        self._build()
        self._expanded_size = self._measure()
        self._collapsed_size = QSize(164, self.NOTCH + 9)

        screen = QGuiApplication.primaryScreen()
        area = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        stored_x = settings.extra.get("quickbar_x")
        stored_y = settings.extra.get("quickbar_y")
        if isinstance(stored_x, int) and isinstance(stored_y, int):
            self._center_x = stored_x
            self._top_y = stored_y
        else:
            self._center_x = area.center().x()
            self._top_y = area.top()
        self._clamp_to_screen()

        self._anim = QPropertyAnimation(self, b"geometry", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(self._on_anim_finished)

        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.setInterval(1100)
        self._collapse_timer.timeout.connect(self._maybe_collapse)

        self._apply_geometry(expanded=True, animate=False)

    # ------------------------------------------------------------------ ui
    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, self.NOTCH + 8, 10, 9)
        layout.setSpacing(3)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.setMinimumSize(0, 0)
        self.setStyleSheet(BUTTON_QSS)

        self.btn_region = self._big_button("region", "Chụp vùng", "region")
        self.btn_record = self._big_button("record", "Quay video", "record", color="#ef4444")
        layout.addWidget(self.btn_region)
        layout.addWidget(self.btn_record)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("color: #333a45;")
        line.setFixedWidth(1)
        layout.addSpacing(3)
        layout.addWidget(line)
        layout.addSpacing(3)

        self.btn_folder = self._small_button("folder", "Mở thư mục lưu", "folder")
        self.btn_menu = self._small_button("chevron", "Thêm thao tác", "menu")
        self.btn_close = self._small_button("close", "Ẩn thanh này", "hide")
        for button in (self.btn_folder, self.btn_menu, self.btn_close):
            layout.addWidget(button)

        menu = QMenu(self)
        hotkeys = self.settings.hotkeys

        def hint(key: str) -> str:
            value = (hotkeys.get(key) or "").strip()
            return f"\t{value}" if value else ""

        entries = [
            ("Chụp vùng", "region", "region", "capture_region"),
            ("Chụp lại vùng trước", "previous", "history", "capture_previous"),
            ("Chụp toàn màn hình", "screen", "fullscreen", "capture_screen"),
            ("Chụp cửa sổ", "window", "window", "capture_window"),
            ("Chụp hẹn giờ 3 giây", "delayed", "timer", ""),
            ("Bút lấy màu", "color", "eyedropper", ""),
            (None, None, None, None),
            ("Bảng điều khiển ảnh", "history", "history", "open_history"),
            ("Cài đặt…", "settings", "settings", ""),
        ]
        for label, key, icon_name, hotkey in entries:
            if label is None:
                menu.addSeparator()
                continue
            act = menu.addAction(icons.icon(icon_name), f"{label}{hint(hotkey)}")
            act.triggered.connect(lambda _=False, k=key: self.action.emit(k))
        menu.aboutToShow.connect(self._on_menu_show)
        menu.aboutToHide.connect(self._on_menu_hide)
        self.btn_menu.setMenu(menu)
        self.btn_menu.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        self._children = [self.btn_region, self.btn_record, line,
                          self.btn_folder, self.btn_menu, self.btn_close]

    def _big_button(self, icon_name: str, text: str, action: str,
                    color: str = "#e6e8ec") -> QToolButton:
        button = QToolButton()
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setIcon(icons.icon(icon_name, color))
        button.setIconSize(QSize(26, 26))
        button.setText(text)
        button.setFixedSize(92, 56)
        button.setFont(QFont("Segoe UI", 9))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip(text)
        button.clicked.connect(lambda: self.action.emit(action))
        return button

    def _small_button(self, icon_name: str, tooltip: str, action: str) -> QToolButton:
        button = QToolButton()
        button.setIcon(icons.icon(icon_name))
        button.setIconSize(QSize(16, 16))
        button.setFixedSize(28, 28)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip(tooltip)
        if action != "menu":
            button.clicked.connect(lambda: self.action.emit(action))
        return button

    def _measure(self) -> QSize:
        hint = self.layout().sizeHint()
        return QSize(max(300, hint.width()), hint.height() + 2)

    # -------------------------------------------------------------- painting
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        body = QRectF(0.5, self.NOTCH + 0.5, self.width() - 1, self.height() - self.NOTCH - 1)
        path = QPainterPath()
        path.addRoundedRect(body, self.RADIUS, self.RADIUS)
        painter.fillPath(path, BODY)
        painter.setPen(QPen(BORDER, 1))
        painter.drawPath(path)

        # small tab pointing at the screen edge
        if self._expanded:
            cx = self.width() / 2
            tab = QPainterPath()
            tab.moveTo(cx - 8, self.NOTCH + 1)
            tab.lineTo(cx, 0.5)
            tab.lineTo(cx + 8, self.NOTCH + 1)
            tab.closeSubpath()
            painter.fillPath(tab, BODY)
            painter.setPen(QPen(BORDER, 1))
            painter.drawLine(QPoint(int(cx - 8), self.NOTCH), QPoint(int(cx - 1), 1))
            painter.drawLine(QPoint(int(cx + 1), 1), QPoint(int(cx + 8), self.NOTCH))
        else:
            # grip so the collapsed sliver stays discoverable
            grip = QRectF(self.width() / 2 - 22, self.height() - 5.5, 44, 3)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(198, 208, 222, 170))
            painter.drawRoundedRect(grip, 1.5, 1.5)

    # --------------------------------------------------------------- geometry
    def _clamp_to_screen(self) -> None:
        screens = QGuiApplication.screens()
        if not screens:
            return
        area = None
        for screen in screens:
            if screen.availableGeometry().contains(QPoint(self._center_x, self._top_y + 20)):
                area = screen.availableGeometry()
                break
        area = area or QGuiApplication.primaryScreen().availableGeometry()
        width = self._expanded_size.width() if hasattr(self, "_expanded_size") else 320
        self._center_x = max(area.left() + width // 2, min(area.right() - width // 2, self._center_x))
        self._top_y = max(area.top(), min(area.bottom() - 40, self._top_y))

    def _target_rect(self, expanded: bool) -> QRect:
        size = self._expanded_size if expanded else self._collapsed_size
        return QRect(self._center_x - size.width() // 2, self._top_y, size.width(), size.height())

    def _apply_geometry(self, expanded: bool, animate: bool = True) -> None:
        self._expanded = expanded
        for child in self._children:
            child.setVisible(expanded)
        target = self._target_rect(expanded)
        if animate and self.isVisible():
            self._anim.stop()
            self._anim.setStartValue(self.geometry())
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            self.setGeometry(target)
        self.update()

    def _on_anim_finished(self) -> None:
        if self._expanded:
            for child in self._children:
                child.setVisible(True)
        self.update()

    def expand(self) -> None:
        if self._paused:
            return
        self._collapse_timer.stop()
        if not self._expanded:
            self._apply_geometry(True)

    def collapse(self) -> None:
        if self._paused or not self.settings.quickbar_autohide or self._menu_open:
            return
        if self._expanded:
            self._apply_geometry(False)

    def _maybe_collapse(self) -> None:
        if self._menu_open or not self.settings.quickbar_autohide:
            return
        if self.underMouse() or self._anim.state() == QPropertyAnimation.State.Running:
            self._collapse_timer.start()
            return
        self.collapse()

    # ----------------------------------------------------------------- hover
    def enterEvent(self, event) -> None:  # noqa: N802
        self._collapse_timer.stop()
        if not self._expanded:
            self.expand()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        if self.settings.quickbar_autohide and not self._menu_open:
            self._collapse_timer.start()
        super().leaveEvent(event)

    def _on_menu_show(self) -> None:
        self._menu_open = True
        self._collapse_timer.stop()

    def _on_menu_hide(self) -> None:
        self._menu_open = False
        if self.settings.quickbar_autohide:
            self._collapse_timer.start()

    # ------------------------------------------------------------------ drag
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            point = event.globalPosition().toPoint() - self._drag_offset
            self.move(point)
            self._center_x = point.x() + self.width() // 2
            self._top_y = point.y()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None:
            self._drag_offset = None
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            self._clamp_to_screen()
            self.setGeometry(self._target_rect(self._expanded))
            self.settings.extra["quickbar_x"] = self._center_x
            self.settings.extra["quickbar_y"] = self._top_y
            self.settings.save()
        super().mouseReleaseEvent(event)

    # ------------------------------------------------------------- lifecycle
    def pause(self) -> None:
        """Hide while a capture or recording is running."""
        self._paused = True
        self._collapse_timer.stop()
        self.hide()

    def resume(self) -> None:
        self._paused = False
        if not self.settings.show_quickbar:
            return
        self.show()
        self.raise_()
        if self.settings.quickbar_autohide:
            self._apply_geometry(False, animate=False)
        else:
            self._apply_geometry(True, animate=False)

    def refresh_style(self) -> None:
        """Recompute size and reposition after a DPI or settings change."""
        self._expanded_size = self._measure()
        self._apply_geometry(self._expanded, animate=False)
        self._clamp_to_screen()
        self.setGeometry(self._target_rect(self._expanded))
