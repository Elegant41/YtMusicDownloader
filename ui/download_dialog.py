from __future__ import annotations

from typing import List, Optional, Union

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QButtonGroup,
    QRadioButton,
    QFrame,
    QLineEdit,
    QComboBox,
    QSizePolicy,
    QScrollArea,
    QWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap

from core.downloader import QUALITY_PRESETS, make_download_task_from_yt, get_manager
from core import database
from ui.widgets.thumbnail import ThumbnailWidget

_QUALITY_CARDS = [
    ("low",      "🟢 Düşük Kalite",   "64 kbps MP3  •  En küçük dosya"),
    ("medium",   "🟡 Orta Kalite",    "128 kbps MP3  •  Dengeli"),
    ("high",     "🔴 Yüksek Kalite",  "256 kbps MP3  •  Önerilen"),
    ("original", "⚡ Orijinal",       "320 kbps MP3  •  En iyi kalite"),
]

_DEFAULT_QUALITY = "high"

_NEW_PLAYLIST_SENTINEL = "__new_playlist__"

def _make_quality_card(
    key: str,
    title: str,
    desc: str,
    radio: QRadioButton,
    is_default: bool,
) -> QFrame:
    card = QFrame()
    card.setObjectName("quality_card")
    card.setCursor(Qt.CursorShape.PointingHandCursor)
    card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    card.setProperty("quality_key", key)

    row = QHBoxLayout(card)
    row.setContentsMargins(14, 10, 14, 10)
    row.setSpacing(12)

    radio.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    row.addWidget(radio)

    text_box = QVBoxLayout()
    text_box.setSpacing(2)

    lbl_title = QLabel(title)
    font_title = QFont("Segoe UI", 10)
    font_title.setBold(True)
    lbl_title.setFont(font_title)
    lbl_title.setStyleSheet("color: #FFFFFF; background: transparent;")

    lbl_desc = QLabel(desc)
    font_desc = QFont("Segoe UI", 8)
    lbl_desc.setFont(font_desc)
    lbl_desc.setStyleSheet("color: #888888; background: transparent;")

    text_box.addWidget(lbl_title)
    text_box.addWidget(lbl_desc)

    row.addLayout(text_box)
    row.addStretch()

    _apply_card_style(card, active=is_default)

    return card

def _apply_card_style(card: QFrame, active: bool) -> None:
    if active:
        card.setStyleSheet("""
            QFrame#quality_card {
                background-color: #1E1E1E;
                border: 1px solid #333333;
                border-left: 3px solid #FF0000;
                border-radius: 8px;
            }
        """)
    else:
        card.setStyleSheet("""
            QFrame#quality_card {
                background-color: #141414;
                border: 1px solid #2A2A2A;
                border-radius: 8px;
            }
            QFrame#quality_card:hover {
                background-color: #1A1A1A;
                border: 1px solid #444444;
            }
        """)

