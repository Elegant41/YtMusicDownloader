import os
import threading
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass, field
from enum import Enum

from PyQt6.QtCore import QObject, QThread, pyqtSignal

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

from core import database

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DEFAULT_DOWNLOAD_DIR = os.path.join(BASE_DIR, "data", "downloads")

QUALITY_PRESETS = {
    "low":      {"bitrate": "64",  "label": "Düşük  (64 kbps)"},
    "medium":   {"bitrate": "128", "label": "Orta  (128 kbps)"},
    "high":     {"bitrate": "256", "label": "Yüksek (256 kbps)"},
    "original": {"bitrate": "320", "label": "Orijinal (En iyi)"},
}

class DownloadStatus(Enum):
    QUEUED      = "queued"
    DOWNLOADING = "downloading"
    PROCESSING  = "processing"
    COMPLETED   = "completed"
    FAILED      = "failed"
    CANCELLED   = "cancelled"

@dataclass
class DownloadTask:
    video_id:      str
    title:         str
    artist:        str
    album:         str
    duration:      int
    thumbnail_url: str
    quality:       str
    playlist_id:   Optional[int]   = None                                 
    yt_playlist_id: str = ""
    status:        DownloadStatus   = DownloadStatus.QUEUED
    progress:      float            = 0.0
    error_msg:     str              = ""
    file_path:     str              = ""
    song_db_id:    int              = 0

class DownloadWorker(QThread):
    progress_updated = pyqtSignal(str, float, str)                                   
    download_complete = pyqtSignal(str, str)                              
    download_failed   = pyqtSignal(str, str)                              

    def __init__(self, task: DownloadTask, download_dir: str, parent=None):
        super().__init__(parent)
        self.task = task
        self.download_dir = download_dir
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        if not YTDLP_AVAILABLE:
            self.download_failed.emit(self.task.video_id, "yt-dlp kurulu değil!")
            return

        try:
            quality = self.task.quality
            bitrate = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["high"])["bitrate"]

            if self.task.playlist_id and self.task.yt_playlist_id:
                out_dir = os.path.join(self.download_dir, "playlists", self.task.yt_playlist_id)
            else:
                out_dir = os.path.join(self.download_dir, "singles")

            os.makedirs(out_dir, exist_ok=True)

            safe_artist = sanitize_filename(self.task.artist or "Unknown")
            safe_title  = sanitize_filename(self.task.title or "Unknown")
            out_file    = os.path.join(out_dir, f"{safe_artist} - {safe_title}.%(ext)s")

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": out_file,
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [self._progress_hook],
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate,
                }],
                "postprocessor_hooks": [self._pp_hook],
                "writethumbnail": False,
                "embedthumbnail": False,
            }

            url = f"https://music.youtube.com/watch?v={self.task.video_id}"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if self._cancelled:
                    self.download_failed.emit(self.task.video_id, "İptal edildi")
                    return
                info = ydl.extract_info(url, download=True)

            mp3_path = self._find_mp3(out_dir, safe_artist, safe_title)

            if mp3_path and os.path.exists(mp3_path):
                                    
                self._write_tags(mp3_path)
                self.download_complete.emit(self.task.video_id, mp3_path)
            else:
                self.download_failed.emit(self.task.video_id, "Dosya bulunamadı")

        except Exception as e:
            if not self._cancelled:
                self.download_failed.emit(self.task.video_id, str(e))

    def _progress_hook(self, d: Dict):
        if self._cancelled:
            raise Exception("İptal edildi")

        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                pct = (downloaded / total) * 85                      
            else:
                pct = 0
            speed = d.get("speed") or 0
            speed_str = f"{speed/1024:.0f} KB/s" if speed else ""
            self.progress_updated.emit(self.task.video_id, pct, f"İndiriliyor {speed_str}")
        elif d["status"] == "finished":
            self.progress_updated.emit(self.task.video_id, 88, "İşleniyor...")

    def _pp_hook(self, d: Dict):
        if d["status"] == "started":
            self.progress_updated.emit(self.task.video_id, 92, "MP3'e dönüştürülüyor...")
        elif d["status"] == "finished":
            self.progress_updated.emit(self.task.video_id, 99, "Tamamlanıyor...")

    def _find_mp3(self, out_dir: str, artist: str, title: str) -> str:
        prefix = f"{artist} - {title}"
        try:
            for f in os.listdir(out_dir):
                if f.startswith(prefix) and f.endswith(".mp3"):
                    return os.path.join(out_dir, f)
                                   
            mp3s = [f for f in os.listdir(out_dir) if f.endswith(".mp3")]
            if mp3s:
                mp3s.sort(key=lambda x: os.path.getmtime(os.path.join(out_dir, x)), reverse=True)
                return os.path.join(out_dir, mp3s[0])
        except Exception:
            pass
        return ""

    def _write_tags(self, mp3_path: str):
        try:
            from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, error as ID3Error
            from mutagen.mp3 import MP3
            import requests

            tags = ID3(mp3_path) if os.path.exists(mp3_path) else ID3()
            try:
                tags = ID3(mp3_path)
            except Exception:
                tags = ID3()

            tags.add(TIT2(encoding=3, text=self.task.title))
            tags.add(TPE1(encoding=3, text=self.task.artist))
            tags.add(TALB(encoding=3, text=self.task.album))

            if self.task.thumbnail_url:
                try:
                    r = requests.get(self.task.thumbnail_url, timeout=8)
                    if r.status_code == 200:
                        tags.add(APIC(
                            encoding=3,
                            mime="image/jpeg",
                            type=3,
                            desc="Cover",
                            data=r.content
                        ))
                except Exception:
                    pass

            tags.save(mp3_path)
        except Exception as e:
            print(f"[Downloader] Tag yazma hatası: {e}")

