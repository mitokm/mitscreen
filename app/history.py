"""Workspace window: sidebar, thumbnail grid and a bottom action bar.

This is the panel behind the tray icon and the quick bar, modelled on the
"workspace" window of commercial screenshot tools.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QIcon, QImageReader, QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QInputDialog, QLabel, QListWidget,
                               QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton,
                               QToolButton, QVBoxLayout, QWidget)

from . import icons, library
from .config import Settings

SIDEBAR_QSS = """
QPushButton#side {
    color: #d6dbe4; background: transparent; border: 1px solid transparent;
    border-radius: 8px; padding: 9px 10px; text-align: left; font-size: 13px;
}
QPushButton#side:hover { background: #232936; border-color: #313a49; }
QPushButton#side:checked { background: #1d3a6e; border-color: #2f5fb0; color: #ffffff; }
"""

ACTION_QSS = """
QToolButton {
    color: #e6e8ec; background: transparent; border: 1px solid transparent;
    border-radius: 12px; padding: 6px 4px; font-size: 12px;
}
QToolButton:hover { background: #262d3a; border-color: #38424f; }
QToolButton::menu-indicator { image: none; }
"""


def _thumb(path: Path, width: int = 240, height: int = 150) -> QPixmap:
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid():
        reader.setScaledSize(size.scaled(QSize(width, height), Qt.AspectRatioMode.KeepAspectRatio))
    image = reader.read()
    if image.isNull():
        return QPixmap()
    return QPixmap.fromImage(image)


class WorkspaceWindow(QMainWindow):
    capture_requested = Signal(str)      # region | window | screen | record
    settings_requested = Signal()
    folder_requested = Signal()
    edit_requested = Signal(Path)
    share_requested = Signal(str, Path)  # copy_image | copy_path | reveal | delete

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Mitscreen — Bảng điều khiển")
        self.resize(1020, 660)
        self.setWindowIcon(icons.icon("snap"))
        self._build()
        self.refresh()

    # ------------------------------------------------------------------ ui
    def _build(self) -> None:
        central = QWidget(self)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Bảng điều khiển")
        title.setStyleSheet("font-size: 17px; font-weight: 600;")
        self.count_label = QLabel("Đang tải…")
        self.count_label.setStyleSheet("color: #9aa3b2; font-size: 12px;")
        header.addWidget(title)
        header.addSpacing(10)
        header.addWidget(self.count_label)
        header.addStretch(1)
        refresh = QPushButton("Làm mới")
        refresh.clicked.connect(self.refresh)
        header.addWidget(refresh)
        outer.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._sidebar())

        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("color: #262c36;")
        line.setFixedWidth(1)
        body.addWidget(line)

        self.list = QListWidget()
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setIconSize(QSize(232, 146))
        self.list.setGridSize(QSize(252, 198))
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setUniformItemSizes(True)
        self.list.setSpacing(6)
        self.list.setWordWrap(True)
        self.list.itemDoubleClicked.connect(self._open_item)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
        body.addWidget(self.list, 1)
        outer.addLayout(body, 1)

        outer.addWidget(self._action_bar())
        self.setCentralWidget(central)

    def _sidebar(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(186)
        panel.setStyleSheet(SIDEBAR_QSS)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        recent = QPushButton("Ảnh gần đây")
        recent.setObjectName("side")
        recent.setCheckable(True)
        recent.setChecked(True)
        recent.setIcon(icons.icon("history"))
        recent.setIconSize(QSize(16, 16))
        layout.addWidget(recent)

        folder = QPushButton("Thư mục lưu")
        folder.setObjectName("side")
        folder.setIcon(icons.icon("folder"))
        folder.setIconSize(QSize(16, 16))
        folder.clicked.connect(self.folder_requested.emit)
        layout.addWidget(folder)

        settings = QPushButton("Cài đặt…")
        settings.setObjectName("side")
        settings.setIcon(icons.icon("settings"))
        settings.setIconSize(QSize(16, 16))
        settings.clicked.connect(self.settings_requested.emit)
        layout.addWidget(settings)

        layout.addStretch(1)

        new_button = QPushButton("＋  Chụp mới")
        new_button.setStyleSheet(
            "QPushButton { background: #2563eb; border: none; border-radius: 8px;"
            " color: white; padding: 10px; font-weight: 600; }"
            "QPushButton:hover { background: #3b7bff; }"
            "QPushButton::menu-indicator { image: none; }")
        menu = QMenu(new_button)
        for label, key in (("Chụp vùng", "region"),
                           ("Chụp cửa sổ", "window"),
                           ("Chụp toàn màn hình", "screen"),
                           ("Quay video", "record")):
            act = menu.addAction(icons.icon(key if key != "screen" else "fullscreen"), label)
            act.triggered.connect(lambda _=False, k=key: self.capture_requested.emit(k))
        new_button.setMenu(menu)
        layout.addWidget(new_button)
        return panel

    def _action_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("actionBar")
        bar.setStyleSheet(ACTION_QSS + """
QFrame#actionBar {
    background: #1a1f28; border: 1px solid #262d38; border-radius: 12px;
}
""")

        def action(icon_name: str, text: str, slot) -> QToolButton:
            button = QToolButton()
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setIcon(icons.icon(icon_name))
            button.setIconSize(QSize(26, 26))
            button.setText(text)
            button.setFixedSize(104, 62)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(slot)
            return button

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        self.btn_region = action("region", "Chụp vùng",
                                  lambda: self.capture_requested.emit("region"))
        self.btn_record = action("record", "Quay video",
                                  lambda: self.capture_requested.emit("record"))
        self.btn_edit = action("crop", "Sửa…", self._edit_selected)
        layout.addWidget(self.btn_region)
        layout.addWidget(self.btn_record)
        layout.addWidget(self.btn_edit)

        share = QToolButton()
        share.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        share.setIcon(icons.icon("share"))
        share.setIconSize(QSize(26, 26))
        share.setText("Chia sẻ")
        share.setFixedSize(104, 62)
        share.setCursor(Qt.CursorShape.PointingHandCursor)
        share_menu = QMenu(share)
        for label, key in (("Copy ảnh", "copy_image"),
                           ("Copy đường dẫn", "copy_path"),
                           ("Mở thư mục chứa ảnh", "reveal"),
                           ("Xoá ảnh", "delete")):
            act = share_menu.addAction(label)
            act.triggered.connect(lambda _=False, k=key: self._share(k))
        share.setMenu(share_menu)
        share.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_share = share
        layout.addWidget(share)

        layout.addStretch(1)
        self.btn_close = action("close", "Đóng", self.close)
        layout.addWidget(self.btn_close)
        return bar

    # ------------------------------------------------------------------ data
    def refresh(self) -> None:
        self.list.clear()
        items = library.list_items(self.settings, limit=500)
        for item in items:
            widget_item = QListWidgetItem()
            widget_item.setText(f"{item.path.name}\n{item.created:%d/%m/%Y %H:%M}")
            widget_item.setData(Qt.ItemDataRole.UserRole, str(item.path))
            thumb = _thumb(item.path)
            if not thumb.isNull():
                widget_item.setIcon(QIcon(thumb))
            widget_item.setToolTip(str(item.path))
            self.list.addItem(widget_item)
        self.count_label.setText(f"{len(items)} ảnh")

    # --------------------------------------------------------------- actions
    def selected_path(self) -> Path | None:
        item = self.list.currentItem()
        if item is None:
            return None
        raw = item.data(Qt.ItemDataRole.UserRole)
        return Path(raw) if raw else None

    def _edit_selected(self) -> None:
        path = self.selected_path()
        if path is None:
            QMessageBox.information(self, "Chưa chọn ảnh", "Hãy chọn một ảnh trong lưới trước.")
            return
        self.edit_requested.emit(path)

    def _share(self, action: str) -> None:
        path = self.selected_path()
        if path is None:
            QMessageBox.information(self, "Chưa chọn ảnh", "Hãy chọn một ảnh trong lưới trước.")
            return
        self.share_requested.emit(action, path)

    def _open_item(self, item: QListWidgetItem) -> None:
        raw = item.data(Qt.ItemDataRole.UserRole)
        if raw:
            self.edit_requested.emit(Path(raw))

    def rename_prompt(self) -> Path | None:
        path = self.selected_path()
        if path is None:
            return None
        name, ok = QInputDialog.getText(self, "Đổi tên ảnh", "Tên mới (không cần đuôi):",
                                        text=path.stem)
        if not ok or not name.strip():
            return None
        return self.rename_to(name)

    def rename_to(self, new_stem: str) -> Path | None:
        """Rename the selected library image (and its metadata sidecar)."""
        path = self.selected_path()
        if path is None:
            return None
        safe = "".join(ch for ch in new_stem.strip() if ch not in '<>:"/\\|?*').strip(" .")
        if not safe:
            return None
        target = path.with_name(safe + path.suffix)
        if target == path:
            return path
        if target.exists():
            QMessageBox.warning(self, "Trùng tên", f"Tệp đã tồn tại:\n{target.name}")
            return None
        try:
            sidecar = path.with_suffix(path.suffix + ".json")
            path.rename(target)
            if sidecar.is_file():
                sidecar.rename(target.with_suffix(target.suffix + ".json"))
        except OSError as exc:
            QMessageBox.warning(self, "Không đổi tên được", str(exc))
            return None
        self.refresh()
        return target

    def _context_menu(self, pos) -> None:
        path = self.selected_path()
        if path is None:
            return
        menu = QMenu(self)
        act_edit = QAction("Mở trong trình sửa", self)
        act_edit.triggered.connect(lambda: self.edit_requested.emit(path))
        act_rename = QAction("Đổi tên…", self)
        act_rename.triggered.connect(self.rename_prompt)
        act_copy = QAction("Copy ảnh", self)
        act_copy.triggered.connect(lambda: self._share("copy_image"))
        act_reveal = QAction("Hiện trong Explorer", self)
        act_reveal.triggered.connect(lambda: self._share("reveal"))
        act_delete = QAction("Xoá", self)
        act_delete.triggered.connect(lambda: self._share("delete"))
        for action in (act_edit, act_rename, act_copy, act_reveal, act_delete):
            menu.addAction(action)
        menu.exec(self.list.mapToGlobal(pos))


# older imports used this name
HistoryWindow = WorkspaceWindow