class DownloadDialog(QDialog):

    download_requested = pyqtSignal()

    def __init__(
        self,
        song_data: Union[dict, List[dict]],
        is_playlist: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self._song_data = song_data
        self._is_playlist = is_playlist

        self._songs: List[dict] = (
            song_data if isinstance(song_data, list) else [song_data]
        )

        self._radio_buttons: dict[str, QRadioButton] = {}
        self._quality_cards: dict[str, QFrame] = {}
        self._btn_group = QButtonGroup(self)

        self._combo_playlist: Optional[QComboBox] = None
        self._new_playlist_edit: Optional[QLineEdit] = None
        self._playlist_id_map: dict[int, int] = {}                        

        self._setup_window()
        self._build_ui()

    def _setup_window(self) -> None:
        self.setWindowTitle("İndirme Seçenekleri")
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F0F0F;
                color: #FFFFFF;
            }
            QLabel {
                color: #FFFFFF;
                background: transparent;
            }
            QComboBox {
                background-color: #1A1A1A;
                color: #FFFFFF;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                min-height: 32px;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #1A1A1A;
                color: #FFFFFF;
                selection-background-color: #FF0000;
                border: 1px solid #333333;
                outline: none;
            }
            QLineEdit {
                background-color: #1A1A1A;
                color: #FFFFFF;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                min-height: 32px;
            }
            QLineEdit:focus {
                border: 1px solid #FF0000;
            }
            QRadioButton {
                color: #FFFFFF;
                background: transparent;
                spacing: 0px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 2px solid #555555;
                background: transparent;
            }
            QRadioButton::indicator:checked {
                background-color: #FF0000;
                border: 2px solid #FF0000;
            }
        """)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        root.addLayout(self._build_header_section())
        root.addWidget(self._build_divider())
        root.addLayout(self._build_quality_section())
        root.addWidget(self._build_divider())
        root.addLayout(self._build_playlist_section())
        root.addStretch()
        root.addLayout(self._build_button_row())

    def _build_header_section(self) -> QHBoxLayout:
        hbox = QHBoxLayout()
        hbox.setSpacing(14)

        if self._is_playlist or len(self._songs) > 1:
                             
            icon_lbl = QLabel("🎵")
            icon_lbl.setFont(QFont("Segoe UI", 26))
            icon_lbl.setFixedSize(64, 64)
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_lbl.setStyleSheet(
                "background-color: #1A1A1A; border-radius: 8px; color: #FF0000;"
            )

            count = len(self._songs)
            info_lbl = QLabel(f"{count} şarkı indirilecek")
            info_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            info_lbl.setStyleSheet("color: #FFFFFF;")

            hbox.addWidget(icon_lbl)
            hbox.addWidget(info_lbl)
            hbox.addStretch()

        else:
                                
            song = self._songs[0]

            thumb = ThumbnailWidget(size=64, radius=8, parent=self)
            thumbnails = song.get("thumbnails") or []
            if thumbnails:
                best = max(
                    thumbnails,
                    key=lambda t: t.get("width", 0) if isinstance(t, dict) else 0,
                )
                url = best.get("url", "") if isinstance(best, dict) else ""
                if url:
                    thumb.set_url(url)

            hbox.addWidget(thumb)

            vbox = QVBoxLayout()
            vbox.setSpacing(4)

            title_text = song.get("title", "Bilinmiyor")
            title_lbl = QLabel(title_text)
            title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            title_lbl.setStyleSheet("color: #FFFFFF;")
            title_lbl.setWordWrap(True)

            artists = song.get("artists") or []
            if artists:
                artist_text = ", ".join(
                    a.get("name", "") for a in artists if isinstance(a, dict)
                )
            else:
                artist_text = song.get("artist", "Bilinmiyor")

            artist_lbl = QLabel(artist_text)
            artist_lbl.setFont(QFont("Segoe UI", 9))
            artist_lbl.setStyleSheet("color: #888888;")

            vbox.addWidget(title_lbl)
            vbox.addWidget(artist_lbl)
            vbox.addStretch()

            hbox.addLayout(vbox)
            hbox.addStretch()

        return hbox

    def _build_quality_section(self) -> QVBoxLayout:
        vbox = QVBoxLayout()
        vbox.setSpacing(8)

        section_lbl = QLabel("Kalite Seçin:")
        section_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        section_lbl.setStyleSheet("color: #FFFFFF;")
        vbox.addWidget(section_lbl)

        for key, title, desc in _QUALITY_CARDS:
            is_default = key == _DEFAULT_QUALITY

            radio = QRadioButton()
            radio.setChecked(is_default)
            self._btn_group.addButton(radio)
            self._radio_buttons[key] = radio

            card = _make_quality_card(key, title, desc, radio, is_default)
            self._quality_cards[key] = card

            radio.toggled.connect(
                lambda checked, k=key: self._on_quality_toggled(k, checked)
            )

            card.mousePressEvent = lambda event, k=key: self._select_quality(k)

            vbox.addWidget(card)

        return vbox

    def _on_quality_toggled(self, key: str, checked: bool) -> None:
        if checked:
            for k, card in self._quality_cards.items():
                _apply_card_style(card, active=(k == key))

    def _select_quality(self, key: str) -> None:
        radio = self._radio_buttons.get(key)
        if radio and not radio.isChecked():
            radio.setChecked(True)
                                                   
    def _get_selected_quality(self) -> str:
        for key, radio in self._radio_buttons.items():
            if radio.isChecked():
                return key
        return _DEFAULT_QUALITY

    def _build_playlist_section(self) -> QVBoxLayout:
        vbox = QVBoxLayout()
        vbox.setSpacing(8)

        pl_lbl = QLabel("Kaydedilecek Playlist:")
        pl_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        pl_lbl.setStyleSheet("color: #FFFFFF;")
        vbox.addWidget(pl_lbl)

        self._combo_playlist = QComboBox()
        self._combo_playlist.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._populate_playlist_combo()
        self._combo_playlist.currentIndexChanged.connect(self._on_combo_changed)
        vbox.addWidget(self._combo_playlist)

        self._new_playlist_edit = QLineEdit()
        self._new_playlist_edit.setPlaceholderText("Yeni playlist adı girin…")
        self._new_playlist_edit.setVisible(False)
        vbox.addWidget(self._new_playlist_edit)

        return vbox

    def _populate_playlist_combo(self) -> None:
        combo = self._combo_playlist
        combo.blockSignals(True)
        combo.clear()
        self._playlist_id_map.clear()

        combo.addItem("➕  Yeni Playlist Oluştur…", _NEW_PLAYLIST_SENTINEL)

        playlists = database.get_all_playlists()
        default_index = 1                                                      

        for i, pl in enumerate(playlists):
            combo.addItem(pl["name"], pl["id"])
            self._playlist_id_map[i + 1] = pl["id"]                            
            if pl["id"] == 1:                       
                default_index = i + 1

        combo.setCurrentIndex(default_index)
        combo.blockSignals(False)

    def _on_combo_changed(self, index: int) -> None:
        is_new = self._combo_playlist.itemData(index) == _NEW_PLAYLIST_SENTINEL
        self._new_playlist_edit.setVisible(is_new)
        if is_new:
            self._new_playlist_edit.setFocus()

    def _resolve_playlist_id(self) -> Optional[int]:
        combo = self._combo_playlist
        data = combo.currentData()

        if data == _NEW_PLAYLIST_SENTINEL:
            name = (self._new_playlist_edit.text() or "").strip()
            if not name:
                name = "Yeni Playlist"
            return database.create_playlist(name)

        try:
            return int(data)
        except (TypeError, ValueError):
            return 1                              

    def _build_button_row(self) -> QHBoxLayout:
        hbox = QHBoxLayout()
        hbox.setSpacing(10)
        hbox.addStretch()

        btn_cancel = QPushButton("İptal")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setMinimumWidth(90)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #AAAAAA;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 13px;
            }
            QPushButton:hover {
                color: #FFFFFF;
                border-color: #555555;
                background-color: #1A1A1A;
            }
            QPushButton:pressed {
                background-color: #111111;
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_download = QPushButton("⬇ İndir")
        btn_download.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_download.setMinimumWidth(110)
        btn_download.setStyleSheet("""
            QPushButton {
                background-color: #FF0000;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
            QPushButton:pressed {
                background-color: #AA0000;
            }
        """)
        btn_download.clicked.connect(self._start_download)

        hbox.addWidget(btn_cancel)
        hbox.addWidget(btn_download)

        return hbox

    @staticmethod
    def _build_divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #222222; background-color: #222222;")
        line.setFixedHeight(1)
        return line

    def _start_download(self) -> None:
        quality = self._get_selected_quality()
        playlist_id = self._resolve_playlist_id()

        manager = get_manager()

        for song in self._songs:
            task = make_download_task_from_yt(song, quality, playlist_id)
            manager.add_task(task)

        self.download_requested.emit()
        self.accept()
