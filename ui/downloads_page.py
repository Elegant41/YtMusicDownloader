from typing import List, Dict, Optional
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QScrollArea, QFrame, QTabWidget,
                              QSizePolicy, QProgressBar, QMenu, QInputDialog,
                              QMessageBox, QGridLayout, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QAction

from core import database
from core.downloader import get_manager, DownloadTask, DownloadStatus
from core.player import get_player
from ui.widgets.song_card import SongRow, format_duration
from ui.widgets.playlist_card import LocalPlaylistCard
from ui.widgets.progress_ring import ProgressRing
from ui.widgets.thumbnail import ThumbnailWidget

class DownloadQueueItem(QFrame):
    cancel_clicked = pyqtSignal(str)            

    def __init__(self, task: DownloadTask, parent=None):
        super().__init__(parent)
        self.task     = task
        self.video_id = task.video_id
        self.setObjectName("download_item")
        self.setFixedHeight(72)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        self._thumb = ThumbnailWidget(size=52, radius=6)
        if task.thumbnail_url:
            self._thumb.set_url(task.thumbnail_url)
        layout.addWidget(self._thumb)

        info = QVBoxLayout()
        info.setSpacing(2)

        self._title_lbl = QLabel(task.title[:50] + ("..." if len(task.title) > 50 else ""))
        self._title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        self._title_lbl.setStyleSheet("color: #EFEFEF;")

        self._status_lbl = QLabel("Bekleniyor...")
        self._status_lbl.setFont(QFont("Segoe UI", 10))
        self._status_lbl.setStyleSheet("color: #777777;")

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setTextVisible(False)

        info.addWidget(self._title_lbl)
        info.addWidget(self._status_lbl)
        info.addWidget(self._progress_bar)
        layout.addLayout(info, stretch=1)

        self._ring = ProgressRing(size=44)
        layout.addWidget(self._ring)

        cancel_btn = QPushButton("✕")
        cancel_btn.setObjectName("btn_icon")
        cancel_btn.setFixedSize(28, 28)
        cancel_btn.clicked.connect(lambda: self.cancel_clicked.emit(self.video_id))
        layout.addWidget(cancel_btn)

    def update_progress(self, progress: float, status_text: str, status: str):
        self._progress_bar.setValue(int(progress))
        self._ring.set_progress(progress)
        self._status_lbl.setText(status_text)

        if status == DownloadStatus.COMPLETED.value:
            self._status_lbl.setText("✓ Tamamlandı")
            self._status_lbl.setStyleSheet("color: #FF0033;")
        elif status == DownloadStatus.FAILED.value:
            self._status_lbl.setStyleSheet("color: #FF4444;")

class CreatePlaylistDialog(QWidget):
    created = pyqtSignal(str)                 

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Playlist adı...")
        self._input.setFixedHeight(36)
        layout.addWidget(self._input)

        ok_btn = QPushButton("Oluştur")
        ok_btn.setObjectName("btn_primary")
        ok_btn.setFixedHeight(36)
        ok_btn.clicked.connect(self._create)
        layout.addWidget(ok_btn)

        cancel_btn = QPushButton("İptal")
        cancel_btn.setObjectName("btn_secondary")
        cancel_btn.setFixedHeight(36)
        cancel_btn.clicked.connect(self.hide)
        layout.addWidget(cancel_btn)

        self._input.returnPressed.connect(self._create)

    def _create(self):
        name = self._input.text().strip()
        if name:
            self.created.emit(name)
            self._input.clear()
            self.hide()