class DownloadManager(QObject):
    task_added      = pyqtSignal(DownloadTask)
    task_updated    = pyqtSignal(str, float, str, str)                                                
    task_completed  = pyqtSignal(str, str)                                   
    task_failed     = pyqtSignal(str, str)                               
    all_done        = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue: List[DownloadTask] = []
        self._active: Dict[str, DownloadWorker] = {}
        self._completed: Dict[str, DownloadTask] = {}
        self._max_concurrent = int(database.get_setting("max_concurrent_downloads", "3"))
        self._download_dir = database.get_setting("download_dir", "") or DEFAULT_DOWNLOAD_DIR
        self._lock = threading.Lock()

    @property
    def max_concurrent(self):
        return self._max_concurrent

    @max_concurrent.setter
    def max_concurrent(self, value: int):
        self._max_concurrent = value
        database.set_setting("max_concurrent_downloads", str(value))

    @property
    def download_dir(self):
        return self._download_dir

    @download_dir.setter
    def download_dir(self, value: str):
        self._download_dir = value
        database.set_setting("download_dir", value)

    def add_task(self, task: DownloadTask) -> bool:
        if database.song_exists(task.video_id):
            return False
                            
        with self._lock:
            for t in self._queue:
                if t.video_id == task.video_id:
                    return False
            if task.video_id in self._active:
                return False
            self._queue.append(task)

        self.task_added.emit(task)
        self._try_start_next()
        return True

    def add_playlist_tasks(self, tasks: List[DownloadTask]):
        for task in tasks:
            self.add_task(task)

    def cancel_task(self, video_id: str):
        with self._lock:
                               
            if video_id in self._active:
                self._active[video_id].cancel()
                return
                          
            self._queue = [t for t in self._queue if t.video_id != video_id]

    def _try_start_next(self):
        with self._lock:
            while len(self._active) < self._max_concurrent and self._queue:
                task = self._queue.pop(0)
                task.status = DownloadStatus.DOWNLOADING
                worker = DownloadWorker(task, self._download_dir)
                worker.progress_updated.connect(self._on_progress)
                worker.download_complete.connect(self._on_complete)
                worker.download_failed.connect(self._on_failed)
                self._active[task.video_id] = worker
                worker.start()

    def _on_progress(self, video_id: str, progress: float, status_text: str):
        self.task_updated.emit(video_id, progress, status_text, DownloadStatus.DOWNLOADING.value)

    def _on_complete(self, video_id: str, file_path: str):
        task = None
        with self._lock:
            worker = self._active.pop(video_id, None)
            if worker:
                            
                for q_task in self._completed.values():
                    if q_task.video_id == video_id:
                        task = q_task
                        break
                if task is None:
                    task = worker.task

        if task:
            task.status = DownloadStatus.COMPLETED
            task.file_path = file_path
            task.progress = 100
            self._completed[video_id] = task

            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            thumb_path = self._save_thumbnail(task)
            song_id = database.add_song(
                video_id=task.video_id,
                title=task.title,
                artist=task.artist,
                album=task.album,
                duration=task.duration,
                file_path=file_path,
                thumbnail_path=thumb_path,
                quality=task.quality,
                file_size=file_size
            )
            task.song_db_id = song_id

            if task.playlist_id is not None:
                database.add_song_to_playlist(task.playlist_id, song_id)
            else:
                database.add_song_to_playlist(1, song_id)                     

        self.task_updated.emit(video_id, 100, "Tamamlandı", DownloadStatus.COMPLETED.value)
        self.task_completed.emit(video_id, file_path)
        self._try_start_next()
        if not self._active and not self._queue:
            self.all_done.emit()

    def _on_failed(self, video_id: str, error: str):
        with self._lock:
            self._active.pop(video_id, None)
        self.task_updated.emit(video_id, 0, f"Hata: {error}", DownloadStatus.FAILED.value)
        self.task_failed.emit(video_id, error)
        self._try_start_next()

    def _save_thumbnail(self, task: DownloadTask) -> str:
        if not task.thumbnail_url:
            return ""
        try:
            import requests
            cover_dir = os.path.join(self._download_dir, "covers")
            os.makedirs(cover_dir, exist_ok=True)
            path = os.path.join(cover_dir, f"{task.video_id}.jpg")
            if not os.path.exists(path):
                r = requests.get(task.thumbnail_url, timeout=8)
                if r.status_code == 200:
                    with open(path, "wb") as f:
                        f.write(r.content)
            return path
        except Exception:
            return ""

    def get_all_tasks(self) -> List[DownloadTask]:
        with self._lock:
            return list(self._queue) + list(self._active.values())

    def get_completed_tasks(self) -> Dict[str, DownloadTask]:
        return self._completed

    def is_downloading(self, video_id: str) -> bool:
        with self._lock:
            return video_id in self._active or any(t.video_id == video_id for t in self._queue)

