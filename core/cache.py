import os
import hashlib
import threading
from typing import Optional, Dict
from io import BytesIO

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

BASE_DIR    = os.path.dirname(os.path.dirname(__file__))
CACHE_DIR   = os.path.join(BASE_DIR, "data", "cache", "thumbnails")
MEMORY_LIMIT = 200                                    

class ThumbnailLoader(QThread):
    loaded = pyqtSignal(str, QPixmap)               

    def __init__(self, url: str, size: int = 120):
        super().__init__()
        self.url  = url
        self.size = size

    def run(self):
        try:
            import requests
            from PIL import Image

            r = requests.get(self.url, timeout=8)
            if r.status_code != 200:
                return

            img = Image.open(BytesIO(r.content))
                       
            w, h = img.size
            side = min(w, h)
            left = (w - side) // 2
            top  = (h - side) // 2
            img  = img.crop((left, top, left + side, top + side))
            img  = img.resize((self.size, self.size), Image.LANCZOS)
            img  = img.convert("RGB")

            buf = BytesIO()
            img.save(buf, format="JPEG", quality=85)
            buf.seek(0)

            pixmap = QPixmap()
            pixmap.loadFromData(buf.read())
            self.loaded.emit(self.url, pixmap)

        except Exception as e:
            pass

class ThumbnailCache(QObject):
    thumbnail_ready = pyqtSignal(str, QPixmap)               

    def __init__(self, parent=None):
        super().__init__(parent)
        os.makedirs(CACHE_DIR, exist_ok=True)
        self._memory: Dict[str, QPixmap] = {}
        self._pending: Dict[str, ThumbnailLoader] = {}
        self._lock = threading.Lock()

    def get(self, url: str, size: int = 120) -> Optional[QPixmap]:
        if not url:
            return None

        with self._lock:
            if url in self._memory:
                return self._memory[url]

        disk_path = self._disk_path(url)
        if os.path.exists(disk_path):
            pixmap = QPixmap(disk_path)
            if not pixmap.isNull():
                with self._lock:
                    self._add_to_memory(url, pixmap)
                return pixmap

        with self._lock:
            if url not in self._pending:
                loader = ThumbnailLoader(url, size)
                loader.loaded.connect(self._on_loaded)
                loader.finished.connect(lambda: self._pending.pop(url, None))
                self._pending[url] = loader
                loader.start()

        return None

    def get_or_placeholder(self, url: str, size: int = 120) -> QPixmap:
        result = self.get(url, size)
        if result:
            return result
        return self._make_placeholder(size)

    def _on_loaded(self, url: str, pixmap: QPixmap):
        if pixmap.isNull():
            return
                      
        disk_path = self._disk_path(url)
        pixmap.save(disk_path, "JPEG")
                      
        with self._lock:
            self._add_to_memory(url, pixmap)
        self.thumbnail_ready.emit(url, pixmap)

    def _add_to_memory(self, url: str, pixmap: QPixmap):
        if len(self._memory) >= MEMORY_LIMIT:
                                             
            oldest_key = next(iter(self._memory))
            del self._memory[oldest_key]
        self._memory[url] = pixmap

    def _disk_path(self, url: str) -> str:
        name = hashlib.md5(url.encode()).hexdigest() + ".jpg"
        return os.path.join(CACHE_DIR, name)

    def _make_placeholder(self, size: int) -> QPixmap:
        from PyQt6.QtGui import QPainter, QColor, QFont
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor("#242424"))
        painter = QPainter(pixmap)
        painter.setPen(QColor("#555555"))
        font = QFont()
        font.setPointSize(size // 3)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), 0x84, "♪")               
        painter.end()
        return pixmap

    def clear_memory(self):
        with self._lock:
            self._memory.clear()

_cache: Optional[ThumbnailCache] = None

def get_cache() -> ThumbnailCache:
    global _cache
    if _cache is None:
        _cache = ThumbnailCache()
    return _cache
