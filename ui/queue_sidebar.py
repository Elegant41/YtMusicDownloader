from typing import List, Dict
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QScrollArea, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QRect, QEasingCurve
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent

from core.player import get_player
from ui.widgets.thumbnail import ThumbnailWidget

class QueueSongItem(QFrame):
    play_now    = pyqtSignal(int)          
    remove_from_queue = pyqtSignal(int)

    def __init__(self, song: Dict, index: int, is_current: bool = False, parent=None):
        super().__init__(parent)
        self.song  = song
        self.index = index
        self.setObjectName("song_row")
        self.setFixedHeight(56)
        self.setStyleSheet(
            "QFrame#song_row { background: rgba(255,0,51,0.12); border-radius: 6px; }"
            if is_current else ""
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        if is_current:
            idx_lbl = QLabel("▶")
            idx_lbl.setStyleSheet("color: #FF0033; font-weight: bold;")
        else:
            idx_lbl = QLabel(str(index + 1))
            idx_lbl.setStyleSheet("color: #555;")
        idx_lbl.setFixedWidth(20)
        idx_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(idx_lbl)

        thumb = ThumbnailWidget(size=40, radius=4)
        thumbnails = song.get("thumbnails") or []
        if thumbnails:
            best = max(thumbnails, key=lambda t: t.get("width", 0) if isinstance(t, dict) else 0)
            url = best.get("url", "") if isinstance(best, dict) else ""
            if url:
                thumb.set_url(url)
        layout.addWidget(thumb)

        info = QVBoxLayout()
        info.setSpacing(1)

        title = song.get("title", "Unknown")
        title_lbl = QLabel(title[:35] + ("..." if len(title) > 35 else ""))
        title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium if is_current else QFont.Weight.Normal))
        title_lbl.setStyleSheet("color: #FF0033;" if is_current else "color: #EFEFEF;")

        artists = song.get("artists") or []
        if artists and isinstance(artists[0], dict):
            artist = ", ".join(a.get("name", "") for a in artists)
        else:
            artist = song.get("artist", "")
        artist_lbl = QLabel(artist[:30])
        artist_lbl.setFont(QFont("Segoe UI", 10))
        artist_lbl.setStyleSheet("color: #666;")

        info.addWidget(title_lbl)
        info.addWidget(artist_lbl)
        layout.addLayout(info, stretch=1)

        self._remove_btn = QPushButton("✕")
        self._remove_btn.setObjectName("btn_icon")
        self._remove_btn.setFixedSize(24, 24)
        self._remove_btn.setVisible(False)
        self._remove_btn.clicked.connect(lambda: self.remove_from_queue.emit(self.index))
        layout.addWidget(self._remove_btn)

    def enterEvent(self, e):
        self._remove_btn.setVisible(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._remove_btn.setVisible(False)
        super().leaveEvent(e)

    def mouseDoubleClickEvent(self, e):
        self.play_now.emit(self.index)
        super().mouseDoubleClickEvent(e)

class QueueSidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._visible = False
        self.setObjectName("now_playing_bg")
        self.setFixedWidth(320)
        self._build_ui()
        self._connect_player()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        title_lbl = QLabel("Çalma Sırası")
        title_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #FFFFFF;")
        header_row.addWidget(title_lbl)
        header_row.addStretch()

        clear_btn = QPushButton("Temizle")
        clear_btn.setObjectName("btn_secondary")
        clear_btn.setFixedHeight(28)
        clear_btn.clicked.connect(self._clear_queue)
        header_row.addWidget(clear_btn)
        layout.addLayout(header_row)

        self._now_playing_frame = QFrame()
        self._now_playing_frame.setObjectName("card")
        self._now_playing_frame.setStyleSheet("""
            QFrame#card {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 rgba(255,0,51,0.15), stop:1 rgba(255,0,51,0.05));
                border: 1px solid rgba(255,0,51,0.3);
                border-radius: 10px;
            }
        """)
        now_layout = QHBoxLayout(self._now_playing_frame)
        now_layout.setContentsMargins(12, 10, 12, 10)
        now_layout.setSpacing(10)

        self._now_thumb = ThumbnailWidget(size=52, radius=6)
        now_layout.addWidget(self._now_thumb)

        now_info = QVBoxLayout()
        now_info.setSpacing(2)

        now_lbl = QLabel("ŞİMDİ ÇALIYOR")
        now_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        now_lbl.setStyleSheet("color: #FF0033; letter-spacing: 1px;")
        now_info.addWidget(now_lbl)

        self._now_title = QLabel("—")
        self._now_title.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        self._now_title.setStyleSheet("color: #FFFFFF;")
        now_info.addWidget(self._now_title)

        self._now_artist = QLabel("—")
        self._now_artist.setFont(QFont("Segoe UI", 11))
        self._now_artist.setStyleSheet("color: #AFAFAF;")
        now_info.addWidget(self._now_artist)

        now_layout.addLayout(now_info, stretch=1)
        self._now_playing_frame.setVisible(False)
        layout.addWidget(self._now_playing_frame)

        next_lbl = QLabel("Sıradaki")
        next_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        next_lbl.setStyleSheet("color: #AFAFAF;")
        layout.addWidget(next_lbl)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._queue_container = QWidget()
        self._queue_container.setStyleSheet("background: transparent;")
        self._queue_layout = QVBoxLayout(self._queue_container)
        self._queue_layout.setContentsMargins(0, 0, 0, 0)
        self._queue_layout.setSpacing(4)
        self._queue_layout.addStretch()

        self._empty_lbl = QLabel("Çalma sırası boş")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet("color: #444; font-size: 13px; padding: 40px;")
        self._queue_layout.insertWidget(0, self._empty_lbl)

        self._scroll.setWidget(self._queue_container)
        layout.addWidget(self._scroll, stretch=1)

    def _connect_player(self):
        player = get_player()
        player.queue_changed.connect(self._refresh_queue)
        player.track_changed.connect(self._on_track_changed)

    def _refresh_queue(self, queue: List[Dict]):
                 
        while self._queue_layout.count() > 1:
            item = self._queue_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        player = get_player()
        current_idx = player.current_index

        if not queue:
            self._empty_lbl.show()
            return
        self._empty_lbl.hide()

        for i, song in enumerate(queue):
            if i == current_idx:
                continue                                
            item = QueueSongItem(song, i, is_current=False)
            item.play_now.connect(self._play_at_index)
            item.remove_from_queue.connect(self._remove_at_index)
            self._queue_layout.insertWidget(self._queue_layout.count() - 1, item)

    def _on_track_changed(self, song: Dict):
        self._now_playing_frame.setVisible(True)

        title = song.get("title", "")
        artists = song.get("artists") or []
        if artists and isinstance(artists[0], dict):
            artist = ", ".join(a.get("name", "") for a in artists)
        else:
            artist = song.get("artist", "")

        thumbnails = song.get("thumbnails") or []
        if thumbnails:
            best = max(thumbnails, key=lambda t: t.get("width", 0) if isinstance(t, dict) else 0)
            url = best.get("url", "") if isinstance(best, dict) else ""
            if url:
                self._now_thumb.set_url(url)

        self._now_title.setText(title[:35])
        self._now_artist.setText(artist[:35])

    def _play_at_index(self, index: int):
        player = get_player()
        player._current_index = index
        player._play_current()

    def _remove_at_index(self, index: int):
        get_player().remove_from_queue(index)

    def _clear_queue(self):
        get_player().clear_queue()