def sanitize_filename(name: str) -> str:
    invalid = r'\/:*?"<>|'
    for ch in invalid:
        name = name.replace(ch, "_")
    return name.strip()[:120]

def make_download_task_from_yt(song_data: Dict, quality: str,
                                playlist_id: Optional[int] = None,
                                yt_playlist_id: str = "") -> DownloadTask:
    video_id = song_data.get("videoId", "")
    title    = song_data.get("title", "Unknown")

    artists = song_data.get("artists") or []
    artist  = ", ".join(a.get("name", "") for a in artists) if artists else song_data.get("artist", "")

    album_data = song_data.get("album") or {}
    album  = album_data.get("name", "") if isinstance(album_data, dict) else str(album_data)

    duration = 0
    dur_text = song_data.get("duration") or ""
    if dur_text:
        parts = dur_text.split(":")
        try:
            if len(parts) == 2:
                duration = int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except Exception:
            duration = song_data.get("duration_seconds", 0) or 0

    thumbnails = song_data.get("thumbnails") or []
    thumb_url = ""
    if thumbnails:
        best = max(thumbnails, key=lambda t: t.get("width", 0) if isinstance(t, dict) else 0)
        thumb_url = best.get("url", "") if isinstance(best, dict) else ""

    return DownloadTask(
        video_id=video_id,
        title=title,
        artist=artist,
        album=album,
        duration=duration,
        thumbnail_url=thumb_url,
        quality=quality,
        playlist_id=playlist_id,
        yt_playlist_id=yt_playlist_id,
    )

_manager: Optional[DownloadManager] = None

def get_manager() -> DownloadManager:
    global _manager
    if _manager is None:
        _manager = DownloadManager()
    return _manager
