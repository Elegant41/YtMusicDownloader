import os
from typing import Optional, List, Dict
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                              QLabel, QPushButton, QFrame, QStackedWidget,
                              QSizePolicy, QApplication, QSplitter, QScrollArea,
                              QMessageBox, QMenuBar)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QPropertyAnimation, QRect
from PyQt6.QtGui import QFont, QPixmap, QIcon, QColor, QAction

from core.ytmusic_client import get_client
from core.player import get_player
from core import database
from ui.home_page import HomePage
from ui.search_page import SearchPage
from ui.library_page import LibraryPage
from ui.playlist_page import PlaylistPage
from ui.downloads_page import DownloadsPage
from ui.player_bar import PlayerBar
from ui.queue_sidebar import QueueSidebar

PAGE_HOME      = 0
PAGE_SEARCH    = 1
PAGE_LIBRARY   = 2
PAGE_PLAYLIST  = 3
PAGE_DOWNLOADS = 4

class SidebarButton(QPushButton):
    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self._icon_char = icon
        self._label     = label
        self.setObjectName("btn_sidebar")
        self.setText(f"  {icon}   {label}")
        self.setFixedHeight(44)
        self.setCheckable(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        font = QFont("Segoe UI", 13)
        self.setFont(font)

    def set_active(self, active: bool):
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)

