from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtWidgets import QWidget, QApplication


class DetectionOverlay(QWidget):
    CORNER_LEN = 20
    LINE_WIDTH = 3
    DOT_RADIUS = 8

    def __init__(self, x: int, y: int, w: int, h: int, target_x: int = None, target_y: int = None):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        screen = QApplication.primaryScreen()
        dpr = screen.devicePixelRatio() if screen else 1.0

        self._box_x = int(x / dpr)
        self._box_y = int(y / dpr)
        self._box_w = int(w / dpr)
        self._box_h = int(h / dpr)

        if target_x is not None and target_y is not None:
            self._target_x = int(target_x / dpr)
            self._target_y = int(target_y / dpr)
            self._show_target = True
        else:
            self._target_x = self._box_x + self._box_w // 2
            self._target_y = self._box_y + self._box_h // 2
            self._show_target = True

        sg = screen.geometry() if screen else None
        if sg:
            self.setGeometry(sg)
        else:
            self.setGeometry(0, 0, 1920, 1080)

        self._accepting_clicks = False
        QTimer.singleShot(200, self._enable_clicks)

    def _enable_clicks(self):
        self._accepting_clicks = True

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        bx, by = self._box_x, self._box_y
        bw, bh = self._box_w, self._box_h
        cl = self.CORNER_LEN
        lw = self.LINE_WIDTH

        pen = QPen(QColor(0, 255, 100), lw, Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(bx, by, bw, bh)

        painter.setPen(QPen(QColor(0, 255, 100), lw))

        painter.drawLine(bx, by, bx + cl, by)
        painter.drawLine(bx, by, bx, by + cl)

        painter.drawLine(bx + bw, by, bx + bw - cl, by)
        painter.drawLine(bx + bw, by, bx + bw, by + cl)

        painter.drawLine(bx, by + bh, bx + cl, by + bh)
        painter.drawLine(bx, by + bh, bx, by + bh - cl)

        painter.drawLine(bx + bw, by + bh, bx + bw - cl, by + bh)
        painter.drawLine(bx + bw, by + bh, bx + bw, by + bh - cl)

        if self._show_target:
            tx, ty = self._target_x, self._target_y
            r = self.DOT_RADIUS

            painter.setBrush(QColor(255, 60, 60, 220))
            painter.setPen(QPen(QColor(255, 255, 255, 200), 2))
            painter.drawEllipse(tx - r, ty - r, r * 2, r * 2)

            painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
            cross_r = r + 4
            painter.drawLine(tx - cross_r, ty, tx + cross_r, ty)
            painter.drawLine(tx, ty - cross_r, tx, ty + cross_r)

        painter.end()

    def mousePressEvent(self, event):
        if self._accepting_clicks:
            self.close()

    def keyPressEvent(self, event):
        if self._accepting_clicks:
            self.close()