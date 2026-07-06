from typing import List, Dict, Optional
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QLineEdit, QPushButton, QScrollArea, QFrame,
                              QSizePolicy, QCompleter, QListWidget, QListWidgetItem,
                              QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QStringListModel
from PyQt6.QtGui import QFont, QKeySequence, QIcon

from core.ytmusic_client import get_client
from ui.widgets.song_card import SongRow
from ui.widgets.playlist_card import PlaylistCard

FILTER_LABELS = {
    "songs":                "Şarkılar",
    "videos":               "Videolar",
    "albums":               "Albümler",
    "artists":              "Sanatçılar",
    "playlists":            "Playlist'ler",
    "community_playlists":  "Topluluk",
}

class FilterBar(QFrame):
    filter_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")
        self._active = "songs"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._buttons: Dict[str, QPushButton] = {}

        for key, label in FILTER_LABELS.items():
            btn = QPushButton(label)
            btn.setObjectName("filter_btn")
            btn.setCheckable(False)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self._select(k))
            layout.addWidget(btn)
            self._buttons[key] = btn

        layout.addStretch()
        self._select("songs")

    def _select(self, key: str):
        self._active = key
        for k, btn in self._buttons.items():
            btn.setProperty("active", "true" if k == key else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.filter_changed.emit(key)

    @property
    def active(self) -> str:
        return self._active

class SearchResultsWidget(QWidget):
    song_play_requested      = pyqtSignal(dict)
    song_download_requested  = pyqtSignal(dict)
    playlist_open_requested  = pyqtSignal(dict)
    add_to_queue_signal      = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self._rows: List[QWidget] = []
        self._current_filter = "songs"

    def set_filter(self, filter_type: str):
        self._current_filter = filter_type

    def show_results(self, results: List[Dict], filter_type: str):
        self._clear()
        self._current_filter = filter_type

        if not results:
            empty = QLabel("Sonuç bulunamadı.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #777; font-size: 14px; padding: 40px;")
            self._layout.addWidget(empty)
            self._rows.append(empty)
            return

        if filter_type in ("songs", "videos"):
            for i, item in enumerate(results[:40]):
                row = SongRow(item, index=i, show_thumbnail=True, show_index=True)
                row.play_requested.connect(self.song_play_requested)
                row.download_requested.connect(self.song_download_requested)
                row.add_to_queue_signal.connect(self.add_to_queue_signal)
                self._layout.addWidget(row)
                self._rows.append(row)

        elif filter_type in ("playlists", "albums", "community_playlists"):
                           
            grid_container = QWidget()
            grid_container.setStyleSheet("background: transparent;")
            from PyQt6.QtWidgets import QGridLayout
            grid = QGridLayout(grid_container)
            grid.setSpacing(12)
            grid.setContentsMargins(0, 0, 0, 0)

            for i, item in enumerate(results[:30]):
                card = PlaylistCard(item, card_width=160)
                card.clicked.connect(self.playlist_open_requested)
                grid.addWidget(card, i // 5, i % 5)

            self._layout.addWidget(grid_container)
            self._rows.append(grid_container)

        elif filter_type == "artists":
            for item in results[:20]:
                name = item.get("artist", item.get("title", ""))
                sub  = item.get("subscribers", "")
                lbl = QLabel(f"🎤 {name}  {('• ' + sub) if sub else ''}")
                lbl.setFont(QFont("Segoe UI", 14))
                lbl.setStyleSheet("color: #EFEFEF; padding: 10px 4px; border-bottom: 1px solid #1A1A1A;")
                self._layout.addWidget(lbl)
                self._rows.append(lbl)

        self._layout.addStretch()

    def _clear(self):
        for w in self._rows:
            w.deleteLater()
        self._rows.clear()
                        
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

class SearchPage(QWidget):
    playlist_open_requested = pyqtSignal(dict)
    song_play_requested     = pyqtSignal(dict)
    song_download_requested = pyqtSignal(dict)
    add_to_queue_signal     = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_query  = ""
        self._current_filter = "songs"
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._do_search)

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 0)
        outer.setSpacing(16)

        title = QLabel("Ara")
        title.setObjectName("lbl_title")
        outer.addWidget(title)

        search_row = QHBoxLayout()
        search_row.setSpacing(12)

        self._search_input = QLineEdit()
        self._search_input.setObjectName("search_input")
        self._search_input.setPlaceholderText("🔍  Şarkı, sanatçı, albüm ara...")
        self._search_input.setFixedHeight(48)
        search_row.addWidget(self._search_input)

        self._clear_btn = QPushButton("✕")
        self._clear_btn.setObjectName("btn_icon")
        self._clear_btn.setFixedSize(36, 36)
        self._clear_btn.setVisible(False)
        self._clear_btn.clicked.connect(self._clear_search)
        search_row.addWidget(self._clear_btn)

        outer.addLayout(search_row)

        self._filter_bar = FilterBar()
        outer.addWidget(self._filter_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._results_widget = SearchResultsWidget()
        self._results_widget.song_play_requested.connect(self.song_play_requested)
        self._results_widget.song_download_requested.connect(self.song_download_requested)
        self._results_widget.playlist_open_requested.connect(self.playlist_open_requested)
        self._results_widget.add_to_queue_signal.connect(self.add_to_queue_signal)
        scroll.setWidget(self._results_widget)
        outer.addWidget(scroll, stretch=1)

        self._status_lbl = QLabel("YouTube Music'te arama yapın")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setStyleSheet("color: #555; font-size: 14px; padding: 40px;")
        outer.addWidget(self._status_lbl)

    def _connect_signals(self):
        self._search_input.textChanged.connect(self._on_text_changed)
        self._search_input.returnPressed.connect(self._do_search)
        self._filter_bar.filter_changed.connect(self._on_filter_changed)

        client = get_client()
        client.search_results_ready.connect(self._on_results)

    def _on_text_changed(self, text: str):
        self._clear_btn.setVisible(bool(text))
        self._current_query = text
        if len(text) >= 2:
            self._debounce_timer.start(350)
        else:
            self._debounce_timer.stop()

    def _on_filter_changed(self, filter_type: str):
        self._current_filter = filter_type
        self._results_widget.set_filter(filter_type)
        if self._current_query:
            self._do_search()

    def _do_search(self):
        query = self._current_query.strip()
        if not query:
            return

        client = get_client()
        if not client.is_authenticated():
            self._status_lbl.setText("Giriş yapmanız gerekiyor.")
            return

        self._status_lbl.setText(f"'{query}' aranıyor...")
        self._status_lbl.setVisible(True)
        client.search(query, self._current_filter)

    def _on_results(self, results: List[Dict], filter_type: str):
        self._status_lbl.setVisible(False)
        if filter_type != self._current_filter:
            return
        self._results_widget.show_results(results, filter_type)

    def _clear_search(self):
        self._search_input.clear()
        self._results_widget._clear()
        self._status_lbl.setText("YouTube Music'te arama yapın")
        self._status_lbl.setVisible(True)

    def focus_search(self):
        self._search_input.setFocus()
        self._search_input.selectAll()