class Sidebar(QFrame):
    page_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(4)

        logo_lbl = QLabel("▶ YT Music")
        logo_lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        logo_lbl.setStyleSheet("color: #FF0033; padding: 8px 4px 16px 4px;")
        layout.addWidget(logo_lbl)

        self._buttons: List[SidebarButton] = []
        nav_items = [
            ("🏠", "Ana Sayfa",    PAGE_HOME),
            ("🔍", "Ara",          PAGE_SEARCH),
            ("📚", "Kütüphane",    PAGE_LIBRARY),
            ("⬇",  "İndirilenler", PAGE_DOWNLOADS),
        ]

        for icon, label, page_idx in nav_items:
            btn = SidebarButton(icon, label)
            btn.clicked.connect(lambda checked, p=page_idx: self._on_btn_clicked(p))
            layout.addWidget(btn)
            self._buttons.append(btn)

        layout.addStretch()

        self._user_frame = QFrame()
        self._user_frame.setStyleSheet("background: #1A1A1A; border-radius: 10px;")
        user_layout = QVBoxLayout(self._user_frame)
        user_layout.setContentsMargins(12, 10, 12, 10)
        user_layout.setSpacing(4)

        self._user_name_lbl = QLabel("Hesap")
        self._user_name_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self._user_name_lbl.setStyleSheet("color: #EFEFEF;")
        user_layout.addWidget(self._user_name_lbl)

        self._user_email_lbl = QLabel("")
        self._user_email_lbl.setFont(QFont("Segoe UI", 10))
        self._user_email_lbl.setStyleSheet("color: #666;")
        user_layout.addWidget(self._user_email_lbl)

        logout_btn = QPushButton("🚪  Çıkış")
        logout_btn.setObjectName("btn_secondary")
        logout_btn.setFixedHeight(28)
        logout_btn.clicked.connect(self._logout)
        user_layout.addWidget(logout_btn)

        layout.addWidget(self._user_frame)

        self._select_page(PAGE_HOME)

    def _on_btn_clicked(self, page_idx: int):
        self._select_page(page_idx)
        self.page_changed.emit(page_idx)

    def _select_page(self, page_idx: int):
        btn_map = {PAGE_HOME: 0, PAGE_SEARCH: 1, PAGE_LIBRARY: 2, PAGE_DOWNLOADS: 3}
        for i, btn in enumerate(self._buttons):
            btn.set_active(i == btn_map.get(page_idx, -1))

    def set_user_info(self, name: str, email: str = ""):
        self._user_name_lbl.setText(name or "Kullanıcı")
        self._user_email_lbl.setText(email)

    def navigate_to(self, page_idx: int):
        self._select_page(page_idx)

    def _logout(self):
        reply = QMessageBox.question(
            self, "Çıkış Yap",
            "YouTube Music hesabından çıkmak istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            get_client().logout()
            QApplication.quit()

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("YT Music Desktop Player")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)

        central = QWidget()
        self.setCentralWidget(central)

        self._main_layout = QVBoxLayout(central)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        content_area = QWidget()
        self._content_layout = QHBoxLayout(content_area)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)

        self._sidebar = Sidebar()
        self._sidebar.page_changed.connect(self._navigate_to)
        self._content_layout.addWidget(self._sidebar)

        self._pages = QStackedWidget()
        self._pages.setStyleSheet("background: #0F0F0F;")
        self._content_layout.addWidget(self._pages, stretch=1)

        self._queue_sidebar = QueueSidebar()
        self._queue_sidebar.setVisible(False)
        self._content_layout.addWidget(self._queue_sidebar)

        self._main_layout.addWidget(content_area, stretch=1)

        self._player_bar = PlayerBar()
        self._player_bar.queue_toggled.connect(self._toggle_queue)
        self._main_layout.addWidget(self._player_bar)

        self._home_page     = HomePage()
        self._search_page   = SearchPage()
        self._library_page  = LibraryPage()
        self._playlist_page = PlaylistPage()
        self._downloads_page = DownloadsPage()

        self._pages.addWidget(self._home_page)          
        self._pages.addWidget(self._search_page)        
        self._pages.addWidget(self._library_page)       
        self._pages.addWidget(self._playlist_page)      
        self._pages.addWidget(self._downloads_page)     

        self._connect_signals()
        self._load_user_info()

        QTimer.singleShot(300, self._home_page.load_data)
        QTimer.singleShot(600, self._library_page.load_data)

    def _connect_signals(self):
              
        self._home_page.playlist_open_requested.connect(self._open_yt_playlist)
        self._home_page.song_play_requested.connect(self._play_song)
        self._home_page.song_download_requested.connect(self._download_song)

        self._search_page.playlist_open_requested.connect(self._open_yt_playlist)
        self._search_page.song_play_requested.connect(self._play_song)
        self._search_page.song_download_requested.connect(self._download_song)
        self._search_page.add_to_queue_signal.connect(self._add_to_queue)

        self._library_page.playlist_open_requested.connect(self._open_yt_playlist)
        self._library_page.song_play_requested.connect(self._play_song)
        self._library_page.song_download_requested.connect(self._download_song)

        self._playlist_page.back_requested.connect(self._go_back)
        self._playlist_page.song_play_requested.connect(self._play_song_with_queue)
        self._playlist_page.song_download_requested.connect(self._download_song)
        self._playlist_page.add_to_queue_signal.connect(self._add_to_queue)

        self._downloads_page.song_play_requested.connect(self._play_song_with_queue)
        self._downloads_page.playlist_open_requested.connect(self._open_local_playlist)

        get_player().error_occurred.connect(self._on_player_error)

    def _navigate_to(self, page_idx: int):
        self._sidebar.navigate_to(page_idx)
        self._pages.setCurrentIndex(page_idx)

        if page_idx == PAGE_SEARCH:
            self._search_page.focus_search()
        elif page_idx == PAGE_DOWNLOADS:
            self._downloads_page.refresh()

    def _open_yt_playlist(self, playlist_data: Dict):
        self._playlist_page.load_yt_playlist(playlist_data)
        self._pages.setCurrentIndex(PAGE_PLAYLIST)

    def _open_local_playlist(self, playlist_id: int):
        self._playlist_page.load_local_playlist(playlist_id)
        self._pages.setCurrentIndex(PAGE_PLAYLIST)

    def _go_back(self):
        self._pages.setCurrentIndex(max(0, self._pages.currentIndex() - 1))

    def _play_song(self, song: Dict):
        file_path = song.get("file_path", "")
        if file_path and os.path.exists(file_path):
            player = get_player()
            player.set_queue([song], 0)
        else:
                                                  
            self._download_song(song)

    def _play_song_with_queue(self, song: Dict, queue: List[Dict]):
                                          
        local_queue = []
        for s in queue:
            file_path = s.get("file_path", "")
            if file_path and os.path.exists(file_path):
                local_queue.append(s)

        if local_queue:
            start_idx = 0
            for i, s in enumerate(local_queue):
                if s.get("videoId") == song.get("videoId") or s.get("video_id") == song.get("video_id"):
                    start_idx = i
                    break
            get_player().set_queue(local_queue, start_idx)
        else:
            self._download_song(song)

    def _add_to_queue(self, song: Dict):
        file_path = song.get("file_path", "")
        if file_path and os.path.exists(file_path):
            get_player().add_to_queue(song)
        else:
            QMessageBox.information(self, "Bilgi",
                "Bu şarkı henüz indirilmemiş. Önce indirin, ardından çalabilirsiniz.")

    def _download_song(self, song: Dict):
        from ui.download_dialog import DownloadDialog
        dlg = DownloadDialog(song, is_playlist=False, parent=self)
        dlg.exec()
                                  
        self._navigate_to(PAGE_DOWNLOADS)

    def _toggle_queue(self):
        self._queue_sidebar.setVisible(not self._queue_sidebar.isVisible())

    def _load_user_info(self):
        client = get_client()
        if client.is_authenticated():
            def _fetch():
                info = client.get_user_info()
                name  = info.get("accountName", "Kullanıcı")
                email = info.get("channelHandle", "")
                self._sidebar.set_user_info(name, email)

            QTimer.singleShot(500, _fetch)

    def _on_player_error(self, error: str):
        pass                                  

    def show_search(self):
        self._navigate_to(PAGE_SEARCH)

    def show_downloads(self):
        self._navigate_to(PAGE_DOWNLOADS)
