import os
import json
import time
from typing import Optional, List, Dict, Any, Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal

try:
    from ytmusicapi import YTMusic
    YTMUSIC_AVAILABLE = True
except ImportError:
    YTMUSIC_AVAILABLE = False

BROWSER_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "browser.json")

class YTMusicWorker(QThread):
    result_ready   = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self._fn     = fn
        self._args   = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))

class YTMusicClient(QObject):
    auth_success          = pyqtSignal(dict)
    auth_failed           = pyqtSignal(str)
    home_loaded           = pyqtSignal(list)
    search_results_ready  = pyqtSignal(list, str)
    playlist_loaded       = pyqtSignal(dict)
    library_loaded        = pyqtSignal(dict)
    history_loaded        = pyqtSignal(list)
    watch_playlist_loaded = pyqtSignal(list)
    song_url_ready        = pyqtSignal(str, str)
    error_occurred        = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
                                                       
        self._yt_anon:       YTMusic = YTMusic() if YTMUSIC_AVAILABLE else None
                                                           
        self._yt_auth:       Optional[YTMusic] = None
        
        self._workers:       List[YTMusicWorker] = []

    def is_authenticated(self) -> bool:
        return os.path.exists(BROWSER_JSON_PATH) and self._yt_auth is not None

    def auth_file_exists(self) -> bool:
        return os.path.exists(BROWSER_JSON_PATH)

    def try_connect(self) -> bool:
        if not self.auth_file_exists() or not YTMUSIC_AVAILABLE:
            return False
        return self._do_connect()

    def _do_connect(self) -> bool:
        try:
                                                                
            self._refresh_sapisidhash()
            self._yt_auth = YTMusic(BROWSER_JSON_PATH)
            print(f"[YTMusic] Browser yetkilendirmesi başarılı.")
            return True
        except Exception as e:
            print(f"[YTMusic] Bağlantı hatası: {e}")
            self._yt_auth = None
            return False

    def _refresh_sapisidhash(self):
        try:
            import hashlib, time, json as _json
            with open(BROWSER_JSON_PATH, "r", encoding="utf-8") as f:
                headers = _json.load(f)

            cookie_str = headers.get("cookie", "")
            sapisid = ""
            for part in cookie_str.split(";"):
                k, _, v = part.strip().partition("=")
                if k == "SAPISID":
                    sapisid = v
                    break

            if not sapisid:
                return                         

            origin = "https://music.youtube.com"
            ts = str(int(time.time()))
            digest = hashlib.sha1(f"{ts} {sapisid} {origin}".encode()).hexdigest()
            headers["authorization"] = f"SAPISIDHASH {ts}_{digest}"
            headers["origin"] = origin
            headers["x-origin"] = origin

            with open(BROWSER_JSON_PATH, "w", encoding="utf-8") as f:
                _json.dump(headers, f, indent=2)
        except Exception as e:
            print(f"[YTMusic] SAPISIDHASH yenileme hatası: {e}")

    def get_user_info(self) -> Dict:
        if not self._yt_auth:
            return {}
        try:
            info = self._yt_auth.get_account_info()
            return info if isinstance(info, dict) else {}
        except Exception as e:
            print(f"[YTMusic] get_user_info: {e}")
            return {}

    def logout(self):
        self._yt_auth = None
        if os.path.exists(BROWSER_JSON_PATH):
            os.remove(BROWSER_JSON_PATH)

    def _run_async(self, fn: Callable, *args, on_result=None, on_error=None, **kwargs):
        worker = YTMusicWorker(fn, *args, **kwargs)
        if on_result:
            worker.result_ready.connect(on_result)
        worker.error_occurred.connect(
            lambda e: (print(f"[YTMusic] Worker hata: {e}"), self.error_occurred.emit(e))
        )
        if on_error:
            worker.error_occurred.connect(on_error)
        worker.finished.connect(
            lambda: self._workers.remove(worker) if worker in self._workers else None
        )
        self._workers.append(worker)
        worker.start()
        return worker

    def load_home(self):
        def _fetch():
            if not self._yt_anon:
                return []
            try:
                                             
                result = self._yt_anon.get_home(limit=6)
                return result if isinstance(result, list) else []
            except Exception as e:
                print(f"[YTMusic] get_home: {e}")
                return []
        return self._run_async(_fetch, on_result=self.home_loaded.emit)

    def search(self, query: str, filter_type: str = "songs", limit: int = 30):
        _filter_map = {
            "songs":               "songs",
            "videos":              "videos",
            "albums":              "albums",
            "artists":             "artists",
            "playlists":           "featured_playlists",
            "community_playlists": "community_playlists",
        }
        yt_filter = _filter_map.get(filter_type, "songs")

        def _fetch():
            if not self._yt_anon:
                return []
            try:
                results = self._yt_anon.search(query, filter=yt_filter, limit=limit)
                return results if isinstance(results, list) else []
            except Exception as e:
                print(f"[YTMusic] search: {e}")
                return []
        return self._run_async(
            _fetch,
            on_result=lambda r: self.search_results_ready.emit(r, filter_type)
        )

    def search_suggestions(self, query: str) -> List[str]:
        if not self._yt_anon:
            return []
        try:
            result = self._yt_anon.get_search_suggestions(query)
            return result if isinstance(result, list) else []
        except Exception:
            return []

    def load_playlist(self, playlist_id: str):
        def _fetch():
            yt_client = self._yt_auth if self._yt_auth else self._yt_anon
            if not yt_client:
                return {}
            try:
                return yt_client.get_playlist(playlist_id, limit=100)
            except Exception as e:
                print(f"[YTMusic] get_playlist ({'auth' if yt_client==self._yt_auth else 'anon'}): {e}")
                if yt_client == self._yt_auth and self._yt_anon:
                    try:
                        return self._yt_anon.get_playlist(playlist_id, limit=100)
                    except:
                        pass
                return {}
        return self._run_async(_fetch, on_result=self.playlist_loaded.emit)

    def load_library(self):
        def _fetch():
            if not self._yt_auth:
                return {"playlists": [], "liked": {}}
            playlists = []
            try:
                playlists = self._yt_auth.get_library_playlists(limit=50) or []
            except Exception as e:
                print(f"[YTMusic] get_library_playlists: {e}")
            liked = {}
            try:
                liked = self._yt_auth.get_liked_songs(limit=100) or {}
            except Exception as e:
                print(f"[YTMusic] get_liked_songs: {e}")
            return {"playlists": playlists, "liked": liked}
        return self._run_async(_fetch, on_result=self.library_loaded.emit)

    def load_history(self):
        def _fetch():
            if not self._yt_auth:
                return []
            try:
                return self._yt_auth.get_history() or []
            except Exception as e:
                print(f"[YTMusic] get_history: {e}")
                return []
        return self._run_async(_fetch, on_result=self.history_loaded.emit)

    def get_watch_playlist(self, video_id: str, playlist_id: str = ""):
        def _fetch():
            if not self._yt_anon:
                return []
            try:
                data = self._yt_anon.get_watch_playlist(
                    videoId=video_id,
                    playlistId=playlist_id or None,
                    limit=25
                )
                return data.get("tracks", []) if isinstance(data, dict) else []
            except Exception as e:
                print(f"[YTMusic] get_watch_playlist: {e}")
                return []
        return self._run_async(_fetch, on_result=self.watch_playlist_loaded.emit)

    def get_album(self, browse_id: str) -> Dict:
        if not self._yt_anon:
            return {}
        try:
            return self._yt_anon.get_album(browse_id) or {}
        except Exception:
            return {}

    def get_artist(self, channel_id: str) -> Dict:
        if not self._yt_anon:
            return {}
        try:
            return self._yt_anon.get_artist(channel_id) or {}
        except Exception:
            return {}

    @property
    def yt(self) -> Optional[YTMusic]:
        return self._yt_auth if self._yt_auth else self._yt_anon

_client: Optional[YTMusicClient] = None

def get_client() -> YTMusicClient:
    global _client
    if _client is None:
        _client = YTMusicClient()
    return _client
