from typing import Dict, Optional
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap

from ui.widgets.thumbnail import ThumbnailWidget

class PlaylistCard(QFrame):
    clicked          = pyqtSignal(dict)                  
    play_requested   = pyqtSignal(dict)
    download_requested = pyqtSignal(dict)

    def __init__(self, playlist_data: Dict, card_width: int = 160, parent=None):
        super().__init__(parent)
        self.playlist_data = playlist_data
        self._card_width   = card_width

        self.setObjectName("card")
        self.setFixedWidth(card_width)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 12)
        layout.setSpacing(8)

        thumb_size = self._card_width - 20
        self._thumb = ThumbnailWidget(size=thumb_size, radius=10)
        thumbnails  = self.playlist_data.get("thumbnails") or []
        url = self._best_thumb(thumbnails)
        if url:
            self._thumb.set_url(url)
        layout.addWidget(self._thumb, alignment=Qt.AlignmentFlag.AlignCenter)

        title = self.playlist_data.get("title") or self.playlist_data.get("name", "")
        self._name_lbl = QLabel(title)
        self._name_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self._name_lbl.setStyleSheet("color: #EFEFEF;")
        self._name_lbl.setWordWrap(True)
        self._name_lbl.setMaximumHeight(40)
        layout.addWidget(self._name_lbl)

        sub_parts = []
        author = self.playlist_data.get("author") or {}
        if isinstance(author, dict):
            author_name = author.get("name", "")
            if author_name:
                sub_parts.append(author_name)
        count = self.playlist_data.get("count", "") or self.playlist_data.get("song_count", "")
        if count:
            sub_parts.append(f"{count} şarkı")

        if sub_parts:
            sub_lbl = QLabel(" · ".join(str(p) for p in sub_parts))
            sub_lbl.setFont(QFont("Segoe UI", 10))
            sub_lbl.setStyleSheet("color: #777777;")
            sub_lbl.setWordWrap(True)
            layout.addWidget(sub_lbl)

    def _best_thumb(self, thumbnails) -> str:
        if not thumbnails:
            return ""
        best = max(thumbnails, key=lambda t: t.get("width", 0) if isinstance(t, dict) else 0)
        return best.get("url", "") if isinstance(best, dict) else ""

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.playlist_data)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self.setStyleSheet("QFrame#card { background-color: #212121; border-color: #444444; }")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet("")
        super().leaveEvent(event)

class LocalPlaylistCard(QFrame):
    clicked = pyqtSignal(int)                
    play_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)

    def __init__(self, playlist: Dict, card_width: int = 160, parent=None):
        super().__init__(parent)
        self.playlist = playlist
        self._card_width = card_width

        self.setObjectName("card")
        self.setFixedWidth(card_width)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 12)
        layout.setSpacing(8)

        thumb_size = self._card_width - 20
        self._thumb = ThumbnailWidget(size=thumb_size, radius=10)
        cover = self.playlist.get("cover_path", "")
        if cover:
            pixmap = QPixmap(cover)
            if not pixmap.isNull():
                self._thumb.set_pixmap_direct(pixmap)
        layout.addWidget(self._thumb, alignment=Qt.AlignmentFlag.AlignCenter)

        self._name_lbl = QLabel(self.playlist.get("name", ""))
        self._name_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self._name_lbl.setStyleSheet("color: #EFEFEF;")
        self._name_lbl.setWordWrap(True)
        layout.addWidget(self._name_lbl)

        count = self.playlist.get("song_count", 0)
        count_lbl = QLabel(f"{count} şarkı")
        count_lbl.setFont(QFont("Segoe UI", 10))
        count_lbl.setStyleSheet("color: #777777;")
        layout.addWidget(count_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.playlist["id"])
        super().mousePressEvent(event)
