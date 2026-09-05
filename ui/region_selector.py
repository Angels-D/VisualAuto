from PySide6.QtCore import Qt, QRect, Signal, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtWidgets import QWidget, QApplication


class RegionSelector(QWidget):
    region_selected = Signal(int, int, int, int)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        screen = QApplication.primaryScreen()
        self._dpr = 1.0
        if screen:
            geo = screen.geometry()
            self.setGeometry(geo)
            self._dpr = screen.devicePixelRatio()

        self._start = QPoint()
        self._end = QPoint()
        self._selecting = False
        self._selection = QRect()

        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start = event.position().toPoint()
            self._end = self._start
            self._selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self._selecting:
            self._end = event.position().toPoint()
            self._selection = QRect(self._start, self._end).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._selecting = False
            self._selection = QRect(self._start, self._end).normalized()
            if self._selection.width() > 5 and self._selection.height() > 5:
                dpr = self._dpr
                x = int(self._selection.x() * dpr)
                y = int(self._selection.y() * dpr)
                w = int(self._selection.width() * dpr)
                h = int(self._selection.height() * dpr)
                self.hide()
                self.region_selected.emit(x, y, w, h)
            else:
                self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setBrush(QColor(0, 0, 0, 80))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())

        if self._selecting and not self._selection.isEmpty():
            sel = self._selection
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.drawRect(sel)

            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            pen = QPen(QColor(0, 255, 100), 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(sel)

            painter.setPen(QColor(255, 255, 255))
            painter.drawText(
                sel.x() + 5,
                sel.y() - 8 if sel.y() > 20 else sel.y() + sel.height() + 15,
                f"{sel.width()} x {sel.height()}",
            )

        painter.end()