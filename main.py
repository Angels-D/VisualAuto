import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor, QFont

from core.data_manager import DataManager
from ui.main_window import MainWindow

STYLE_QSS = """
QMainWindow {
    background-color: #1e1e2e;
}

QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
}

QGroupBox {
    border: 1px solid #45475a;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
    font-size: 13px;
    color: #cdd6f4;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #89b4fa;
}

QLineEdit, QSpinBox, QComboBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
    color: #cdd6f4;
    selection-background-color: #89b4fa;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #89b4fa;
}

QComboBox::drop-down {
    border: none;
    padding-right: 6px;
}

QComboBox QAbstractItemView {
    background-color: #313244;
    border: 1px solid #45475a;
    color: #cdd6f4;
    selection-background-color: #45475a;
    font-size: 13px;
}

QPushButton {
    background-color: #45475a;
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
    color: #cdd6f4;
    font-weight: bold;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #585b70;
}

QPushButton:pressed {
    background-color: #313244;
}

QPushButton:disabled {
    background-color: #313244;
    color: #6c7086;
}

QListWidget {
    background-color: #181825;
    border: 1px solid #45475a;
    border-radius: 4px;
    outline: none;
}

QListWidget::item {
    padding: 2px;
    border-bottom: 1px solid #313244;
}

QListWidget::item:hover {
    background-color: #313244;
}

QListWidget::item:selected {
    background-color: #45475a;
}

QTextEdit {
    background-color: #181825;
    border: 1px solid #45475a;
    border-radius: 4px;
    color: #a6adc8;
    font-family: "Consolas", "Microsoft YaHei", monospace;
    font-size: 11px;
}

QScrollBar:vertical {
    background-color: #181825;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #181825;
    height: 8px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #45475a;
    border-radius: 4px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #585b70;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

QSlider::groove:horizontal {
    background-color: #313244;
    height: 6px;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background-color: #89b4fa;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}

QSlider::sub-page:horizontal {
    background-color: #89b4fa;
    border-radius: 3px;
}

QCheckBox {
    color: #cdd6f4;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #45475a;
    border-radius: 3px;
    background-color: #313244;
}

QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

QRadioButton {
    color: #cdd6f4;
    spacing: 6px;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #45475a;
    border-radius: 8px;
    background-color: #313244;
}

QRadioButton::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

QSplitter::handle {
    background-color: #45475a;
}

QMessageBox {
    background-color: #1e1e2e;
}

QMessageBox QLabel {
    color: #cdd6f4;
}

QDialog {
    background-color: #1e1e2e;
}

QLabel {
    color: #cdd6f4;
}
"""


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 9))
    app.setStyleSheet(STYLE_QSS)

    data_manager = DataManager()
    data_manager.load_materials()
    data_manager.load_scripts()

    window = MainWindow(data_manager)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()