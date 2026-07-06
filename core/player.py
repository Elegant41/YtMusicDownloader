import os
import random
from typing import Optional, List, Dict
from enum import Enum

from PyQt6.QtCore import QObject, QUrl, pyqtSignal, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from core import database

class RepeatMode(Enum):
    NONE    = "none"
    ONE     = "one"
    ALL     = "all"

class PlayerState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED  = "paused"

class MusicPlayer(QObject):
             
    state_changed       = pyqtSignal(str)                                          
    track_changed       = pyqtSignal(dict)                     
    position_changed    = pyqtSignal(int, int)                                
    volume_changed      = pyqtSignal(float)                    
    queue_changed       = pyqtSignal(list)                          
    shuffle_changed     = pyqtSignal(bool)
    repeat_changed      = pyqtSignal(str)                                 
    error_occurred      = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._player = QMediaPlayer(self)
        self._audio  = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)

        self._queue: List[Dict]       = []
        self._original_queue: List[Dict] = []
        self._current_index: int      = -1
        self._shuffle: bool           = False
        self._repeat: RepeatMode      = RepeatMode.NONE
        self._state: PlayerState      = PlayerState.STOPPED
        self._current_song: Optional[Dict] = None

        self._player.playbackStateChanged.connect(self._on_playback_state)
        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.errorOccurred.connect(self._on_error)

        self._audio.setVolume(0.8)

        self._duration_ms = 0

    def set_queue(self, songs: List[Dict], start_index: int = 0):
        self._original_queue = list(songs)
        if self._shuffle:
            shuffled = list(songs)
            start_song = shuffled.pop(start_index) if 0 <= start_index < len(shuffled) else None
            random.shuffle(shuffled)
            if start_song:
                shuffled.insert(0, start_song)
            self._queue = shuffled
            self._current_index = 0
        else:
            self._queue = list(songs)
            self._current_index = start_index

        self.queue_changed.emit(self._queue)
        self._play_current()

    def add_to_queue(self, song: Dict):
        self._queue.append(song)
        self._original_queue.append(song)
        self.queue_changed.emit(self._queue)

    def insert_next(self, song: Dict):
        insert_pos = self._current_index + 1
        self._queue.insert(insert_pos, song)
        self._original_queue.insert(insert_pos, song)
        self.queue_changed.emit(self._queue)

    def remove_from_queue(self, index: int):
        if 0 <= index < len(self._queue):
            if index < self._current_index:
                self._current_index -= 1
            elif index == self._current_index:
                self._queue.pop(index)
                self._current_index = min(self._current_index, len(self._queue) - 1)
                self.queue_changed.emit(self._queue)
                self._play_current()
                return
            self._queue.pop(index)
            self.queue_changed.emit(self._queue)

    def move_in_queue(self, from_idx: int, to_idx: int):
        if 0 <= from_idx < len(self._queue) and 0 <= to_idx < len(self._queue):
            song = self._queue.pop(from_idx)
            self._queue.insert(to_idx, song)
            if self._current_index == from_idx:
                self._current_index = to_idx
            self.queue_changed.emit(self._queue)

    def clear_queue(self):
        self.stop()
        self._queue.clear()
        self._original_queue.clear()
        self._current_index = -1
        self._current_song = None
        self.queue_changed.emit([])

    def play(self):
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self._player.play()
        elif self._current_index >= 0:
            self._play_current()

    def pause(self):
        self._player.pause()

    def toggle_play_pause(self):
        state = self._player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self.play()

    def stop(self):
        self._player.stop()
        self._state = PlayerState.STOPPED
        self.state_changed.emit("stopped")

    def next(self):
        if not self._queue:
            return
        if self._repeat == RepeatMode.ONE:
            self.seek(0)
            self._player.play()
            return
        if self._current_index < len(self._queue) - 1:
            self._current_index += 1
            self._play_current()
        elif self._repeat == RepeatMode.ALL:
            self._current_index = 0
            self._play_current()

    def previous(self):
        if not self._queue:
            return
                                              
        if self._player.position() > 3000:
            self.seek(0)
            return
        if self._current_index > 0:
            self._current_index -= 1
            self._play_current()
        elif self._repeat == RepeatMode.ALL:
            self._current_index = len(self._queue) - 1
            self._play_current()

    def seek(self, position_ms: int):
        self._player.setPosition(position_ms)

    def seek_percent(self, percent: float):
        if self._duration_ms > 0:
            self.seek(int(self._duration_ms * percent))

    def set_volume(self, volume: float):
        self._audio.setVolume(max(0.0, min(1.0, volume)))
        self.volume_changed.emit(volume)

    def get_volume(self) -> float:
        return self._audio.volume()

    def toggle_shuffle(self):
        self._shuffle = not self._shuffle
        if self._shuffle:
            current = self._current_song
            shuffled = [s for s in self._original_queue if s.get("id") != (current.get("id") if current else None)]
            random.shuffle(shuffled)
            if current:
                shuffled.insert(0, current)
            self._queue = shuffled
            self._current_index = 0
        else:
            current = self._current_song
            self._queue = list(self._original_queue)
            if current:
                for i, s in enumerate(self._queue):
                    if s.get("id") == current.get("id") or s.get("video_id") == current.get("video_id"):
                        self._current_index = i
                        break
        self.shuffle_changed.emit(self._shuffle)
        self.queue_changed.emit(self._queue)

    def toggle_repeat(self):
        modes = [RepeatMode.NONE, RepeatMode.ALL, RepeatMode.ONE]
        current_idx = modes.index(self._repeat)
        self._repeat = modes[(current_idx + 1) % len(modes)]
        self.repeat_changed.emit(self._repeat.value)

    @property
    def current_song(self) -> Optional[Dict]:
        return self._current_song

    @property
    def state(self) -> PlayerState:
        return self._state

    @property
    def is_playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    @property
    def is_shuffled(self) -> bool:
        return self._shuffle

    @property
    def repeat_mode(self) -> RepeatMode:
        return self._repeat

    @property
    def queue(self) -> List[Dict]:
        return self._queue

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def position(self) -> int:
        return self._player.position()

    @property
    def duration(self) -> int:
        return self._player.duration()

    def _play_current(self):
        if not self._queue or self._current_index < 0 or self._current_index >= len(self._queue):
            return

        song = self._queue[self._current_index]
        self._current_song = song

        file_path = song.get("file_path", "")
        if not file_path or not os.path.exists(file_path):
            self.error_occurred.emit(f"Dosya bulunamadı: {file_path}")
            return

        url = QUrl.fromLocalFile(os.path.abspath(file_path))
        self._player.setSource(url)
        self._player.play()

        song_id = song.get("id")
        if song_id:
            database.increment_play_count(song_id)

        self.track_changed.emit(song)

    def _on_playback_state(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._state = PlayerState.PLAYING
            self.state_changed.emit("playing")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._state = PlayerState.PAUSED
            self.state_changed.emit("paused")
        else:
            self._state = PlayerState.STOPPED
            self.state_changed.emit("stopped")

    def _on_position(self, pos_ms: int):
        dur_ms = self._player.duration()
        self.position_changed.emit(pos_ms, dur_ms)

    def _on_duration(self, dur_ms: int):
        self._duration_ms = dur_ms

    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._handle_end_of_track()

    def _handle_end_of_track(self):
        if self._repeat == RepeatMode.ONE:
            self.seek(0)
            self._player.play()
        elif self._current_index < len(self._queue) - 1:
            self._current_index += 1
            self._play_current()
        elif self._repeat == RepeatMode.ALL:
            self._current_index = 0
            self._play_current()
        else:
            self._state = PlayerState.STOPPED
            self.state_changed.emit("stopped")

    def _on_error(self, error, error_string: str):
        self.error_occurred.emit(f"Çalma hatası: {error_string}")

_player: Optional[MusicPlayer] = None

def get_player() -> MusicPlayer:
    global _player
    if _player is None:
        _player = MusicPlayer()
    return _player
