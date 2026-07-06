from typing import List, Dict, Optional
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QScrollArea, QFrame, QPushButton, QTabBar,
                              QTabWidget, QGridLayout, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from core.ytmusic_client import get_client
from ui.widgets.playlist_card import PlaylistCard
from ui.widgets.song_card import SongRow

class PlaylistGrid(QWidget):
    playlist_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)

        self._grid_container = QWidget()
        self._grid_container.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._grid_container)
        self._grid.setSpacing(16)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._outer.addWidget(self._grid_container)
        self._outer.addStretch()

    def show_playlists(self, playlists: List[Dict], cols: int = 5):
                 
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, pl in enumerate(playlists):
            card = PlaylistCard(pl, card_width=160)
            card.clicked.connect(self.playlist_clicked)
            self._grid.addWidget(card, i // cols, i % cols)

class LibraryPage(QWidget):
    playlist_open_requested = pyqtSignal(dict)
    song_play_requested     = pyqtSignal(dict)
    song_download_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._liked_songs: List[Dict] = []
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 0)
        outer.setSpacing(16)

        header_row = QHBoxLayout()
        title = QLabel("Kütüphane")
        title.setObjectName("lbl_title")
        header_row.addWidget(title)
        header_row.addStretch()

        refresh_btn = QPushButton("↻  Yenile")
        refresh_btn.setObjectName("btn_secondary")
        refresh_btn.setFixedHeight(36)
        refresh_btn.clicked.connect(self.load_data)
        header_row.addWidget(refresh_btn)
        outer.addLayout(header_row)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabBar::tab { padding: 10px 20px; font-size: 13px; font-weight: 600; color: #777; border-bottom: 2px solid transparent; background: transparent; }
            QTabBar::tab:hover { color: #EEE; }
            QTabBar::tab:selected { color: #FF0033; border-bottom: 2px solid #FF0033; }
            QTabWidget::pane { border: none; background: transparent; }
        """)

        self._playlist_tab = self._make_scroll_tab()
        self._playlist_grid = PlaylistGrid()
        self._playlist_grid.playlist_clicked.connect(self.playlist_open_requested)
        self._playlist_tab.widget().layout().addWidget(self._playlist_grid)
        self._playlist_tab.widget().layout().addStretch()
        self._tabs.addTab(self._playlist_tab, "🎵  Playlist'ler")

        self._liked_tab = self._make_scroll_tab()
        self._liked_layout = self._liked_tab.widget().layout()
        self._liked_layout.addStretch()
        self._tabs.addTab(self._liked_tab, "❤  Beğenilenler")

        self._albums_tab = self._make_scroll_tab()
        self._albums_grid = PlaylistGrid()
        self._albums_grid.playlist_clicked.connect(self.playlist_open_requested)
        self._albums_tab.widget().layout().addWidget(self._albums_grid)
        self._albums_tab.widget().layout().addStretch()
        self._tabs.addTab(self._albums_tab, "💿  Albümler")

        outer.addWidget(self._tabs, stretch=1)

        self._loading_lbl = QLabel("🎵 Kütüphane yükleniyor...")
        self._loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_lbl.setStyleSheet("color: #555; font-size: 14px; padding: 40px;")
        self._loading_lbl.setVisible(False)
        outer.addWidget(self._loading_lbl)

    def _make_scroll_tab(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 16, 0, 100)
        layout.setSpacing(8)

        scroll.setWidget(container)
        return scroll

    def load_data(self):
        client = get_client()
        if not client.is_authenticated():
            self._show_not_logged_in()
            return

        self._loading_lbl.setVisible(True)
        client.library_loaded.connect(self._on_library_loaded)
        client.load_library()

    def _on_library_loaded(self, data: Dict):
        self._loading_lbl.setVisible(False)

        playlists = data.get("playlists", [])
        liked = data.get("liked", {})

        all_playlists = []
        for pl in playlists:
            all_playlists.append(pl)
        self._playlist_grid.show_playlists(all_playlists)

        if isinstance(liked, dict):
            liked_tracks = liked.get("tracks", [])
        else:
            liked_tracks = []

        self._liked_songs = liked_tracks
        self._show_liked_songs(liked_tracks)

        albums = [pl for pl in playlists if pl.get("type") == "album"]
        self._albums_grid.show_playlists(albums)

    def _show_liked_songs(self, songs: List[Dict]):
                 
        layout = self._liked_layout
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not songs:
            lbl = QLabel("Beğenilen şarkı bulunamadı.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #555; padding: 40px;")
            layout.insertWidget(0, lbl)
            return

        header = QHBoxLayout()
        count_lbl = QLabel(f"{len(songs)} şarkı")
        count_lbl.setObjectName("lbl_subtitle")
        header.addWidget(count_lbl)
        header.addStretch()

        play_all_btn = QPushButton("▶  Tümünü Çal")
        play_all_btn.setObjectName("btn_primary")
        play_all_btn.setFixedHeight(36)
        play_all_btn.clicked.connect(lambda: self.song_play_requested.emit(songs[0]) if songs else None)
        header.addWidget(play_all_btn)

        dl_all_btn = QPushButton("⬇  Tümünü İndir")
        dl_all_btn.setObjectName("btn_secondary")
        dl_all_btn.setFixedHeight(36)
        dl_all_btn.clicked.connect(self._download_all_liked)
        header.addWidget(dl_all_btn)

        header_widget = QWidget()
        header_widget.setLayout(header)
        layout.insertWidget(0, header_widget)

        for i, song in enumerate(songs[:100]):
            row = SongRow(song, index=i, show_thumbnail=True, show_index=True)
            row.play_requested.connect(self.song_play_requested)
            row.download_requested.connect(self.song_download_requested)
            layout.insertWidget(i + 1, row)

    def _download_all_liked(self):
        if self._liked_songs:
            from ui.download_dialog import DownloadDialog
            dlg = DownloadDialog(self._liked_songs, is_playlist=True, parent=self)
            dlg.exec()

    def _show_not_logged_in(self):
        pass

    def refresh(self):
        self.load_data()
