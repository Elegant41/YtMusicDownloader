import json
import hashlib
import time
import os

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                             QDialog, QHBoxLayout, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile

from core.ytmusic_client import get_client, BROWSER_JSON_PATH

ORIGIN = "https://music.youtube.com"

def _compute_sapisidhash(sapisid: str) -> str:
    ts = str(int(time.time()))
    digest = hashlib.sha1(f"{ts} {sapisid} {ORIGIN}".encode()).hexdigest()
    return f"SAPISIDHASH {ts}_{digest}"

class YTLoginBrowser(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("YouTube Music'e Giriş Yap")
        self.resize(1000, 700)

        self.webview = QWebEngineView(self)
        self.profile = QWebEngineProfile.defaultProfile()
        self.cookie_store = self.profile.cookieStore()

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        top_bar = QWidget()
        top_bar.setStyleSheet("background-color: #1a1a1a; border-bottom: 2px solid #FF0000;")
        top_bar.setFixedHeight(60)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(14, 0, 14, 0)

        info_lbl = QLabel(
            "1. YouTube Music hesabınıza giriş yapın.\n"
            "2. Giriş yaptıktan sonra sağdaki butona tıklayın."
        )
        info_lbl.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
        top_layout.addWidget(info_lbl)

        btn_done = QPushButton("✅  Giriş Yaptım, Devam Et")
        btn_done.setStyleSheet("""
            QPushButton {
                background-color: #FF0000;
                color: white;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 22px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #CC0000; }
            QPushButton:pressed { background-color: #990000; }
        """)
                                                       
        btn_done.setAutoDefault(False)
        btn_done.setDefault(False)
        btn_done.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_done.clicked.connect(self._save_cookies_and_accept)
        top_layout.addWidget(btn_done, 0, Qt.AlignmentFlag.AlignRight)

        root_layout.addWidget(top_bar)
        root_layout.addWidget(self.webview)

        self.cookies: dict[str, str] = {}
        self.cookie_store.cookieAdded.connect(self._on_cookie_added)

        self.webview.setUrl(QUrl("https://music.youtube.com/"))

    def _on_cookie_added(self, cookie):
        domain = cookie.domain()
        if "youtube" in domain or "google" in domain:
            try:
                name = cookie.name().data().decode("utf-8", errors="replace")
                value = cookie.value().data().decode("utf-8", errors="replace")
                self.cookies[name] = value
            except Exception:
                pass

    def _save_cookies_and_accept(self):
        if "SAPISID" not in self.cookies:
            QMessageBox.warning(
                self,
                "Giriş Yapılmadı",
                "Lütfen önce YouTube Music hesabınıza giriş yapın!\n"
                "Giriş yapmadan devam edemezsiniz."
            )
            return

        cookie_str = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        sapisid = self.cookies.get("SAPISID", "")

        sapisidhash = _compute_sapisidhash(sapisid)

        headers = {
            "accept": "*/*",
            "accept-language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "authorization": sapisidhash,
            "content-type": "application/json",
            "cookie": cookie_str,
            "origin": ORIGIN,
            "x-origin": ORIGIN,
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        os.makedirs(os.path.dirname(BROWSER_JSON_PATH), exist_ok=True)
        with open(BROWSER_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(headers, f, indent=2)

        self.accept()

class LoginPage(QWidget):
    login_success = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("login_page")
        self._build_ui()

        if get_client().try_connect():
            self.login_success.emit()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._card = QWidget()
        self._card.setObjectName("login_card")
        self._card.setFixedSize(460, 310)
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(18)

        icon_lbl = QLabel("▶")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setFont(QFont("Segoe UI", 48, QFont.Weight.Bold))
        icon_lbl.setStyleSheet("color: #FF0000; margin-bottom: 6px;")
        card_layout.addWidget(icon_lbl)

        title_lbl = QLabel("YT Music Desktop")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #FFFFFF;")
        card_layout.addWidget(title_lbl)

        sub_lbl = QLabel("Kütüphanenize erişmek için hesabınızla giriş yapın.")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("color: #AAAAAA; font-size: 13px; margin-bottom: 14px;")
        card_layout.addWidget(sub_lbl)

        self._btn_login = QPushButton("Tarayıcı ile Giriş Yap")
        self._btn_login.setObjectName("btn_primary")
        self._btn_login.setFixedHeight(46)
        self._btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_login.clicked.connect(self._open_browser_login)
        card_layout.addWidget(self._btn_login)

        main_layout.addWidget(self._card)

    def _open_browser_login(self):
        dialog = YTLoginBrowser(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if get_client().try_connect():
                self.login_success.emit()
            else:
                QMessageBox.critical(
                    self,
                    "Bağlantı Hatası",
                    "Çerezler kaydedildi ancak bağlantı kurulamadı.\n"
                    "Lütfen tekrar giriş yapmayı deneyin."
                )
