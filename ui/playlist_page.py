from typing import List, Dict, Optional
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QScrollArea, QFrame, QSizePolicy,
                              QSplitter)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QColor, QPainter, QPainterPath

from core.ytmusic_client import get_client
from core import database
from core.player import get_player
from ui.widgets.song_card import SongRow, format_duration
from ui.widgets.thumbnail import ThumbnailWidget

class PlaylistHeader(QFrame):
    play_all_clicked     = pyqtSignal()
    shuffle_play_clicked = pyqtSignal()
    download_all_clicked = pyqtSignal()
    back_clicked         = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(240)
        self.setStyleSheet("background: transparent; border: none;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)

        self._thumb = ThumbnailWidget(size=200, radius=12)
        layout.addWidget(self._thumb)

        info = QVBoxLayout()
        info.setSpacing(8)
        info.setContentsMargins(0, 0, 0, 0)

        back_btn = QPushButton("← Geri")
        back_btn.setObjectName("btn_icon")
        back_btn.setStyleSheet("QPushButton { color: #AFAFAF; background: transparent; border: none; text-align: left; padding: 4px 0; }")
        back_btn.clicked.connect(self.back_clicked)
        info.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self._type_lbl = QLabel("PLAYLIST")
        self._type_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._type_lbl.setStyleSheet("color: #777777; letter-spacing: 2px;")
        info.addWidget(self._type_lbl)

        self._title_lbl = QLabel("Playlist Adı")
        self._title_lbl.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet("color: #FFFFFF;")
        self._title_lbl.setWordWrap(True)
        info.addWidget(self._title_lbl)

        self._meta_lbl = QLabel("")
        self._meta_lbl.setObjectName("lbl_subtitle")
        info.addWidget(self._meta_lbl)

        info.addSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._play_btn = QPushButton("▶  Tümünü Çal")
        self._play_btn.setObjectName("btn_primary")
        self._play_btn.setFixedHeight(40)
        self._play_btn.clicked.connect(self.play_all_clicked)
        btn_row.addWidget(self._play_btn)

        self._shuffle_btn = QPushButton("⇄  Karıştır")
        self._shuffle_btn.setObjectName("btn_secondary")
        self._shuffle_btn.setFixedHeight(40)
        self._shuffle_btn.clicked.connect(self.shuffle_play_clicked)
        btn_row.addWidget(self._shuffle_btn)

        self._download_btn = QPushButton("⬇  Tümünü İndir")
        self._download_btn.setObjectName("btn_secondary")
        self._download_btn.setFixedHeight(40)
        self._download_btn.clicked.connect(self.download_all_clicked)
        btn_row.addWidget(self._download_btn)

        btn_row.addStretch()
        info.addLayout(btn_row)
        info.addStretch()

        layout.addLayout(info, stretch=1)

    def set_data(self, title: str, author: str, count: int, duration: int,
                 thumbnail_url: str, playlist_type: str = "PLAYLIST"):
        self._title_lbl.setText(title)
        self._type_lbl.setText(playlist_type)
        meta = []
        if author:
            meta.append(author)
        if count:
            meta.append(f"{count} şarkı")
        if duration:
            meta.append(format_duration(duration))
        self._meta_lbl.setText("  •  ".join(meta))
        if thumbnail_url:
            self._thumb.set_url(thumbnail_url)

class PlaylistPage(QWidget):
    back_requested          = pyqtSignal()
    song_play_requested     = pyqtSignal(dict, list)                    
    song_download_requested = pyqtSignal(dict)
    add_to_queue_signal     = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._songs: List[Dict] = []
        self._playlist_data: Dict = {}
        self._current_song_index = -1
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 0)
        outer.setSpacing(0)

        self._header = PlaylistHeader()
        self._header.back_clicked.connect(self.back_requested)
        self._header.play_all_clicked.connect(self._play_all)
        self._header.shuffle_play_clicked.connect(self._shuffle_play)
        self._header.download_all_clicked.connect(self._download_all)
        outer.addWidget(self._header)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #1A1A1A;")
        outer.addWidget(sep)

        outer.addSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._songs_container = QWidget()
        self._songs_container.setStyleSheet("background: transparent;")
        self._songs_layout = QVBoxLayout(self._songs_container)
        self._songs_layout.setContentsMargins(0, 0, 0, 100)
        self._songs_layout.setSpacing(2)

        scroll.setWidget(self._songs_container)
        outer.addWidget(scroll, stretch=1)

        self._loading_lbl = QLabel("🎵 Yükleniyor...")
        self._loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_lbl.setStyleSheet("color: #555; font-size: 14px; padding: 40px;")
        outer.addWidget(self._loading_lbl)

    def load_yt_playlist(self, playlist_data: Dict):
        self._playlist_data = playlist_data
        self._songs = []

        title = playlist_data.get("title", "")
        author = playlist_data.get("author") or {}
        if isinstance(author, dict):
            author_name = author.get("name", "")
        else:
            author_name = str(author)

        thumbs = playlist_data.get("thumbnails") or []
        thumb_url = self._best_thumb(thumbs)

        self._header.set_data(title, author_name, 0, 0, thumb_url)
        self._loading_lbl.setVisible(True)
        self._clear_songs()

        playlist_id = playlist_data.get("playlistId") or playlist_data.get("browseId", "")
        if playlist_id:
            client = get_client()
            client.playlist_loaded.connect(self._on_playlist_loaded)
            client.load_playlist(playlist_id)

    def load_local_playlist(self, playlist_id: int):
        pl = database.get_playlist_by_id(playlist_id)
        if not pl:
            return
        songs = database.get_playlist_songs(playlist_id)
        self._playlist_data = pl
        self._songs = []

        total_dur = sum(s.get("duration", 0) for s in songs)
        self._header.set_data(
            pl["name"],
            "Yerel Koleksiyon",
            len(songs),
            total_dur,
            pl.get("cover_path", ""),
            "YEREL PLAYLİST"
        )
        self._loading_lbl.setVisible(False)
        self._show_songs_local(songs)

    def _on_playlist_loaded(self, data: Dict):
        self._loading_lbl.setVisible(False)
        client = get_client()
        try:
            client.playlist_loaded.disconnect(self._on_playlist_loaded)
        except Exception:
            pass

        tracks = data.get("tracks") or data.get("songs", [])
        title  = data.get("title", self._playlist_data.get("title", ""))
        author = data.get("author") or {}
        if isinstance(author, dict):
            author_name = author.get("name", "")
        else:
            author_name = str(author)

        thumbs = data.get("thumbnails") or self._playlist_data.get("thumbnails") or []
        thumb_url = self._best_thumb(thumbs)

        total_dur = 0
        for t in tracks:
            dur = t.get("duration_seconds", 0) or 0
            total_dur += dur

        self._header.set_data(title, author_name, len(tracks), total_dur, thumb_url)
        self._playlist_data.update(data)
        self._show_songs_yt(tracks)

    def _show_songs_yt(self, songs: List[Dict]):
        self._clear_songs()
        self._songs = songs

        for i, song in enumerate(songs):
            row = SongRow(song, index=i, show_thumbnail=True, show_index=True)
            row.play_requested.connect(lambda s, idx=i: self._play_from_index(idx))
            row.download_requested.connect(self.song_download_requested)
            row.add_to_queue_signal.connect(self.add_to_queue_signal)
            self._songs_layout.addWidget(row)

        self._songs_layout.addStretch()

    def _show_songs_local(self, songs: List[Dict]):
        self._clear_songs()
        self._songs = []

        for i, song in enumerate(songs):
                                                 
            song_data = {
                "videoId": song.get("video_id", ""),
                "title":   song.get("title", ""),
                "artists": [{"name": song.get("artist", "")}],
                "album":   {"name": song.get("album", "")},
                "duration_seconds": song.get("duration", 0),
                "thumbnails": [{"url": "file:///" + song.get("thumbnail_path", "").replace("\\", "/"), "width": 120}],
                "file_path": song.get("file_path", ""),
                "id": song.get("id"),
            }
            self._songs.append(song_data)
            row = SongRow(song_data, index=i, show_thumbnail=True, show_index=True, is_local=True)
            row.play_requested.connect(lambda s, idx=i: self._play_from_index(idx))
            row.download_requested.connect(self.song_download_requested)
            row.add_to_queue_signal.connect(self.add_to_queue_signal)
            row.remove_signal.connect(self._remove_song)
            self._songs_layout.addWidget(row)

        self._songs_layout.addStretch()

    def _play_from_index(self, index: int):
        if 0 <= index < len(self._songs):
            self.song_play_requested.emit(self._songs[index], self._songs)

    def _play_all(self):
        if self._songs:
            self._play_from_index(0)

    def _shuffle_play(self):
        if self._songs:
            player = get_player()
            import random
            shuffled = list(self._songs)
            random.shuffle(shuffled)
            player.set_queue(shuffled, 0)

    def _download_all(self):
        if self._songs:
            from ui.download_dialog import DownloadDialog
            dlg = DownloadDialog(self._songs, is_playlist=True, parent=self)
            dlg.exec()

    def _remove_song(self, song_data: Dict):
        pl_id = self._playlist_data.get("id")
        song_id = song_data.get("id")
        if pl_id and song_id:
            database.remove_song_from_playlist(pl_id, song_id)
            self.load_local_playlist(pl_id)

    def _clear_songs(self):
        self._songs = []
        while self._songs_layout.count():
            item = self._songs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _best_thumb(self, thumbnails) -> str:
        if not thumbnails:
            return ""
        best = max(thumbnails, key=lambda t: t.get("width", 0) if isinstance(t, dict) else 0)
        return best.get("url", "") if isinstance(best, dict) else ""
