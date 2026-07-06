import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, pyqtProperty
from PyQt6.QtGui import QPainter, QPen, QColor, QFont

class ProgressRing(QWidget):
    def __init__(self, size: int = 40, parent=None):
        super().__init__(parent)
        self._size     = size
        self._progress = 0
        self._color    = QColor("#FF0033")
        self._bg_color = QColor("#2A2A2A")
        self._width    = 4

        self.setFixedSize(size, size)

    def set_progress(self, value: float):
        self._progress = max(0, min(100, value))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        margin  = self._width
        rect    = QRectF(margin, margin,
                         self._size - 2 * margin,
                         self._size - 2 * margin)

        pen = QPen(self._bg_color, self._width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawEllipse(rect)

        if self._progress > 0:
            pen = QPen(self._color, self._width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            span = int(-self._progress * 360 / 100 * 16)
            painter.drawArc(rect, 90 * 16, span)

        if 0 < self._progress < 100:
            painter.setPen(QColor("#EFEFEF"))
            font = QFont("Segoe UI", max(7, self._size // 6))
            painter.setFont(font)
            painter.drawText(
                QRectF(0, 0, self._size, self._size),
                Qt.AlignmentFlag.AlignCenter,
                f"{int(self._progress)}%"
            )
        elif self._progress >= 100:
            painter.setPen(QColor("#FF0033"))
            font = QFont("Segoe UI", max(8, self._size // 5))
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                QRectF(0, 0, self._size, self._size),
                Qt.AlignmentFlag.AlignCenter,
                "✓"
            )
