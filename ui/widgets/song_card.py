from typing import Dict, Optional
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QLabel,
                              QPushButton, QMenu, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QAction, QColor

from ui.widgets.thumbnail import ThumbnailWidget
from core import database

def format_duration(seconds: int) -> str:
    if not seconds:
        return "--:--"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

class SongRow(QFrame):
    play_requested       = pyqtSignal(dict)              
    download_requested   = pyqtSignal(dict)              
    add_to_queue_signal  = pyqtSignal(dict)
    add_to_playlist_signal = pyqtSignal(dict)
    remove_signal        = pyqtSignal(dict)

    def __init__(self, song_data: Dict, index: int = 0,
                 show_thumbnail: bool = True,
                 show_index: bool = True,
                 is_local: bool = False,
                 parent=None):
        super().__init__(parent)
        self.song_data  = song_data
        self.index      = index
        self.is_local   = is_local
        self._is_playing = False

        self.setObjectName("song_row")
        self.setFixedHeight(60)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._build_ui(show_thumbnail, show_index)
        self.mouseDoubleClickEvent = lambda e: self.play_requested.emit(self.song_data)

    def _build_ui(self, show_thumbnail: bool, show_index: bool):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        if show_index:
            self._idx_lbl = QLabel(str(self.index + 1))
            self._idx_lbl.setObjectName("lbl_small")
            self._idx_lbl.setFixedWidth(24)
            self._idx_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self._idx_lbl)

        if show_thumbnail:
            self._thumb = ThumbnailWidget(size=44, radius=6)
            thumbnails = self.song_data.get("thumbnails") or []
            url = self._best_thumb(thumbnails)
            if url:
                self._thumb.set_url(url)
            layout.addWidget(self._thumb)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        text_box.setContentsMargins(0, 0, 0, 0)

        title = self.song_data.get("title", "Unknown")
        self._title_lbl = QLabel(title)
        self._title_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
        self._title_lbl.setStyleSheet("color: #EFEFEF;")
        self._title_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        artists = self.song_data.get("artists") or []
        if artists and isinstance(artists[0], dict):
            artist_str = ", ".join(a.get("name", "") for a in artists)
        else:
            artist_str = self.song_data.get("artist", "")

        album_data = self.song_data.get("album") or {}
        album_name = album_data.get("name", "") if isinstance(album_data, dict) else str(album_data)
        sub = artist_str
        if album_name:
            sub += f"  •  {album_name}"

        self._sub_lbl = QLabel(sub)
        self._sub_lbl.setFont(QFont("Segoe UI", 11))
        self._sub_lbl.setStyleSheet("color: #777777;")

        text_box.addWidget(self._title_lbl)
        text_box.addWidget(self._sub_lbl)
        layout.addLayout(text_box, stretch=1)

        video_id = self.song_data.get("videoId") or self.song_data.get("video_id", "")
        if database.song_exists(video_id):
            self._downloaded_lbl = QLabel("✓")
            self._downloaded_lbl.setStyleSheet("color: #FF0033; font-weight: 700;")
            self._downloaded_lbl.setFixedWidth(20)
            layout.addWidget(self._downloaded_lbl)

        dur = self.song_data.get("duration") or self.song_data.get("duration_seconds", 0)
        if isinstance(dur, str):
            dur_text = dur
        else:
            dur_text = format_duration(dur)

        self._dur_lbl = QLabel(dur_text)
        self._dur_lbl.setObjectName("lbl_small")
        self._dur_lbl.setFixedWidth(44)
        self._dur_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._dur_lbl)

        self._menu_btn = QPushButton("⋯")
        self._menu_btn.setObjectName("btn_icon")
        self._menu_btn.setFixedSize(32, 32)
        self._menu_btn.clicked.connect(self._show_context_menu)
        self._menu_btn.setVisible(False)
        layout.addWidget(self._menu_btn)

    def _best_thumb(self, thumbnails) -> str:
        if not thumbnails:
            return ""
        best = max(thumbnails, key=lambda t: t.get("width", 0) if isinstance(t, dict) else 0)
        return best.get("url", "") if isinstance(best, dict) else ""

    def _show_context_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #1A1A1A; border: 1px solid #333; border-radius: 8px; padding: 4px 0; }
            QMenu::item { padding: 8px 20px; color: #EFEFEF; }
            QMenu::item:selected { background: #2A2A2A; }
        """)

        act_play = QAction("▶  Çal", self)
        act_play.triggered.connect(lambda: self.play_requested.emit(self.song_data))

        act_queue = QAction("≡  Sıraya Ekle", self)
        act_queue.triggered.connect(lambda: self.add_to_queue_signal.emit(self.song_data))

        act_download = QAction("⬇  İndir", self)
        act_download.triggered.connect(lambda: self.download_requested.emit(self.song_data))

        act_playlist = QAction("＋  Playlist'e Ekle", self)
        act_playlist.triggered.connect(lambda: self.add_to_playlist_signal.emit(self.song_data))

        menu.addAction(act_play)
        menu.addAction(act_queue)
        menu.addSeparator()
        menu.addAction(act_download)
        menu.addAction(act_playlist)

        if self.is_local:
            act_remove = QAction("🗑  Kaldır", self)
            act_remove.triggered.connect(lambda: self.remove_signal.emit(self.song_data))
            menu.addSeparator()
            menu.addAction(act_remove)

        menu.exec(self._menu_btn.mapToGlobal(self._menu_btn.rect().bottomLeft()))

    def set_playing(self, playing: bool):
        self._is_playing = playing
        self.setProperty("playing", "true" if playing else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        if hasattr(self, "_idx_lbl"):
            if playing:
                self._idx_lbl.setText("▶")
                self._idx_lbl.setStyleSheet("color: #FF0033; font-weight: bold;")
            else:
                self._idx_lbl.setText(str(self.index + 1))
                self._idx_lbl.setStyleSheet("")

    def enterEvent(self, event):
        self._menu_btn.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._menu_btn.setVisible(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu()
        super().mousePressEvent(event)
