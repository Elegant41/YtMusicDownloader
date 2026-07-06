import sys
import os

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    pass

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QFontDatabase, QIcon

from core import database

def load_stylesheet(app: QApplication):
    qss_path = os.path.join(BASE_DIR, "resources", "style.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    else:
        print(f"[UYARI] style.qss bulunamadı: {qss_path}")

def check_dependencies() -> bool:
    missing = []

    try:
        import PyQt6
    except ImportError:
        missing.append("PyQt6")

    try:
        import ytmusicapi
    except ImportError:
        missing.append("ytmusicapi")

    try:
        import yt_dlp
    except ImportError:
        missing.append("yt-dlp")

    try:
        import mutagen
    except ImportError:
        missing.append("mutagen")

    if missing:
        print(f"[HATA] Eksik bağımlılıklar: {', '.join(missing)}")
        print("Çözüm: pip install -r requirements.txt")
        return False
    return True

def check_ffmpeg() -> bool:
    import shutil
    return shutil.which("ffmpeg") is not None

def main():
                   
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("YT Music Desktop")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("YTMusicDesktop")

    app.setStyle("Fusion")

    from PyQt6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor("#0F0F0F"))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor("#EFEFEF"))
    palette.setColor(QPalette.ColorRole.Base,            QColor("#1A1A1A"))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor("#141414"))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor("#1A1A1A"))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor("#EFEFEF"))
    palette.setColor(QPalette.ColorRole.Text,            QColor("#EFEFEF"))
    palette.setColor(QPalette.ColorRole.Button,          QColor("#1A1A1A"))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor("#EFEFEF"))
    palette.setColor(QPalette.ColorRole.BrightText,      QColor("#FF0033"))
    palette.setColor(QPalette.ColorRole.Link,            QColor("#FF0033"))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor("#FF0033"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)

    load_stylesheet(app)

    database.init_db()

    for d in [
        os.path.join(BASE_DIR, "data", "downloads", "playlists"),
        os.path.join(BASE_DIR, "data", "downloads", "singles"),
        os.path.join(BASE_DIR, "data", "downloads", "covers"),
        os.path.join(BASE_DIR, "data", "cache",     "thumbnails"),
    ]:
        os.makedirs(d, exist_ok=True)

    from core.ytmusic_client import get_client
    client = get_client()

    if not check_ffmpeg():
        print("[UYARI] FFmpeg bulunamadı! MP3 indirme çalışmayabilir.")

    _window = None                                              

    def _open_main_window():
        nonlocal _window
        try:
            from ui.main_window import MainWindow
            _window = MainWindow()
            _window.show()
        except Exception as e:
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Hata", f"Ana pencere açılamadı:\n{e}")

    if client.auth_file_exists() and client.try_connect():
        _open_main_window()
    else:
        from ui.login_page import LoginPage
        _login = LoginPage()

        def on_login_success():
            _login.hide()
            _open_main_window()

        _login.login_success.connect(on_login_success)
        _login.setMinimumSize(700, 600)
        _login.resize(900, 650)
        _login.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
