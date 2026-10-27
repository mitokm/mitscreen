"""Application controller: tray icon, hotkeys, capture flows."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QRect, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication, QDialog, QInputDialog, QMenu, QMessageBox,
                               QSystemTrayIcon, QWidget)

from . import icons, imageutil, library, win32util
from .config import HOTKEY_LABELS, Settings
from .editor import EditorWindow
from .history import WorkspaceWindow
from .logging_util import log
from .overlay import RegionOverlay
from .quickbar import QuickBar
from .recorder import Recorder, find_ffmpeg
from .settings_ui import SettingsDialog


class MitscreenApp(QObject):
    def __init__(self, app: QApplication, settings: Settings):
        super().__init__()
        self.app = app
        self.settings = settings
        self._overlay: RegionOverlay | None = None
        self._editors: list[EditorWindow] = []
        self._workspace: WorkspaceWindow | None = None
        self._owner = QWidget()
        self._owner.setWindowTitle("Mitscreen")
        self._hotkeys = win32util.HotkeyManager(self._owner)
        self._hotkeys.install()
        self._recorder = Recorder(settings, self)
        self._recorder.stopped.connect(self._on_record_stopped)
        self._recorder.failure.connect(self._on_record_failed)

        self._tray = QSystemTrayIcon(icons.icon("snap"), self)
        self._tray.setToolTip("Mitscreen — chụp & quay màn hình")
        self._menu = self._build_menu()
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()
        self.register_hotkeys()
        self._quickbar: QuickBar | None = None
        if self.settings.show_quickbar:
            self._ensure_quickbar().resume()

    # ------------------------------------------------------------------ menu
    def _build_menu(self) -> QMenu:
        menu = QMenu()
        entries = [
            ("capture_region", "Chụp vùng chọn", "region", lambda: self.capture("region")),
            ("capture_screen", "Chụp toàn màn hình", "fullscreen", lambda: self.capture("screen")),
            ("capture_window", "Chụp cửa sổ", "window", lambda: self.capture("window")),
            ("record_region", "Quay màn hình", "record", self.toggle_recording),
            ("open_history", "Bảng điều khiển ảnh", "history", self.show_history),
        ]
        for key, label, icon_name, slot in entries:
            action = QAction(icons.icon(icon_name), label, self)
            hotkey = self.settings.hotkeys.get(key, "")
            action.setToolTip(f"{label}  ({hotkey})" if hotkey else label)
            action.triggered.connect(slot)
            menu.addAction(action)
        menu.addSeparator()
        open_folder = QAction("Mở thư mục lưu", self)
        open_folder.triggered.connect(self._open_save_folder)
        settings_action = QAction(icons.icon("settings"), "Cài đặt…", self)
        settings_action.triggered.connect(self.open_settings)
        about = QAction("Giới thiệu / phím tắt", self)
        about.triggered.connect(self.show_about)
        tray_help = QAction("Hiện icon trong khay…", self)
        tray_help.triggered.connect(self.show_tray_help)
        menu.addAction(open_folder)
        menu.addAction(settings_action)
        menu.addAction(about)
        menu.addAction(tray_help)
        menu.addSeparator()
        self._quickbar_action = QAction(icons.icon("snap"), "Thanh truy cập nhanh", self)
        self._quickbar_action.setCheckable(True)
        self._quickbar_action.setChecked(self.settings.show_quickbar)
        self._quickbar_action.toggled.connect(self._set_quickbar_visible)
        menu.addAction(self._quickbar_action)
        menu.addSeparator()
        quit_action = QAction(icons.icon("close"), "Thoát", self)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)
        return menu

    # -------------------------------------------------------------- quickbar
    def _ensure_quickbar(self) -> QuickBar:
        if self._quickbar is None:
            self._quickbar = QuickBar(self.settings)
            self._quickbar.action.connect(self._on_quickbar_action)
            log("quickbar created")
        return self._quickbar

    def _on_quickbar_action(self, action: str) -> None:
        log(f"quickbar action: {action}")
        if action == "record":
            self.toggle_recording()
        elif action in ("region", "window", "screen"):
            self.capture(action)
        elif action == "previous":
            self.capture_previous()
        elif action == "delayed":
            self.capture_delayed()
        elif action == "color":
            self.pick_color()
        elif action == "folder":
            self._open_save_folder()
        elif action == "history":
            self.show_history()
        elif action == "settings":
            self.open_settings()
        elif action == "hide":
            self._set_quickbar_visible(False)

    def _set_quickbar_visible(self, visible: bool) -> None:
        self.settings.show_quickbar = bool(visible)
        self.settings.save()
        if visible:
            self._ensure_quickbar().resume()
        elif self._quickbar is not None:
            self._quickbar.hide()
        self._sync_quickbar_menu()

    def _sync_quickbar_menu(self) -> None:
        action = getattr(self, "_quickbar_action", None)
        if action is not None and action.isChecked() != self.settings.show_quickbar:
            action.blockSignals(True)
            action.setChecked(self.settings.show_quickbar)
            action.blockSignals(False)

    def _pause_quickbar(self) -> None:
        if self._quickbar is not None:
            self._quickbar.pause()

    def _resume_quickbar(self) -> None:
        if self._quickbar is not None and self.settings.show_quickbar:
            self._quickbar.resume()

    def _apply_quickbar_settings(self) -> None:
        self._sync_quickbar_menu()
        if self.settings.show_quickbar:
            bar = self._ensure_quickbar()
            bar.refresh_style()
            bar.resume()
            if not self.settings.quickbar_autohide:
                bar.expand()
        elif self._quickbar is not None:
            self._quickbar.hide()

    # -------------------------------------------------------------- hotkeys
    def register_hotkeys(self) -> None:
        self._hotkeys.unregister_all()
        mapping = {
            "capture_region": lambda: self.capture("region"),
            "capture_previous": self.capture_previous,
            "capture_screen": lambda: self.capture("screen"),
            "capture_window": lambda: self.capture("window"),
            "record_region": self.toggle_recording,
            "open_history": self.show_history,
        }
        for key, callback in mapping.items():
            spec = (self.settings.hotkeys.get(key) or "").strip()
            if not spec:
                log(f"hotkey {key}: disabled")
                continue
            ok = self._hotkeys.register(key, spec, callback)
            reason = "" if ok else f" ({self._hotkeys.failed.get(key, '')})"
            log(f"hotkey {key}: {spec} -> {'ok' if ok else 'FAILED'}{reason}")
        if self._hotkeys.failed:
            details = ", ".join(
                f"{HOTKEY_LABELS.get(k, k)} ({self.settings.hotkeys.get(k, '')})"
                for k in self._hotkeys.failed)
            self._notify("Không đăng ký được phím tắt",
                         f"{details}. Đổi tổ hợp trong Cài đặt.")

    # -------------------------------------------------------------- capture
    def capture(self, mode: str) -> None:
        if self._overlay is not None:
            return
        log(f"capture requested: {mode}")
        self._pause_quickbar()
        if mode == "screen":
            QTimer.singleShot(160, self._capture_fullscreen)
        else:
            QTimer.singleShot(160, lambda: self._open_overlay(mode))

    def _capture_fullscreen(self) -> None:
        try:
            image = imageutil.grab_desktop()
        except Exception as exc:  # pragma: no cover - rare
            self._resume_quickbar()
            QMessageBox.warning(None, "Lỗi chụp màn hình", str(exc))
            return
        self._resume_quickbar()
        self.open_editor(image, "toàn màn hình")

    def _open_overlay(self, mode: str) -> None:
        auto: str | None
        if mode == "record":
            auto = "record"
        elif self.settings.after_capture == "menu":
            auto = None
        else:
            auto = "auto"
        try:
            overlay = RegionOverlay(mode, auto_action=auto)
        except Exception as exc:  # pragma: no cover
            self._resume_quickbar()
            QMessageBox.warning(None, "Lỗi chụp màn hình", str(exc))
            return
        overlay.finished.connect(self._on_overlay_finished)
        overlay.cancelled.connect(self._on_overlay_cancelled)
        overlay.destroyed.connect(lambda _=None, o=overlay: self._clear_overlay(o))
        self._overlay = overlay
        overlay.begin()

    def _clear_overlay(self, overlay) -> None:
        if self._overlay is overlay:
            self._overlay = None

    def _on_overlay_finished(self, rect: QRect, action: str, image) -> None:
        self._overlay = None
        origin = f"vùng {rect.width()}×{rect.height()}"
        log(f"capture finished: {action} {rect.width()}x{rect.height()} at {rect.x()},{rect.y()}")
        if action != "record":
            self.settings.extra["last_region"] = [rect.x(), rect.y(),
                                                  rect.width(), rect.height()]
            self.settings.save()
        if action == "record":
            self._start_recording(rect)
        elif action == "auto":
            self._apply_after_capture(image, origin)
        elif action == "copy":
            self._copy_image(image)
            self._notify("Đã copy ảnh", f"{image.width()}×{image.height()} px vào clipboard")
            self._resume_quickbar()
        elif action == "save":
            self._save_quick(image, origin)
            self._resume_quickbar()
        else:
            self.open_editor(image, origin)
            self._resume_quickbar()

    def _apply_after_capture(self, image, origin: str) -> None:
        """Run the configured post-capture behaviour (default: copy + editor)."""
        behavior = self.settings.after_capture
        if behavior == "copy_edit":
            self._copy_image(image)
            self.open_editor(image, origin, already_copied=True)
            log("after capture: copied + editor")
        elif behavior == "save":
            self._save_quick(image, origin)
            log("after capture: saved")
        else:  # "edit"
            self.open_editor(image, origin)
            log("after capture: editor")
        self._resume_quickbar()

    def _on_overlay_cancelled(self) -> None:
        self._overlay = None
        log("capture cancelled")
        self._resume_quickbar()

    # ------------------------------------------------------- extra captures
    def capture_previous(self) -> None:
        """Re-capture the region used last time."""
        region = self.settings.extra.get("last_region")
        valid = (isinstance(region, list) and len(region) == 4
                 and all(isinstance(value, (int, float)) for value in region))
        if not valid:
            self._notify("Chưa có vùng trước", "Hãy chụp một vùng trước đã.")
            self.capture("region")
            return
        rect = QRect(int(region[0]), int(region[1]), int(region[2]), int(region[3]))
        log(f"capture previous region: {rect.width()}x{rect.height()} at {rect.x()},{rect.y()}")
        self._pause_quickbar()
        QTimer.singleShot(160, lambda: self._capture_rect(rect))

    def _capture_rect(self, rect: QRect) -> None:
        try:
            image = imageutil.grab_rect(rect)
        except Exception as exc:  # pragma: no cover - rare
            self._resume_quickbar()
            QMessageBox.warning(None, "Lỗi chụp màn hình", str(exc))
            return
        self._resume_quickbar()
        self._apply_after_capture(image, f"vùng {rect.width()}×{rect.height()}")

    def capture_delayed(self, seconds: int = 3) -> None:
        """Open the region picker after a short countdown."""
        log(f"delayed capture: {seconds}s")
        self._notify("Chụp hẹn giờ", f"Sẽ mở khung chọn vùng sau {seconds} giây…")
        QTimer.singleShot(seconds * 1000, lambda: self.capture("region"))

    def pick_color(self) -> None:
        """Full-screen colour picker: click copies the hex value."""
        if self._overlay is not None:
            return
        self._pause_quickbar()
        QTimer.singleShot(160, self._open_color_picker)

    def _open_color_picker(self) -> None:
        overlay = RegionOverlay("color")
        overlay.colorPicked.connect(self._on_color_picked)
        overlay.cancelled.connect(self._on_overlay_cancelled)
        overlay.destroyed.connect(lambda _=None, o=overlay: self._clear_overlay(o))
        self._overlay = overlay
        overlay.begin()

    def _on_color_picked(self, color) -> None:
        self._overlay = None
        value = color.name().upper()
        QApplication.clipboard().setText(value)
        log(f"color picked: {value}")
        self._resume_quickbar()
        self._notify("Đã copy mã màu",
                     f"{value}   rgb({color.red()}, {color.green()}, {color.blue()})")

    # ------------------------------------------------------------ recording
    def toggle_recording(self) -> None:
        if self._recorder.state() != self._recorder.ProcessState.NotRunning:
            self._recorder.stop_recording()
            return
        if not find_ffmpeg():
            QMessageBox.warning(None, "Thiếu ffmpeg",
                                "Không tìm thấy ffmpeg.exe.\nCài ffmpeg rồi thêm vào PATH.")
            return
        self.capture("record")

    def _start_recording(self, rect: QRect) -> None:
        self._pause_quickbar()
        if self._recorder.start_recording(rect):
            log(f"recording started: {rect.width()}x{rect.height()} at {rect.x()},{rect.y()}")
            self._notify("Bắt đầu quay", "Bấm phím quay lần nữa hoặc nút Dừng để kết thúc.")
        else:
            self._resume_quickbar()

    def _on_record_stopped(self, path: Path) -> None:
        log(f"recording stopped: {path}")
        self._resume_quickbar()
        self._notify("Đã lưu video", str(path))
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except OSError:
            win32util.open_in_explorer(path, select=True)

    def _on_record_failed(self, message: str) -> None:
        self._resume_quickbar()
        QMessageBox.warning(None, "Quay màn hình thất bại", message)

    # ---------------------------------------------------------------- files
    def _decorate(self, image):
        if self.settings.pretty_frame:
            image = imageutil.add_pretty_frame(image)
        if self.settings.watermark_enabled and self.settings.watermark_text.strip():
            image = imageutil.add_watermark(image, self.settings.watermark_text,
                                            self.settings.watermark_color,
                                            self.settings.watermark_opacity)
        return image

    def _next_path(self, stem: str | None = None) -> Path:
        directory = self.settings.save_path
        directory.mkdir(parents=True, exist_ok=True)
        ext = "jpg" if self.settings.image_format in ("jpg", "jpeg") else self.settings.image_format
        base = stem or datetime.now().strftime(self.settings.filename_pattern)
        safe = "".join(ch for ch in base if ch not in '<>:"/\\|?*').strip(" .")
        if not safe:
            safe = datetime.now().strftime(self.settings.filename_pattern)
        candidate = directory / f"{safe}.{ext}"
        index = 2
        while candidate.exists():
            candidate = directory / f"{safe}-{index}.{ext}"
            index += 1
        return candidate

    def _save_quick(self, image, origin: str) -> None:
        image = self._decorate(image)
        path = self._next_path()
        if self.settings.ask_name_on_save:
            name, ok = QInputDialog.getText(None, "Lưu ảnh", "Tên tệp (không cần đuôi):",
                                            text=path.stem)
            if ok and name.strip():
                path = self._next_path(name.strip())
        try:
            export = imageutil.scale_image(image, self.settings.export_scale)
            imageutil.save_qimage(export, path, path.suffix.lstrip("."),
                                  self.settings.jpg_quality,
                                  dpi=self.settings.export_dpi,
                                  compress_level=self.settings.png_compress)
        except OSError as exc:
            QMessageBox.warning(None, "Không lưu được", str(exc))
            return
        library.add_capture(path, self.settings, origin)
        if self.settings.auto_copy:
            self._copy_image(image)
        log(f"saved capture: {path}")
        self._notify("Đã lưu ảnh", str(path))

    def _copy_image(self, image) -> None:
        QApplication.clipboard().setImage(image)

    def open_editor(self, image, origin: str = "", already_copied: bool = False) -> None:
        window = EditorWindow(image, self.settings, origin, already_copied=already_copied)
        window.saved.connect(self._on_editor_saved)
        window.closed.connect(lambda w=window: self._forget_editor(w))
        self._editors.append(window)
        window.show()
        window.raise_()
        window.activateWindow()

    def _on_editor_saved(self, path: Path) -> None:
        self._notify("Đã lưu ảnh", str(path))

    def _forget_editor(self, window: EditorWindow) -> None:
        if window in self._editors:
            self._editors.remove(window)

    # --------------------------------------------------------------- windows
    def show_history(self) -> None:
        """Open the workspace panel (thumbnails + actions)."""
        if self._workspace is None:
            workspace = WorkspaceWindow(self.settings)
            workspace.capture_requested.connect(self._on_workspace_capture)
            workspace.settings_requested.connect(self.open_settings)
            workspace.folder_requested.connect(self._open_save_folder)
            workspace.edit_requested.connect(self._open_from_library)
            workspace.share_requested.connect(self._on_workspace_share)
            self._workspace = workspace
        self._workspace.refresh()
        self._workspace.show()
        self._workspace.raise_()
        self._workspace.activateWindow()
        log("workspace opened")
    def _on_workspace_capture(self, kind: str) -> None:
        if kind == "record":
            self.toggle_recording()
        else:
            if self._workspace is not None:
                self._workspace.hide()
            self.capture(kind)

    def _on_workspace_share(self, action: str, path: Path) -> None:
        if action == "copy_image":
            image = imageutil.open_image(path)
            if image is not None:
                self._copy_image(image)
                self._notify("Đã copy ảnh", path.name)
        elif action == "copy_path":
            QApplication.clipboard().setText(str(path))
            self._notify("Đã copy đường dẫn", str(path))
        elif action == "reveal":
            if not win32util.open_in_explorer(path, select=True):
                QApplication.clipboard().setText(str(path))
                self._notify("Không mở được Explorer", "Đã copy đường dẫn ảnh vào clipboard.")
        elif action == "delete":
            answer = QMessageBox.question(None, "Xoá ảnh", f"Xoá {path.name}?")
            if answer == QMessageBox.StandardButton.Yes:
                library.delete_path(path)
                if self._workspace is not None:
                    self._workspace.refresh()
                self._notify("Đã xoá", path.name)

    def _open_from_library(self, path: Path) -> None:
        image = imageutil.open_image(path)
        if image is None:
            QMessageBox.warning(None, "Không mở được", f"Không đọc được ảnh:\n{path}")
            return
        self.open_editor(image, f"thư viện: {path.name}")

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, None)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        win32util.set_autostart(self.settings.autostart)
        self.register_hotkeys()
        self._apply_quickbar_settings()
        self._tray.setToolTip("Mitscreen — chụp & quay màn hình")
        self._notify("Đã lưu cài đặt", "Phím tắt và tuỳ chọn đã được cập nhật.")

    def show_tray_help(self) -> None:
        """Explain how to un-hide the tray icon on Windows 11."""
        log("tray help requested")
        win32util.open_shell_target("ms-settings:taskbar")
        QMessageBox.information(
            None, "Hiện icon Mitscreen trong khay",
            "Windows 11 ẩn icon mới trong khay hệ thống.\n\n"
            "1. Bảng Settings → Taskbar vừa mở: chọn «Other system tray icons».\n"
            "2. Bật công tắc của Mitscreen.\n\n"
            "Cách khác: bấm mũi tên ^ cạnh đồng hồ để mở khay ẩn, rồi kéo icon "
            "Mitscreen xuống thanh taskbar.\n\n"
            "Trong lúc chưa hiện được, anh vẫn dùng được thanh nổi trên màn hình "
            "hoặc các phím tắt.")

    def show_about(self) -> None:
        hotkeys = "\n".join(
            f"  • {HOTKEY_LABELS[k]}: {self.settings.hotkeys.get(k) or '(tắt)'}"
            for k in HOTKEY_LABELS)
        QMessageBox.information(
            None, "Mitscreen",
            "Mitscreen 1.0 — công cụ chụp & quay màn hình cá nhân.\n\n"
            "Phím tắt hiện tại:\n" + hotkeys + "\n\n"
            "Mẹo: khi chọn vùng, bấm vào một cửa sổ để chụp nguyên cửa sổ đó; "
            "giữ Shift khi kéo để vẽ hình vuông/đường 45°; Ctrl+lăn chuột để zoom trong trình sửa.")

    def _open_save_folder(self) -> None:
        path = self.settings.save_path
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        if win32util.open_in_explorer(path):
            log(f"opened save folder: {path}")
            return
        log(f"could not open save folder: {path}")
        QApplication.clipboard().setText(str(path))
        self._notify("Không mở được thư mục",
                     f"Đã copy đường dẫn: {path}")

    # ------------------------------------------------------------------ tray
    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.capture("region")

    def _notify(self, title: str, message: str) -> None:
        try:
            self._tray.showMessage(title, message, icons.icon("snap"), 2800)
        except Exception:
            pass

    def ping(self) -> None:
        """Another launch happened while we are running: show the panel."""
        log("second instance pinged")
        self._notify("Mitscreen đang chạy", "Đã mở bảng điều khiển.")
        self.show_history()

    # ------------------------------------------------------------------ quit
    def quit(self) -> None:
        if self._recorder.state() != self._recorder.ProcessState.NotRunning:
            self._recorder.stop_recording()
            self._recorder.waitForFinished(3000)
        self._hotkeys.unregister_all()
        for window in list(self._editors):
            window.close()
        if self._workspace is not None:
            self._workspace.close()
        self._tray.hide()
        self.app.quit()
