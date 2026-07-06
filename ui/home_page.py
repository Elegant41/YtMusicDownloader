from typing import List, Dict, Optional
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QScrollArea, QFrame, QPushButton, QSizePolicy,
                              QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from core.ytmusic_client import get_client
from core import database
from ui.widgets.playlist_card import PlaylistCard
from ui.widgets.song_card import SongRow

class HorizontalScrollSection(QFrame):
    card_clicked = pyqtSignal(dict)

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet("QFrame#card { border: none; background: transparent; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 16)
        outer.setSpacing(12)

        self._title_lbl = QLabel(title)
        self._title_lbl.setObjectName("lbl_section")
        outer.addWidget(self._title_lbl)

        self._scroll = QScrollArea()
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFixedHeight(220)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._row_layout = QHBoxLayout(self._container)
        self._row_layout.setContentsMargins(0, 0, 0, 0)
        self._row_layout.setSpacing(12)
        self._row_layout.addStretch()

        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll)

    def add_cards(self, items: List[Dict]):
                                 
        while self._row_layout.count() > 1:
            item = self._row_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for item in items[:12]:
            card = PlaylistCard(item, card_width=160)
            card.clicked.connect(self.card_clicked.emit)
            self._row_layout.insertWidget(self._row_layout.count() - 1, card)

class QuickPicksSection(QFrame):
    song_play_requested = pyqtSignal(dict)
    song_download_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(12)

        title_lbl = QLabel("Hızlı Seçimler")
        title_lbl.setObjectName("lbl_section")
        layout.addWidget(title_lbl)

        self._grid_widget = QWidget()
        self._grid_widget.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setSpacing(4)
        self._grid.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._grid_widget)

    def add_songs(self, songs: List[Dict]):
                 
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, song in enumerate(songs[:12]):
            row_widget = SongRow(song, index=i, show_thumbnail=True, show_index=False)
            row_widget.play_requested.connect(self.song_play_requested.emit)
            row_widget.download_requested.connect(self.song_download_requested.emit)
            col = i % 2
            row = i // 2
            self._grid.addWidget(row_widget, row, col)

class LoadingOverlay(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("Yükleniyor...")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("color: #777777; font-size: 14px;")

class HomePage(QWidget):
    playlist_open_requested = pyqtSignal(dict)
    song_play_requested     = pyqtSignal(dict)
    song_download_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
                         
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: #0F0F0F; }")

        content = QWidget()
        content.setStyleSheet("background: #0F0F0F;")
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(32, 32, 32, 100)
        self._content_layout.setSpacing(8)

        welcome = QLabel("Hoş Geldiniz 👋")
        welcome.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        welcome.setStyleSheet("color: #FFFFFF;")
        self._content_layout.addWidget(welcome)

        self._subtitle = QLabel("Müziğinize kaldığınız yerden devam edin")
        self._subtitle.setObjectName("lbl_subtitle")
        self._content_layout.addWidget(self._subtitle)

        self._content_layout.addSpacing(16)

        self._quick_picks = QuickPicksSection()
        self._quick_picks.song_play_requested.connect(self.song_play_requested)
        self._quick_picks.song_download_requested.connect(self.song_download_requested)
        self._content_layout.addWidget(self._quick_picks)

        self._recent_section = HorizontalScrollSection("Son Çalinanlar")
        self._recent_section.card_clicked.connect(self.playlist_open_requested)
        self._content_layout.addWidget(self._recent_section)

        self._yt_sections: List[HorizontalScrollSection] = []

        self._loading_lbl = LoadingOverlay()
        self._content_layout.addWidget(self._loading_lbl)

        self._content_layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

        client = get_client()
        client.home_loaded.connect(self._on_home_loaded)
        client.error_occurred.connect(self._on_error)

    def load_data(self):
        self._loading_lbl.setVisible(True)
        self._loading_lbl.setText("🎵 YT Music'ten yükleniyor...")

        self._load_local_recent()

        client = get_client()
        if client.is_authenticated():
            client.load_home()
        else:
            self._loading_lbl.setText("Giriş yapıldıktan sonra YT Music içeriği yüklenir.")

    def _load_local_recent(self):
        recent = database.get_recently_played(limit=20)
        if recent:
                                                      
            songs_data = []
            for s in recent:
                thumb = s.get("thumbnail_path", "")
                songs_data.append({
                    "videoId": s.get("video_id", ""),
                    "title": s.get("title", ""),
                    "artists": [{"name": s.get("artist", "")}],
                    "thumbnails": [{"url": "file:///" + thumb.replace("\\", "/"), "width": 120}] if thumb else [],
                    "duration_seconds": s.get("duration", 0),
                    "file_path": s.get("file_path", ""),
                    "id": s.get("id"),
                    "video_id": s.get("video_id", ""),
                })
            self._quick_picks.add_songs(songs_data)

    def _on_home_loaded(self, sections: List[Dict]):
        self._loading_lbl.setVisible(False)

        for sec in self._yt_sections:
            self._content_layout.removeWidget(sec)
            sec.deleteLater()
        self._yt_sections.clear()

        quick_picks_added = False
        insert_pos = self._content_layout.indexOf(self._loading_lbl)

        for section in sections:
            title  = section.get("title", "")
            items  = section.get("contents", [])

            if not items:
                continue

            if not quick_picks_added and title.lower() in ("quick picks", "hızlı seçimler"):
                songs = [i.get("content", i) for i in items if isinstance(i, dict)]
                self._quick_picks.add_songs(songs[:12])
                quick_picks_added = True
                continue

            playlist_items = []
            for item in items:
                content = item.get("content", item) if isinstance(item, dict) else {}
                if isinstance(content, dict):
                    playlist_items.append(content)

            if not playlist_items:
                continue

            sec = HorizontalScrollSection(title)
            sec.add_cards(playlist_items)
            sec.card_clicked.connect(self.playlist_open_requested)

            self._content_layout.insertWidget(insert_pos, sec)
            self._yt_sections.append(sec)
            insert_pos += 1

        if not quick_picks_added:
            self._load_local_recent()

    def _on_error(self, error: str):
        self._loading_lbl.setText(f"⚠ Yüklenemedi: {error[:80]}")
        self._loading_lbl.setVisible(True)

    def refresh(self):
        self.load_data()
