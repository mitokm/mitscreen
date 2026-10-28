"""Settings dialog."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeySequence
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog,
                               QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox,
                               QHBoxLayout, QKeySequenceEdit, QLabel, QLineEdit, QPushButton,
                               QSlider, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from .config import (AFTER_CAPTURE_OPTIONS, DEFAULT_HOTKEYS, HOTKEY_LABELS, Settings,
                     sanitize_pattern)


class SettingsDialog(QDialog):
    """Edits a Settings instance in place; the caller persists it."""

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Cài đặt Mitscreen")
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        tabs = QTabWidget(self)
        layout.addWidget(tabs)
        tabs.addTab(self._capture_tab(), "Chụp ảnh")
        tabs.addTab(self._hotkey_tab(), "Phím tắt")
        tabs.addTab(self._record_tab(), "Quay && hệ thống")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel
                                   | QDialogButtonBox.StandardButton.RestoreDefaults)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Lưu")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Huỷ")
        buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).setText("Mặc định")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(self._reset)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------ tabs
    def _capture_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)

        row = QHBoxLayout()
        self.save_dir_edit = QLineEdit(self.settings.save_dir or str(self.settings.save_path))
        browse = QPushButton("Chọn…")
        browse.clicked.connect(self._pick_dir)
        row.addWidget(self.save_dir_edit, 1)
        row.addWidget(browse)
        form.addRow("Thư mục lưu:", row)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["png", "jpg", "webp"])
        self.format_combo.setCurrentText(
            "jpg" if self.settings.image_format in ("jpg", "jpeg") else self.settings.image_format)
        form.addRow("Định dạng:", self.format_combo)

        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(40, 100)
        self.quality_slider.setValue(self.settings.jpg_quality)
        form.addRow("Chất lượng JPEG/WebP:", self.quality_slider)

        size_group = QGroupBox("Ảnh && dung lượng")
        size_form = QFormLayout(size_group)
        self.dpi_combo = QComboBox()
        for dpi in (72, 96, 150, 300):
            self.dpi_combo.addItem(f"{dpi} dpi", dpi)
        self.dpi_combo.setCurrentIndex(max(0, self.dpi_combo.findData(self.settings.export_dpi)))
        self.dpi_combo.setToolTip("DPI ghi vào tệp (metadata) — không đổi số điểm ảnh.")
        size_form.addRow("DPI khi lưu:", self.dpi_combo)

        self.scale_combo = QComboBox()
        for percent in (100, 90, 75, 50, 25):
            self.scale_combo.addItem(f"{percent} %", percent)
        self.scale_combo.setCurrentIndex(
            max(0, self.scale_combo.findData(self.settings.export_scale)))
        self.scale_combo.setToolTip("Thu nhỏ ảnh khi lưu — cách giảm dung lượng mạnh nhất.")
        size_form.addRow("Kích thước khi lưu:", self.scale_combo)

        self.png_slider = QSlider(Qt.Orientation.Horizontal)
        self.png_slider.setRange(1, 9)
        self.png_slider.setValue(self.settings.png_compress)
        self.png_slider.setToolTip("9 = nén kỹ nhất, tệp PNG nhỏ nhất (chậm hơn một chút).")
        size_form.addRow("Nén PNG (1–9):", self.png_slider)

        size_hint = QLabel("Muốn nhẹ hơn nữa: chọn định dạng WebP, hoặc giảm % kích thước.")
        size_hint.setStyleSheet("color: #9aa3b2;")
        size_hint.setWordWrap(True)
        size_form.addRow(size_hint)
        form.addRow(size_group)

        name_group = QGroupBox("Tên tệp")
        name_form = QFormLayout(name_group)
        self.name_pattern = QLineEdit(self.settings.filename_pattern)
        self.name_pattern.setPlaceholderText("snap-%Y%m%d-%H%M%S")
        name_form.addRow("Mẫu tên:", self.name_pattern)
        self.name_preview = QLabel("")
        self.name_preview.setStyleSheet("color: #9aa3b2; font-family: Consolas;")
        name_form.addRow("Xem trước:", self.name_preview)
        self.ask_name = QCheckBox("Hỏi tên mỗi khi lưu ảnh mới")
        self.ask_name.setChecked(self.settings.ask_name_on_save)
        name_form.addRow("", self.ask_name)
        name_hint = QLabel("Dùng mã thời gian: %Y năm · %m tháng · %d ngày · %H giờ · "
                           "%M phút · %S giây.")
        name_hint.setStyleSheet("color: #9aa3b2;")
        name_hint.setWordWrap(True)
        name_form.addRow(name_hint)
        form.addRow(name_group)
        self.name_pattern.textChanged.connect(self._update_name_preview)
        self.format_combo.currentTextChanged.connect(self._update_name_preview)
        self._update_name_preview()

        self.after_combo = QComboBox()
        for key, label in AFTER_CAPTURE_OPTIONS.items():
            self.after_combo.addItem(label, key)
        index = self.after_combo.findData(self.settings.after_capture)
        self.after_combo.setCurrentIndex(max(0, index))
        self.after_combo.setToolTip(
            "Ảnh chụp luôn được tự lưu vào thư mục lưu ảnh ngay khi chụp; "
            "mở trình sửa là sửa trên chính bản đã lưu đó (Ctrl+S ghi đè).")
        form.addRow("Sau khi chụp xong:", self.after_combo)

        self.auto_copy = QCheckBox("Tự copy vào clipboard khi bấm Lưu nhanh")
        self.auto_copy.setChecked(self.settings.auto_copy)
        form.addRow("", self.auto_copy)

        self.keep_library = QCheckBox("Lưu bản sao vào thư viện ảnh")
        self.keep_library.setChecked(self.settings.keep_library)
        form.addRow("", self.keep_library)

        self.pretty_frame = QCheckBox("Mặc định thêm khung viền + bóng đổ")
        self.pretty_frame.setChecked(self.settings.pretty_frame)
        form.addRow("", self.pretty_frame)

        watermark = QGroupBox("Watermark")
        wform = QFormLayout(watermark)
        self.watermark_enabled = QCheckBox("Bật watermark khi lưu nhanh")
        self.watermark_enabled.setChecked(self.settings.watermark_enabled)
        wform.addRow("", self.watermark_enabled)
        self.watermark_text = QLineEdit(self.settings.watermark_text)
        self.watermark_text.setPlaceholderText("Ví dụ: Mit — nội bộ")
        wform.addRow("Nội dung:", self.watermark_text)
        wrow = QHBoxLayout()
        self.watermark_color_btn = QPushButton()
        self.watermark_color_btn.setFixedWidth(80)
        self._paint_color_button(self.settings.watermark_color)
        self.watermark_color_btn.clicked.connect(self._pick_watermark_color)
        self.watermark_opacity = QSlider(Qt.Orientation.Horizontal)
        self.watermark_opacity.setRange(10, 100)
        self.watermark_opacity.setValue(self.settings.watermark_opacity)
        wrow.addWidget(self.watermark_color_btn)
        wrow.addWidget(QLabel("Độ đậm:"))
        wrow.addWidget(self.watermark_opacity, 1)
        wform.addRow("Màu:", wrow)
        form.addRow(watermark)
        return page

    def _hotkey_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)
        hint = QLabel("Bấm vào ô rồi nhấn tổ hợp phím. Để trống để tắt phím tắt đó.")
        hint.setStyleSheet("color: #9aa3b2;")
        hint.setWordWrap(True)
        form.addRow(hint)
        self.hotkey_edits: dict[str, QKeySequenceEdit] = {}
        for key, label in HOTKEY_LABELS.items():
            edit = QKeySequenceEdit()
            sequence = QKeySequence(self.settings.hotkeys.get(key, DEFAULT_HOTKEYS[key]))
            edit.setKeySequence(sequence)
            form.addRow(f"{label}:", edit)
            self.hotkey_edits[key] = edit
        reset = QPushButton("Đặt lại phím mặc định")
        reset.clicked.connect(self._reset_hotkeys)
        form.addRow("", reset)
        return page

    def _record_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(5, 60)
        self.fps_spin.setValue(self.settings.record_fps)
        self.fps_spin.setSuffix(" fps")
        form.addRow("Tốc độ khung hình:", self.fps_spin)

        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setValue(self.settings.record_crf)
        self.crf_spin.setToolTip("Thấp = nét hơn, tệp lớn hơn (khuyến nghị 20–28)")
        form.addRow("Chất lượng (CRF):", self.crf_spin)

        self.show_cursor = QCheckBox("Hiện con trỏ chuột khi quay")
        self.show_cursor.setChecked(self.settings.show_cursor_in_recordings)
        form.addRow("", self.show_cursor)

        bar_group = QGroupBox("Thanh truy cập nhanh")
        bar_form = QFormLayout(bar_group)
        self.show_quickbar = QCheckBox("Bật thanh truy cập nhanh (Quick Bar)")
        self.show_quickbar.setChecked(self.settings.show_quickbar)
        self.show_quickbar.setToolTip("Bỏ chọn = tắt hẳn thanh nổi và Người Nhện treo trên màn hình")
        bar_form.addRow("", self.show_quickbar)
        self.quickbar_autohide = QCheckBox("Tự thu lại thành Người Nhện treo khi không dùng")
        self.quickbar_autohide.setChecked(self.settings.quickbar_autohide)
        bar_form.addRow("", self.quickbar_autohide)
        bar_hint = QLabel("Kéo thanh ở vùng trống để đổi vị trí; rê chuột vào thanh (hoặc vào Người Nhện) để bung ra.")
        bar_hint.setStyleSheet("color: #9aa3b2;")
        bar_hint.setWordWrap(True)
        bar_form.addRow(bar_hint)
        form.addRow(bar_group)

        self.autostart = QCheckBox("Khởi động cùng Windows")
        self.autostart.setChecked(self.settings.autostart)
        form.addRow("", self.autostart)

        note = QLabel("Video được lưu vào thư mục lưu ảnh với tên rec-<ngày>-<giờ>.mp4")
        note.setStyleSheet("color: #9aa3b2;")
        note.setWordWrap(True)
        form.addRow(note)
        return page

    # --------------------------------------------------------------- helpers
    def _paint_color_button(self, color: str) -> None:
        self._watermark_color = color
        self.watermark_color_btn.setStyleSheet(
            f"background: {color}; border: 1px solid #444b58; border-radius: 6px; min-height: 22px;")

    def _pick_watermark_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._watermark_color), self, "Màu watermark")
        if color.isValid():
            self._paint_color_button(color.name())

    def _update_name_preview(self, *_args) -> None:
        pattern = sanitize_pattern(self.name_pattern.text())
        try:
            sample = datetime.now().strftime(pattern)
        except ValueError:
            sample = "(mẫu không hợp lệ)"
        suffix = self.format_combo.currentText()
        self.name_preview.setText(f"{sample}.{suffix}")

    def _pick_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu",
                                                     self.save_dir_edit.text())
        if directory:
            self.save_dir_edit.setText(directory)
            self.settings.extra["save_dir_chosen"] = True

    def _reset_hotkeys(self) -> None:
        for key, edit in self.hotkey_edits.items():
            edit.setKeySequence(QKeySequence(DEFAULT_HOTKEYS[key]))

    def _reset(self) -> None:
        defaults = Settings()
        self.format_combo.setCurrentText(defaults.image_format)
        self.quality_slider.setValue(defaults.jpg_quality)
        self.name_pattern.setText(defaults.filename_pattern)
        self.ask_name.setChecked(defaults.ask_name_on_save)
        self.dpi_combo.setCurrentIndex(max(0, self.dpi_combo.findData(defaults.export_dpi)))
        self.scale_combo.setCurrentIndex(max(0, self.scale_combo.findData(defaults.export_scale)))
        self.png_slider.setValue(defaults.png_compress)
        self.after_combo.setCurrentIndex(max(0, self.after_combo.findData(defaults.after_capture)))
        self.auto_copy.setChecked(defaults.auto_copy)
        self.keep_library.setChecked(defaults.keep_library)
        self.pretty_frame.setChecked(defaults.pretty_frame)
        self.fps_spin.setValue(defaults.record_fps)
        self.crf_spin.setValue(defaults.record_crf)
        self.show_cursor.setChecked(defaults.show_cursor_in_recordings)
        self.show_quickbar.setChecked(defaults.show_quickbar)
        self.quickbar_autohide.setChecked(defaults.quickbar_autohide)
        self.watermark_enabled.setChecked(False)
        self.watermark_text.setText("")
        self._reset_hotkeys()

    # ---------------------------------------------------------------- accept
    def accept(self) -> None:  # noqa: D401
        s = self.settings
        chosen = self.save_dir_edit.text().strip()
        s.save_dir = chosen
        s.image_format = self.format_combo.currentText()
        s.jpg_quality = self.quality_slider.value()
        s.filename_pattern = sanitize_pattern(self.name_pattern.text())
        s.ask_name_on_save = self.ask_name.isChecked()
        s.export_dpi = self.dpi_combo.currentData() or 96
        s.export_scale = self.scale_combo.currentData() or 100
        s.png_compress = self.png_slider.value()
        s.after_capture = self.after_combo.currentData() or "copy_edit"
        s.auto_copy = self.auto_copy.isChecked()
        s.keep_library = self.keep_library.isChecked()
        s.pretty_frame = self.pretty_frame.isChecked()
        s.watermark_enabled = self.watermark_enabled.isChecked()
        s.watermark_text = self.watermark_text.text().strip()
        s.watermark_color = self._watermark_color
        s.watermark_opacity = self.watermark_opacity.value()
        s.record_fps = self.fps_spin.value()
        s.record_crf = self.crf_spin.value()
        s.show_cursor_in_recordings = self.show_cursor.isChecked()
        s.show_quickbar = self.show_quickbar.isChecked()
        s.quickbar_autohide = self.quickbar_autohide.isChecked()
        s.autostart = self.autostart.isChecked()
        for key, edit in self.hotkey_edits.items():
            text = edit.keySequence().toString(QKeySequence.SequenceFormat.PortableText)
            s.hotkeys[key] = text or ""
        s._sanitize()
        s.ensure_dirs()
        s.save()
        super().accept()
