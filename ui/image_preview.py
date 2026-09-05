from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QScrollArea


class ImagePreviewDialog(QDialog):
    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("图片预览")
        self.resize(600, 500)
        self.setWindowFlags(
            Qt.Dialog
            | Qt.WindowCloseButtonHint
            | Qt.WindowTitleHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignCenter)

        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            label.setPixmap(pixmap.scaled(
                580, 460,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            ))
        else:
            label.setText("无法加载图片")

        scroll.setWidget(label)
        layout.addWidget(scroll)