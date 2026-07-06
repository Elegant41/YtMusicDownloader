from __future__ import annotations

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSizePolicy,
    QWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap

from core.player import get_player, RepeatMode, PlayerState
from core.database import get_setting
from ui.widgets.thumbnail import ThumbnailWidget

_BTN_ICON_STYLE = """
    QPushButton#btn_icon {
        background: transparent;
        border: none;
        color: #aaaaaa;
        font-size: 16px;
        padding: 4px 8px;
        border-radius: 4px;
    }
    QPushButton#btn_icon:hover {
        color: #ffffff;
        background: rgba(255, 255, 255, 0.08);
    }
    QPushButton#btn_icon:pressed {
        background: rgba(255, 255, 255, 0.14);
    }
"""

_BTN_PLAY_LARGE_STYLE = """
    QPushButton#btn_play_large {
        background: #ffffff;
        border: none;
        color: #000000;
        font-size: 18px;
        padding: 0px;
        border-radius: 18px;
        min-width: 36px;
        max-width: 36px;
        min-height: 36px;
        max-height: 36px;
    }
    QPushButton#btn_play_large:hover {
        background: #e0e0e0;
    }
    QPushButton#btn_play_large:pressed {
        background: #c0c0c0;
    }
"""

_SLIDER_PROGRESS_STYLE = """
    QSlider::groove:horizontal {
        height: 4px;
        background: #444444;
        border-radius: 2px;
    }
    QSlider::sub-page:horizontal {
        background: #ff0000;
        border-radius: 2px;
    }
    QSlider::handle:horizontal {
        background: #ffffff;
        border: none;
        width: 12px;
        height: 12px;
        margin: -4px 0;
        border-radius: 6px;
    }
    QSlider::handle:horizontal:hover {
        background: #ff3333;
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }
"""

_SLIDER_VOLUME_STYLE = """
    QSlider#volume_slider::groove:horizontal {
        height: 4px;
        background: #444444;
        border-radius: 2px;
    }
    QSlider#volume_slider::sub-page:horizontal {
        background: #aaaaaa;
        border-radius: 2px;
    }
    QSlider#volume_slider::handle:horizontal {
        background: #ffffff;
        border: none;
        width: 10px;
        height: 10px;
        margin: -3px 0;
        border-radius: 5px;
    }
"""

_ACTIVE_ICON_STYLE = "color: #ff0000;"
_INACTIVE_ICON_STYLE = "color: #aaaaaa;"
_REPEAT_ONE_STYLE = "color: #ff6666;"

