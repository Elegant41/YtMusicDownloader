import os
from typing import Dict, Optional
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QSlider, QFrame, QSizePolicy,
                              QGraphicsBlurEffect)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QRect
from PyQt6.QtGui import QFont, QPixmap, QPainter, QLinearGradient, QColor, QBrush

from core.player import get_player, RepeatMode
from ui.widgets.thumbnail import ThumbnailWidget
from ui.widgets.waveform import WaveformWidget

def _format_ms(ms: int) -> str:
    if ms < 0:
        return "0:00"
    s  = ms // 1000
    m  = s // 60
    s %= 60
    return f"{m}:{s:02d}"

class NowPlayingPage(QWidget):
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: #0A0A0A;")
        self._seeking = False
        self._build_ui()
        self._connect_player()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(0)

        close_row = QHBoxLayout()
        close_btn = QPushButton("✕  Kapat")
        close_btn.setObjectName("btn_secondary")
        close_btn.setFixedHeight(32)
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.close_requested)
        close_row.addWidget(close_btn)
        close_row.addStretch()
        layout.addLayout(close_row)

        layout.addSpacing(20)

        main_row = QHBoxLayout()
        main_row.setSpacing(60)

        left = QVBoxLayout()
        left.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._cover = ThumbnailWidget(size=300, radius=20)
        left.addWidget(self._cover, alignment=Qt.AlignmentFlag.AlignCenter)

        self._waveform = WaveformWidget(bar_count=32)
        self._waveform.setFixedHeight(36)
        self._waveform.setFixedWidth(300)
        left.addSpacing(16)
        left.addWidget(self._waveform, alignment=Qt.AlignmentFlag.AlignCenter)

        main_row.addLayout(left)

        right = QVBoxLayout()
        right.setSpacing(20)
        right.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._title_lbl = QLabel("—")
        self._title_lbl.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet("color: #FFFFFF;")
        self._title_lbl.setWordWrap(True)
        right.addWidget(self._title_lbl)

        self._artist_lbl = QLabel("—")
        self._artist_lbl.setFont(QFont("Segoe UI", 16))
        self._artist_lbl.setStyleSheet("color: #AFAFAF;")
        right.addWidget(self._artist_lbl)

        self._album_lbl = QLabel("")
        self._album_lbl.setFont(QFont("Segoe UI", 13))
        self._album_lbl.setStyleSheet("color: #666;")
        right.addWidget(self._album_lbl)

        right.addSpacing(20)

        progress_row = QHBoxLayout()
        self._time_cur = QLabel("0:00")
        self._time_cur.setStyleSheet("color: #666; font-size: 12px;")
        self._time_cur.setFixedWidth(36)
        progress_row.addWidget(self._time_cur)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 1000)
        self._slider.setValue(0)
        self._slider.sliderPressed.connect(lambda: setattr(self, '_seeking', True))
        self._slider.sliderReleased.connect(self._on_seek)
        progress_row.addWidget(self._slider, stretch=1)

        self._time_tot = QLabel("0:00")
        self._time_tot.setStyleSheet("color: #666; font-size: 12px;")
        self._time_tot.setFixedWidth(36)
        self._time_tot.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        progress_row.addWidget(self._time_tot)

        right.addLayout(progress_row)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(16)
        ctrl_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._shuffle_btn = QPushButton("⇄")
        self._shuffle_btn.setObjectName("btn_icon")
        self._shuffle_btn.setFixedSize(44, 44)
        self._shuffle_btn.clicked.connect(get_player().toggle_shuffle)

        self._prev_btn = QPushButton("⏮")
        self._prev_btn.setObjectName("btn_icon")
        self._prev_btn.setFixedSize(44, 44)
        self._prev_btn.clicked.connect(get_player().previous)

        self._play_btn = QPushButton("▶")
        self._play_btn.setObjectName("btn_play_large")
        self._play_btn.setFixedSize(64, 64)
        self._play_btn.clicked.connect(get_player().toggle_play_pause)

        self._next_btn = QPushButton("⏭")
        self._next_btn.setObjectName("btn_icon")
        self._next_btn.setFixedSize(44, 44)
        self._next_btn.clicked.connect(get_player().next)

        self._repeat_btn = QPushButton("🔁")
        self._repeat_btn.setObjectName("btn_icon")
        self._repeat_btn.setFixedSize(44, 44)
        self._repeat_btn.clicked.connect(get_player().toggle_repeat)

        ctrl_row.addWidget(self._shuffle_btn)
        ctrl_row.addWidget(self._prev_btn)
        ctrl_row.addWidget(self._play_btn)
        ctrl_row.addWidget(self._next_btn)
        ctrl_row.addWidget(self._repeat_btn)
        right.addLayout(ctrl_row)

        vol_row = QHBoxLayout()
        vol_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet("color: #666; font-size: 16px;")
        vol_row.addWidget(vol_icon)
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setObjectName("volume_slider")
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(80)
        self._vol_slider.setFixedWidth(160)
        self._vol_slider.valueChanged.connect(lambda v: get_player().set_volume(v / 100))
        vol_row.addWidget(self._vol_slider)
        right.addLayout(vol_row)

        right.addStretch()
        main_row.addLayout(right)
        layout.addLayout(main_row, stretch=1)

    def _connect_player(self):
        player = get_player()
        player.track_changed.connect(self._on_track_changed)
        player.state_changed.connect(self._on_state_changed)
        player.position_changed.connect(self._on_position)
        player.shuffle_changed.connect(self._on_shuffle)
        player.repeat_changed.connect(self._on_repeat)

    def _on_track_changed(self, song: Dict):
        title = song.get("title", "—")
        artists = song.get("artists") or []
        if artists and isinstance(artists[0], dict):
            artist = ", ".join(a.get("name", "") for a in artists)
        else:
            artist = song.get("artist", "—")
        album_data = song.get("album") or {}
        album = album_data.get("name", "") if isinstance(album_data, dict) else ""

        self._title_lbl.setText(title)
        self._artist_lbl.setText(artist)
        self._album_lbl.setText(album)

        thumbnails = song.get("thumbnails") or []
        if thumbnails:
            best = max(thumbnails, key=lambda t: t.get("width", 0) if isinstance(t, dict) else 0)
            url = best.get("url", "") if isinstance(best, dict) else ""
            if url:
                self._cover.set_url(url)

    def _on_state_changed(self, state: str):
        if state == "playing":
            self._play_btn.setText("⏸")
            self._waveform.start()
        else:
            self._play_btn.setText("▶")
            self._waveform.stop()

    def _on_position(self, pos_ms: int, dur_ms: int):
        if self._seeking:
            return
        if dur_ms > 0:
            self._slider.setValue(int(pos_ms * 1000 / dur_ms))
        self._time_cur.setText(_format_ms(pos_ms))
        self._time_tot.setText(_format_ms(dur_ms))

    def _on_seek(self):
        self._seeking = False
        dur = get_player().duration
        if dur > 0:
            pos = int(self._slider.value() * dur / 1000)
            get_player().seek(pos)

    def _on_shuffle(self, active: bool):
        self._shuffle_btn.setStyleSheet(
            "color: #FF0033;" if active else "color: #AFAFAF;"
        )

    def _on_repeat(self, mode: str):
        colors = {"none": "#AFAFAF", "all": "#FF0033", "one": "#FF8C00"}
        self._repeat_btn.setStyleSheet(f"color: {colors.get(mode, '#AFAFAF')};")
