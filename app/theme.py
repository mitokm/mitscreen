"""Dark theme + stylesheet (all sizes scaled for the host DPI)."""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication


def apply(app: QApplication, scale: float = 1.0) -> None:
    scale = max(1.0, min(2.0, scale))
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#15171b"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e6e8ec"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#1c1f25"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#22262d"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#22262d"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#e6e8ec"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#e6e8ec"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#23272f"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e6e8ec"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ff5c5c"))
    palette.setColor(QPalette.ColorRole.Link, QColor("#5b9bff"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#2563eb"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    base = round(13 * scale)
    small = round(11.5 * scale)
    app.setStyleSheet(f"""
        QWidget {{ background: #15171b; color: #e6e8ec; font-family: "Segoe UI"; font-size: {base}px; }}
        QMainWindow, QDialog {{ background: #15171b; }}
        QToolBar {{ background: #1a1d22; border: none; border-bottom: 1px solid #262a31;
                    spacing: 4px; padding: 4px; }}
        QToolBar::separator {{ background: #2b3039; width: 1px; margin: 4px 6px; }}
        QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: 7px;
                       padding: 5px; color: #e6e8ec; }}
        QToolButton:hover {{ background: #262b34; border-color: #333a45; }}
        QToolButton:checked {{ background: #1d3a6e; border-color: #2f5fb0; }}
        QToolButton::menu-indicator {{ image: none; }}
        QStatusBar {{ background: #1a1d22; color: #9aa3b2; border-top: 1px solid #262a31;
                      font-size: {small}px; }}
        QLabel {{ background: transparent; }}
        QMenu {{ background: #1c2027; border: 1px solid #2c323b; padding: 6px; border-radius: 8px; }}
        QMenu::item {{ padding: 7px 26px 7px 14px; border-radius: 5px; }}
        QMenu::item:selected {{ background: #2563eb; color: white; }}
        QMenu::separator {{ height: 1px; background: #2c323b; margin: 5px 8px; }}
        QPushButton {{ background: #23272f; border: 1px solid #333a45; border-radius: 7px;
                       padding: 7px 14px; }}
        QPushButton:hover {{ background: #2b3139; }}
        QPushButton:default {{ background: #2563eb; border-color: #2563eb; font-weight: 600; }}
        QPushButton:default:hover {{ background: #3b7bff; }}
        QLineEdit, QSpinBox, QComboBox, QKeySequenceEdit {{
            background: #1c2027; border: 1px solid #333a45; border-radius: 6px; padding: 5px 8px;
            selection-background-color: #2563eb; }}
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QKeySequenceEdit:focus {{
            border-color: #3b7bff; }}
        QComboBox QAbstractItemView {{ background: #1c2027; border: 1px solid #333a45;
                                       selection-background-color: #2563eb; }}
        QSlider::groove:horizontal {{ height: 4px; background: #2c323b; border-radius: 2px; }}
        QSlider::sub-page:horizontal {{ background: #2563eb; border-radius: 2px; }}
        QSlider::handle:horizontal {{ background: #e6e8ec; width: 13px; height: 13px;
                                      margin: -5px 0; border-radius: 7px; }}
        QListWidget {{ background: #131519; border: 1px solid #262a31; border-radius: 8px; }}
        QListWidget::item {{ color: #cfd6e2; border-radius: 6px; padding: 4px; }}
        QListWidget::item:selected {{ background: #1d3a6e; color: white; }}
        QCheckBox {{ spacing: 8px; }}
        QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px;
                               border: 1px solid #3a4150; background: #1c2027; }}
        QCheckBox::indicator:checked {{ background: #2563eb; border-color: #2563eb; }}
        QTabWidget::pane {{ border: 1px solid #262a31; border-radius: 8px; top: -1px; }}
        QTabBar::tab {{ background: transparent; padding: 8px 16px; color: #9aa3b2;
                        border-bottom: 2px solid transparent; }}
        QTabBar::tab:selected {{ color: #e6e8ec; border-bottom: 2px solid #2563eb; }}
        QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
        QScrollBar::handle:vertical {{ background: #333a45; border-radius: 5px; min-height: 24px; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
        QGroupBox {{ border: 1px solid #262a31; border-radius: 8px; margin-top: 14px;
                     padding-top: 10px; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px;
                            color: #9aa3b2; font-size: {small}px; }}
    """)

    font = QFont("Segoe UI")
    font.setPixelSize(base)
    app.setFont(font)
