from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QColor, QBrush

from core.cache import get_cache

class ThumbnailWidget(QLabel):
    clicked = pyqtSignal()

    def __init__(self, size: int = 120, radius: int = 8, parent=None):
        super().__init__(parent)
        self._size   = size
        self._radius = radius
        self._url    = ""
        self._raw_pixmap: QPixmap = QPixmap()

        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_placeholder()

        cache = get_cache()
        cache.thumbnail_ready.connect(self._on_cache_ready)

    def set_url(self, url: str):
        if url == self._url:
            return
        self._url = url
        if not url:
            self._set_placeholder()
            return

        cache = get_cache()
        pixmap = cache.get(url, self._size)
        if pixmap:
            self._apply_pixmap(pixmap)
        else:
            self._set_placeholder()

    def set_pixmap_direct(self, pixmap: QPixmap):
        self._raw_pixmap = pixmap
        self._apply_pixmap(pixmap)

    def _on_cache_ready(self, url: str, pixmap: QPixmap):
        if url == self._url:
            self._apply_pixmap(pixmap)

    def _apply_pixmap(self, pixmap: QPixmap):
        if pixmap.isNull():
            return
               
        scaled = pixmap.scaled(
            self._size, self._size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
                 
        rounded = self._make_rounded(scaled)
        self.setPixmap(rounded)

    def _make_rounded(self, pixmap: QPixmap) -> QPixmap:
        result = QPixmap(self._size, self._size)
        result.fill(Qt.GlobalColor.transparent)

        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self._size, self._size, self._radius, self._radius)
        painter.setClipPath(path)

        x = (self._size - pixmap.width()) // 2
        y = (self._size - pixmap.height()) // 2
        painter.drawPixmap(x, y, pixmap)
        painter.end()

        return result

    def _set_placeholder(self):
        pixmap = QPixmap(self._size, self._size)
        pixmap.fill(QColor("#1A1A1A"))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#333333"))

        from PyQt6.QtGui import QFont
        font = QFont("Segoe UI")
        font.setPointSize(self._size // 4)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "♪")
        painter.end()

        self.setPixmap(self._make_rounded(pixmap))

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
