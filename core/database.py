import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "database.db")

def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS downloaded_songs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id        TEXT    UNIQUE NOT NULL,
            title           TEXT    NOT NULL,
            artist          TEXT,
            album           TEXT,
            duration        INTEGER DEFAULT 0,
            file_path       TEXT,
            thumbnail_path  TEXT,
            quality         TEXT    DEFAULT 'high',
            downloaded_at   TEXT    DEFAULT (datetime('now')),
            play_count      INTEGER DEFAULT 0,
            file_size       INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS local_playlists (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL,
            description     TEXT    DEFAULT '',
            cover_path      TEXT,
            created_at      TEXT    DEFAULT (datetime('now')),
            updated_at      TEXT    DEFAULT (datetime('now')),
            yt_playlist_id  TEXT,
            is_auto         INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS playlist_songs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            playlist_id INTEGER NOT NULL,
            song_id     INTEGER NOT NULL,
            position    INTEGER DEFAULT 0,
            FOREIGN KEY (playlist_id) REFERENCES local_playlists(id) ON DELETE CASCADE,
            FOREIGN KEY (song_id)     REFERENCES downloaded_songs(id) ON DELETE CASCADE,
            UNIQUE (playlist_id, song_id)
        );

        CREATE TABLE IF NOT EXISTS play_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id     INTEGER NOT NULL,
            played_at   TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (song_id) REFERENCES downloaded_songs(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        INSERT OR IGNORE INTO settings VALUES ('download_dir', '');
        INSERT OR IGNORE INTO settings VALUES ('default_quality', 'high');
        INSERT OR IGNORE INTO settings VALUES ('max_concurrent_downloads', '3');
        INSERT OR IGNORE INTO settings VALUES ('theme', 'dark');
        INSERT OR IGNORE INTO settings VALUES ('language', 'tr');
    """)

    cur.execute(
        "INSERT OR IGNORE INTO local_playlists (id, name, description, is_auto) VALUES (1, 'Solo İndirilenler', 'Tekil olarak indirilen şarkılar', 1)"
    )

    conn.commit()
    conn.close()

def add_song(video_id: str, title: str, artist: str = "", album: str = "",
             duration: int = 0, file_path: str = "", thumbnail_path: str = "",
             quality: str = "high", file_size: int = 0) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO downloaded_songs
            (video_id, title, artist, album, duration, file_path, thumbnail_path, quality, file_size)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (video_id, title, artist, album, duration, file_path, thumbnail_path, quality, file_size))
    song_id = cur.lastrowid
    conn.commit()
    conn.close()
    return song_id

def get_song_by_video_id(video_id: str) -> Optional[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM downloaded_songs WHERE video_id = ?", (video_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_songs() -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM downloaded_songs ORDER BY downloaded_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_song_path(song_id: int, file_path: str, thumbnail_path: str = "", file_size: int = 0):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE downloaded_songs SET file_path=?, thumbnail_path=?, file_size=? WHERE id=?",
        (file_path, thumbnail_path, file_size, song_id)
    )
    conn.commit()
    conn.close()

def increment_play_count(song_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE downloaded_songs SET play_count = play_count + 1 WHERE id = ?", (song_id,))
    cur.execute("INSERT INTO play_history (song_id) VALUES (?)", (song_id,))
    conn.commit()
    conn.close()

def delete_song(song_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM downloaded_songs WHERE id = ?", (song_id,))
    conn.commit()
    conn.close()

def song_exists(video_id: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, file_path FROM downloaded_songs WHERE video_id = ?", (video_id,))
    row = cur.fetchone()
    conn.close()
    if row and os.path.exists(row["file_path"]):
        return True
    return False

def create_playlist(name: str, description: str = "", yt_playlist_id: str = "",
                    cover_path: str = "") -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO local_playlists (name, description, yt_playlist_id, cover_path)
        VALUES (?, ?, ?, ?)
    """, (name, description, yt_playlist_id, cover_path))
    playlist_id = cur.lastrowid
    conn.commit()
    conn.close()
    return playlist_id

def get_all_playlists() -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT lp.*, COUNT(ps.song_id) as song_count
        FROM local_playlists lp
        LEFT JOIN playlist_songs ps ON lp.id = ps.playlist_id
        GROUP BY lp.id
        ORDER BY lp.updated_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_playlist_by_id(playlist_id: int) -> Optional[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM local_playlists WHERE id = ?", (playlist_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_playlist_songs(playlist_id: int) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ds.*, ps.position
        FROM playlist_songs ps
        JOIN downloaded_songs ds ON ps.song_id = ds.id
        WHERE ps.playlist_id = ?
        ORDER BY ps.position ASC
    """, (playlist_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_song_to_playlist(playlist_id: int, song_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT MAX(position) FROM playlist_songs WHERE playlist_id = ?", (playlist_id,))
    max_pos = cur.fetchone()[0] or 0
    try:
        cur.execute(
            "INSERT OR IGNORE INTO playlist_songs (playlist_id, song_id, position) VALUES (?, ?, ?)",
            (playlist_id, song_id, max_pos + 1)
        )
        cur.execute("UPDATE local_playlists SET updated_at = datetime('now') WHERE id = ?", (playlist_id,))
        conn.commit()
    except Exception:
        pass
    conn.close()

def remove_song_from_playlist(playlist_id: int, song_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM playlist_songs WHERE playlist_id = ? AND song_id = ?", (playlist_id, song_id))
    conn.commit()
    conn.close()

def delete_playlist(playlist_id: int):
    if playlist_id == 1:
        return                               
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM playlist_songs WHERE playlist_id = ?", (playlist_id,))
    cur.execute("DELETE FROM local_playlists WHERE id = ?", (playlist_id,))
    conn.commit()
    conn.close()

def rename_playlist(playlist_id: int, new_name: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE local_playlists SET name = ?, updated_at = datetime('now') WHERE id = ?",
                (new_name, playlist_id))
    conn.commit()
    conn.close()

def update_playlist_cover(playlist_id: int, cover_path: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE local_playlists SET cover_path = ? WHERE id = ?", (cover_path, playlist_id))
    conn.commit()
    conn.close()

def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_recently_played(limit: int = 20) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ds.*, MAX(ph.played_at) as last_played
        FROM play_history ph
        JOIN downloaded_songs ds ON ph.song_id = ds.id
        WHERE ds.file_path != '' AND ds.file_path IS NOT NULL
        GROUP BY ds.id
        ORDER BY last_played DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def search_local_songs(query: str) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    q = f"%{query}%"
    cur.execute("""
        SELECT * FROM downloaded_songs
        WHERE title LIKE ? OR artist LIKE ? OR album LIKE ?
        ORDER BY play_count DESC
    """, (q, q, q))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