class PlayerBar(QFrame):

    queue_toggled = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setObjectName("player_bar")
        self.setFixedHeight(88)

        self._seeking: bool = False
        self._muted: bool = False
        self._last_volume: int = 80                   

        self._build_ui()
        self._connect_player()
        self._apply_initial_settings()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 0, 12, 0)
        root.setSpacing(0)

        root.addWidget(self._build_left_section(), stretch=1)
        root.addWidget(self._build_center_section())
        root.addWidget(self._build_right_section(), stretch=1)

    def _build_left_section(self) -> QWidget:
        self._left = QWidget()
        self._left.setVisible(False)

        layout = QHBoxLayout(self._left)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._thumbnail = ThumbnailWidget(size=48, radius=6)
        layout.addWidget(self._thumbnail, alignment=Qt.AlignmentFlag.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)

        self._title_label = QLabel("--")
        self._title_label.setMaximumWidth(180)
        self._title_label.setWordWrap(False)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        self._title_label.setFont(title_font)
        self._title_label.setStyleSheet("color: #ffffff;")

        self._artist_label = QLabel("--")
        artist_font = QFont()
        artist_font.setPointSize(8)
        self._artist_label.setFont(artist_font)
        self._artist_label.setStyleSheet("color: #777777;")
        self._artist_label.setWordWrap(False)
        self._artist_label.setMaximumWidth(180)

        text_col.addWidget(self._title_label)
        text_col.addWidget(self._artist_label)

        layout.addLayout(text_col)
        layout.addStretch()

        return self._left

    def _build_center_section(self) -> QWidget:
        center = QWidget()
        center.setFixedWidth(380)

        layout = QVBoxLayout(center)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(4)
        btn_row.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        self._shuffle_btn = self._make_icon_btn("\u21c4", "btn_icon")
        self._prev_btn = self._make_icon_btn("\u23ee", "btn_icon")
        self._play_btn = self._make_icon_btn("\u25b6", "btn_play_large")
        self._next_btn = self._make_icon_btn("\u23ed", "btn_icon")
        self._repeat_btn = self._make_icon_btn("\U0001f501", "btn_icon")

        for btn in (self._prev_btn, self._next_btn):
            f = btn.font()
            f.setPointSize(12)
            btn.setFont(f)

        btn_row.addWidget(self._shuffle_btn)
        btn_row.addSpacing(6)
        btn_row.addWidget(self._prev_btn)
        btn_row.addSpacing(6)
        btn_row.addWidget(self._play_btn)
        btn_row.addSpacing(6)
        btn_row.addWidget(self._next_btn)
        btn_row.addSpacing(6)
        btn_row.addWidget(self._repeat_btn)

        layout.addLayout(btn_row)

        seek_row = QHBoxLayout()
        seek_row.setContentsMargins(0, 0, 0, 0)
        seek_row.setSpacing(6)

        time_font = QFont()
        time_font.setPointSize(7)

        self._time_current_lbl = QLabel("0:00")
        self._time_current_lbl.setFixedWidth(40)
        self._time_current_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._time_current_lbl.setFont(time_font)
        self._time_current_lbl.setStyleSheet("color: #888888;")

        self._progress_slider = QSlider(Qt.Orientation.Horizontal)
        self._progress_slider.setRange(0, 1000)
        self._progress_slider.setValue(0)
        self._progress_slider.setTracking(False)
        self._progress_slider.setStyleSheet(_SLIDER_PROGRESS_STYLE)
        self._progress_slider.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        self._time_total_lbl = QLabel("0:00")
        self._time_total_lbl.setFixedWidth(40)
        self._time_total_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._time_total_lbl.setFont(time_font)
        self._time_total_lbl.setStyleSheet("color: #888888;")

        seek_row.addWidget(self._time_current_lbl)
        seek_row.addWidget(self._progress_slider)
        seek_row.addWidget(self._time_total_lbl)

        layout.addLayout(seek_row)

        self.setStyleSheet(self.styleSheet() + _BTN_ICON_STYLE + _BTN_PLAY_LARGE_STYLE)

        return center

    def _build_right_section(self) -> QWidget:
        right = QWidget()

        layout = QHBoxLayout(right)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._queue_btn = self._make_icon_btn("\u2630", "btn_icon")
        self._queue_btn.setToolTip("Calma Sirasi")

        self._vol_icon_btn = self._make_icon_btn("\U0001f50a", "btn_icon")

        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setObjectName("volume_slider")
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(self._last_volume)
        self._vol_slider.setFixedWidth(100)
        self._vol_slider.setStyleSheet(_SLIDER_VOLUME_STYLE)

        layout.addWidget(self._queue_btn)
        layout.addSpacing(4)
        layout.addWidget(self._vol_icon_btn)
        layout.addWidget(self._vol_slider)

        return right

    @staticmethod
    def _make_icon_btn(text: str, object_name: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName(object_name)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return btn

    def _connect_player(self) -> None:
        player = get_player()

        player.state_changed.connect(self._on_state_changed)
        player.track_changed.connect(self._on_track_changed)
        player.position_changed.connect(self._on_position_changed)
        player.shuffle_changed.connect(self._on_shuffle_changed)
        player.repeat_changed.connect(self._on_repeat_changed)

        self._progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self._progress_slider.sliderReleased.connect(self._on_slider_released)

        self._play_btn.clicked.connect(player.toggle_play_pause)
        self._prev_btn.clicked.connect(player.previous)
        self._next_btn.clicked.connect(player.next)
        self._shuffle_btn.clicked.connect(player.toggle_shuffle)
        self._repeat_btn.clicked.connect(player.toggle_repeat)

        self._queue_btn.clicked.connect(self.queue_toggled.emit)

        self._vol_slider.valueChanged.connect(self._on_volume_changed)
        self._vol_icon_btn.clicked.connect(self._toggle_mute)

    def _apply_initial_settings(self) -> None:
        try:
            saved_vol = get_setting("volume", default=80)
            volume = int(saved_vol)
            volume = max(0, min(100, volume))
        except Exception:
            volume = 80

        self._last_volume = volume
        self._vol_slider.setValue(volume)

        player = get_player()
        player.set_volume(volume / 100.0)

    def _on_state_changed(self, state: PlayerState) -> None:
        if state == PlayerState.PLAYING:
            self._play_btn.setText("\u23f8")                 
        else:
            self._play_btn.setText("\u25b6")                

    def _on_track_changed(self, song: object) -> None:
        if song is None:
            self._left.setVisible(False)
            return

        title: str = ""
        artist: str = ""
        thumbnail_url: str = ""

        if isinstance(song, dict):
            title = song.get("title", "") or song.get("name", "")
            artist = (
                song.get("artist", "")
                or song.get("author", "")
                or song.get("channel", "")
            )
            thumbnail_url = (
                song.get("thumbnail_url", "")
                or song.get("thumbnail", "")
                or song.get("cover", "")
            )
        else:
            title = getattr(song, "title", "") or getattr(song, "name", "")
            artist = (
                getattr(song, "artist", "")
                or getattr(song, "author", "")
                or getattr(song, "channel", "")
            )
            thumbnail_url = (
                getattr(song, "thumbnail_url", "")
                or getattr(song, "thumbnail", "")
                or getattr(song, "cover", "")
            )

        display_title = title[:25] + "\u2026" if len(title) > 25 else title
        display_artist = artist[:25] + "\u2026" if len(artist) > 25 else artist

        self._title_label.setText(display_title or "--")
        self._artist_label.setText(display_artist or "--")

        if thumbnail_url:
            try:
                self._thumbnail.set_url(thumbnail_url)
            except AttributeError:
                try:
                    self._thumbnail.load_url(thumbnail_url)
                except AttributeError:
                    pass

        self._progress_slider.setValue(0)
        self._time_current_lbl.setText("0:00")
        self._time_total_lbl.setText("0:00")

        self._left.setVisible(True)

    def _on_position_changed(self, pos_ms: int, dur_ms: int) -> None:
        if self._seeking:
            return

        if dur_ms > 0:
            slider_value = int((pos_ms / dur_ms) * 1000)
            self._progress_slider.setValue(slider_value)
        else:
            self._progress_slider.setValue(0)

        self._time_current_lbl.setText(self._format_time(pos_ms))
        self._time_total_lbl.setText(self._format_time(dur_ms))

    def _on_shuffle_changed(self, active: bool) -> None:
        if active:
            self._shuffle_btn.setStyleSheet(_ACTIVE_ICON_STYLE)
        else:
            self._shuffle_btn.setStyleSheet(_INACTIVE_ICON_STYLE)

    def _on_repeat_changed(self, mode: RepeatMode) -> None:
        if mode == RepeatMode.NONE:
            self._repeat_btn.setText("\U0001f501")
            self._repeat_btn.setStyleSheet(_INACTIVE_ICON_STYLE)
            self._repeat_btn.setToolTip("Tekrar: Kapali")
        elif mode == RepeatMode.ALL:
            self._repeat_btn.setText("\U0001f501")
            self._repeat_btn.setStyleSheet(_ACTIVE_ICON_STYLE)
            self._repeat_btn.setToolTip("Tekrar: Tumu")
        elif mode == RepeatMode.ONE:
            self._repeat_btn.setText("\U0001f502")
            self._repeat_btn.setStyleSheet(_REPEAT_ONE_STYLE)
            self._repeat_btn.setToolTip("Tekrar: Bir")
        else:
            self._repeat_btn.setText("\U0001f501")
            self._repeat_btn.setStyleSheet(_INACTIVE_ICON_STYLE)

    def _on_slider_pressed(self) -> None:
        self._seeking = True

    def _on_slider_released(self) -> None:
        player = get_player()
        slider_value = self._progress_slider.value()          

        try:
            dur_ms = player.duration_ms
        except AttributeError:
            dur_ms = 0

        if dur_ms > 0:
            seek_ms = int((slider_value / 1000) * dur_ms)
            player.seek(seek_ms)

        self._seeking = False

    def _on_volume_changed(self, value: int) -> None:
        player = get_player()
        player.set_volume(value / 100.0)

        if value == 0:
            self._vol_icon_btn.setText("\U0001f507")          
        elif value < 40:
            self._vol_icon_btn.setText("\U0001f508")        
        elif value < 70:
            self._vol_icon_btn.setText("\U0001f509")           
        else:
            self._vol_icon_btn.setText("\U0001f50a")         

    def _toggle_mute(self) -> None:
        if self._muted:
                     
            self._vol_slider.setValue(self._last_volume)
            self._muted = False
        else:
                  
            current = self._vol_slider.value()
            if current > 0:
                self._last_volume = current
            self._vol_slider.setValue(0)
            self._muted = True

    @staticmethod
    def _format_time(ms: int) -> str:
        if ms < 0:
            ms = 0
        total_seconds = ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