class DownloadsPage(QWidget):
    song_play_requested   = pyqtSignal(dict, list)               
    playlist_open_requested = pyqtSignal(int)                           

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue_items: Dict[str, DownloadQueueItem] = {}
        self._build_ui()
        self._connect_manager()

        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_counts)
        self._refresh_timer.start(5000)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 0)
        outer.setSpacing(16)

        header_row = QHBoxLayout()
        title = QLabel("İndirilenler")
        title.setObjectName("lbl_title")
        header_row.addWidget(title)
        header_row.addStretch()

        new_playlist_btn = QPushButton("＋  Yeni Playlist")
        new_playlist_btn.setObjectName("btn_secondary")
        new_playlist_btn.setFixedHeight(36)
        new_playlist_btn.clicked.connect(self._show_create_playlist)
        header_row.addWidget(new_playlist_btn)
        outer.addLayout(header_row)

        self._create_form = CreatePlaylistDialog()
        self._create_form.created.connect(self._create_playlist)
        self._create_form.hide()
        outer.addWidget(self._create_form)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabBar::tab { padding: 10px 20px; font-size: 13px; font-weight: 600; color: #777; border-bottom: 2px solid transparent; background: transparent; }
            QTabBar::tab:hover { color: #EEE; }
            QTabBar::tab:selected { color: #FF0033; border-bottom: 2px solid #FF0033; }
            QTabWidget::pane { border: none; background: transparent; }
        """)

        self._queue_tab = QScrollArea()
        self._queue_tab.setWidgetResizable(True)
        self._queue_tab.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._queue_container = QWidget()
        self._queue_container.setStyleSheet("background: transparent;")
        self._queue_layout = QVBoxLayout(self._queue_container)
        self._queue_layout.setContentsMargins(0, 8, 0, 40)
        self._queue_layout.setSpacing(8)
        self._queue_layout.addStretch()
        self._empty_queue_lbl = QLabel("📥 İndirme kuyruğu boş")
        self._empty_queue_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_queue_lbl.setStyleSheet("color: #555; font-size: 14px; padding: 60px;")
        self._queue_layout.insertWidget(0, self._empty_queue_lbl)
        self._queue_tab.setWidget(self._queue_container)
        self._tabs.addTab(self._queue_tab, "⬇  Aktif İndirmeler")

        self._playlists_tab = QScrollArea()
        self._playlists_tab.setWidgetResizable(True)
        self._playlists_tab.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._playlists_container = QWidget()
        self._playlists_container.setStyleSheet("background: transparent;")
        self._playlists_layout = QVBoxLayout(self._playlists_container)
        self._playlists_layout.setContentsMargins(0, 8, 0, 40)
        self._playlists_layout.setSpacing(0)
        self._playlists_layout.addStretch()
        self._playlists_tab.setWidget(self._playlists_container)
        self._tabs.addTab(self._playlists_tab, "🎵  Playlist'ler")

        self._solo_tab = QScrollArea()
        self._solo_tab.setWidgetResizable(True)
        self._solo_tab.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._solo_container = QWidget()
        self._solo_container.setStyleSheet("background: transparent;")
        self._solo_layout = QVBoxLayout(self._solo_container)
        self._solo_layout.setContentsMargins(0, 8, 0, 100)
        self._solo_layout.setSpacing(2)
        self._solo_layout.addStretch()
        self._solo_tab.setWidget(self._solo_container)
        self._tabs.addTab(self._solo_tab, "🎤  Solo İndirilenler")

        self._tabs.currentChanged.connect(self._on_tab_changed)
        outer.addWidget(self._tabs, stretch=1)

    def _connect_manager(self):
        manager = get_manager()
        manager.task_added.connect(self._on_task_added)
        manager.task_updated.connect(self._on_task_updated)
        manager.task_completed.connect(self._on_task_completed)
        manager.task_failed.connect(self._on_task_failed)

    def _on_tab_changed(self, idx: int):
        if idx == 1:
            self._load_playlists()
        elif idx == 2:
            self._load_solo_songs()

    def _on_task_added(self, task: DownloadTask):
        self._empty_queue_lbl.hide()
        item = DownloadQueueItem(task)
        item.cancel_clicked.connect(lambda vid: get_manager().cancel_task(vid))
        self._queue_layout.insertWidget(self._queue_layout.count() - 1, item)
        self._queue_items[task.video_id] = item
                                      
        self._tabs.setCurrentIndex(0)
        self._update_queue_tab_title()

    def _on_task_updated(self, video_id: str, progress: float, status_text: str, status: str):
        if video_id in self._queue_items:
            self._queue_items[video_id].update_progress(progress, status_text, status)

    def _on_task_completed(self, video_id: str, file_path: str):
        if video_id in self._queue_items:
            item = self._queue_items[video_id]
            item.update_progress(100, "✓ Tamamlandı", DownloadStatus.COMPLETED.value)
                                   
            QTimer.singleShot(3000, lambda: self._remove_queue_item(video_id))
        self._update_queue_tab_title()

    def _on_task_failed(self, video_id: str, error: str):
        if video_id in self._queue_items:
            self._queue_items[video_id].update_progress(0, f"✕ Hata: {error[:50]}", DownloadStatus.FAILED.value)
            QTimer.singleShot(5000, lambda: self._remove_queue_item(video_id))

    def _remove_queue_item(self, video_id: str):
        if video_id in self._queue_items:
            item = self._queue_items.pop(video_id)
            item.deleteLater()
        if not self._queue_items:
            self._empty_queue_lbl.show()
        self._update_queue_tab_title()

    def _update_queue_tab_title(self):
        count = len(self._queue_items)
        title = f"⬇  Aktif İndirmeler" + (f"  ({count})" if count > 0 else "")
        self._tabs.setTabText(0, title)

    def _load_playlists(self):
                 
        layout = self._playlists_layout
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        playlists = database.get_all_playlists()
                                 
        playlists = [p for p in playlists if p.get("id") != 1]

        if not playlists:
            lbl = QLabel("📂 Henüz indirilmiş playlist yok.\nBir playlist'i indir veya yeni playlist oluştur.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #555; font-size: 14px; padding: 60px;")
            layout.insertWidget(0, lbl)
            return

        grid_w = QWidget()
        grid_w.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_w)
        grid.setSpacing(16)
        grid.setContentsMargins(0, 8, 0, 0)

        for i, pl in enumerate(playlists):
            card = LocalPlaylistCard(pl, card_width=160)
            card.clicked.connect(self.playlist_open_requested)
            card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            card.customContextMenuRequested.connect(lambda pos, p=pl, c=card: self._playlist_context_menu(p, c, pos))
            grid.addWidget(card, i // 5, i % 5)

        layout.insertWidget(0, grid_w)

    def _load_solo_songs(self):
        layout = self._solo_layout
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        songs = database.get_playlist_songs(1)                      

        if not songs:
            lbl = QLabel("🎤 Henüz solo indirilen şarkı yok.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #555; font-size: 14px; padding: 60px;")
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
        header.addWidget(play_all_btn)

        shuffle_btn = QPushButton("⇄  Karıştır")
        shuffle_btn.setObjectName("btn_secondary")
        shuffle_btn.setFixedHeight(36)
        header.addWidget(shuffle_btn)

        header_w = QWidget()
        header_w.setLayout(header)
        layout.insertWidget(0, header_w)

        queue: List[Dict] = []
        for i, song in enumerate(songs):
            song_data = self._song_to_dict(song)
            queue.append(song_data)
            row = SongRow(song_data, index=i, show_thumbnail=True, show_index=True, is_local=True)
            row.play_requested.connect(lambda s, idx=i, q=queue: self.song_play_requested.emit(s, q))
            row.remove_signal.connect(self._remove_solo_song)
            layout.insertWidget(i + 1, row)

        play_all_btn.clicked.connect(lambda: self.song_play_requested.emit(queue[0], queue) if queue else None)
        shuffle_btn.clicked.connect(lambda: self._shuffle_play(queue))

    def _shuffle_play(self, queue: List[Dict]):
        if queue:
            import random
            player = get_player()
            shuffled = list(queue)
            random.shuffle(shuffled)
            player.set_queue(shuffled, 0)

    def _remove_solo_song(self, song_data: Dict):
        song_id = song_data.get("id")
        if song_id:
            database.remove_song_from_playlist(1, song_id)
            self._load_solo_songs()

    def _playlist_context_menu(self, playlist: Dict, card: QWidget, pos):
        menu = QMenu(self)
        rename_act = QAction("✏  Yeniden Adlandır", self)
        rename_act.triggered.connect(lambda: self._rename_playlist(playlist))
        delete_act = QAction("🗑  Sil", self)
        delete_act.triggered.connect(lambda: self._delete_playlist(playlist))
        menu.addAction(rename_act)
        menu.addAction(delete_act)
        menu.exec(card.mapToGlobal(pos))

    def _rename_playlist(self, playlist: Dict):
        name, ok = QInputDialog.getText(
            self, "Playlist Adını Değiştir", "Yeni ad:",
            text=playlist.get("name", "")
        )
        if ok and name.strip():
            database.rename_playlist(playlist["id"], name.strip())
            self._load_playlists()

    def _delete_playlist(self, playlist: Dict):
        reply = QMessageBox.question(
            self, "Playlist Sil",
            f"'{playlist.get('name')}' playlist'ini silmek istediğinizden emin misiniz?\n(Şarkı dosyaları silinmez)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            database.delete_playlist(playlist["id"])
            self._load_playlists()

    def _show_create_playlist(self):
        self._create_form.setVisible(not self._create_form.isVisible())

    def _create_playlist(self, name: str):
        database.create_playlist(name)
        self._tabs.setCurrentIndex(1)
        self._load_playlists()

    def _refresh_counts(self):
        if self._tabs.currentIndex() == 2:
            pass                            

    def _song_to_dict(self, song: Dict) -> Dict:
        thumb = song.get("thumbnail_path", "")
        return {
            "videoId":    song.get("video_id", ""),
            "video_id":   song.get("video_id", ""),
            "title":      song.get("title", ""),
            "artists":    [{"name": song.get("artist", "")}],
            "artist":     song.get("artist", ""),
            "album":      {"name": song.get("album", "")},
            "duration_seconds": song.get("duration", 0),
            "thumbnails": [{"url": "file:///" + thumb.replace("\\", "/"), "width": 120}] if thumb else [],
            "file_path":  song.get("file_path", ""),
            "id":         song.get("id"),
        }

    def refresh(self):
        idx = self._tabs.currentIndex()
        if idx == 1:
            self._load_playlists()
        elif idx == 2:
            self._load_solo_songs()
