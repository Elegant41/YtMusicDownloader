import math
import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient

class WaveformWidget(QWidget):
    def __init__(self, bar_count: int = 24, parent=None):
        super().__init__(parent)
        self._bar_count = bar_count
        self._heights   = [0.3 + random.random() * 0.4 for _ in range(bar_count)]
        self._targets   = list(self._heights)
        self._phases    = [random.random() * math.pi * 2 for _ in range(bar_count)]
        self._active    = False
        self._time      = 0

        self._color_start = QColor("#FF0033")
        self._color_end   = QColor("#FF4D6D")

        self._timer = QTimer()
        self._timer.setInterval(40)          
        self._timer.timeout.connect(self._tick)

        self.setMinimumHeight(32)
        self.setMaximumHeight(48)

    def start(self):
        self._active = True
        self._timer.start()

    def stop(self):
        self._active = False
        self._timer.stop()
                        
        self._heights = [h * 0.3 for h in self._heights]
        self.update()

    def _tick(self):
        self._time += 0.08
        for i in range(self._bar_count):
            freq = 1.2 + (i / self._bar_count) * 1.8
            phase = self._phases[i]
            base = 0.35 + 0.25 * math.sin(self._time * freq + phase)
            noise = random.random() * 0.2
            self._heights[i] = base + noise
        self.update()

    def paintEvent(self, event):
        w = self.width()
        h = self.height()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bar_w   = max(2, (w - self._bar_count) / self._bar_count)
        spacing = 1
        total_w = (bar_w + spacing) * self._bar_count

        offset_x = (w - total_w) / 2

        for i, height_ratio in enumerate(self._heights):
            bar_h  = height_ratio * h
            x      = offset_x + i * (bar_w + spacing)
            y      = (h - bar_h) / 2

            grad = QLinearGradient(x, y, x, y + bar_h)
            grad.setColorAt(0, self._color_start)
            grad.setColorAt(1, self._color_end)

            from PyQt6.QtGui import QBrush
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)

            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h), bar_w / 2, bar_w / 2)

        painter.end()
