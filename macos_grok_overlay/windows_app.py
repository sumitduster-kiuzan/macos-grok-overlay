import sys
import threading
from pathlib import Path
from typing import Optional

try:
    import keyboard
except Exception as exc:  # pragma: no cover - optional dependency on Windows
    keyboard = None
    _KEYBOARD_ERROR = exc
else:
    _KEYBOARD_ERROR = None

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAction,
    QApplication,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from .constants import APP_TITLE, WEBSITE, LOGO_WHITE_PATH
from .health_checks import LOG_DIR
from . import windows_launcher


HOTKEY_FILE = LOG_DIR / "windows_hotkey.txt"
DEFAULT_HOTKEY = "alt+space"


def _load_hotkey() -> str:
    if HOTKEY_FILE.exists():
        value = HOTKEY_FILE.read_text(encoding="utf-8").strip()
        if value:
            return value
    return DEFAULT_HOTKEY


def _save_hotkey(combo: str) -> None:
    HOTKEY_FILE.write_text(combo.strip(), encoding="utf-8")


class WindowsOverlayWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} Overlay")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.resize(640, 720)
        self.webview = QWebEngineView(self)
        self.webview.setUrl(QUrl(WEBSITE))
        self.setCentralWidget(self.webview)
        self.webview.loadFinished.connect(self._focus_textarea)
        self.tray_icon: Optional[QSystemTrayIcon] = None

    def _focus_textarea(self, ok: bool) -> None:
        if ok:
            script = "document.querySelector('textarea')?.focus();"
            self.webview.page().runJavaScript(script)

    def navigate_home(self) -> None:
        self.webview.setUrl(QUrl(WEBSITE))

    def clear_cache(self) -> None:
        profile = self.webview.page().profile()
        profile.clearHttpCache()
        profile.clearAllVisitedLinks()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt signature
        # Hide instead of closing so the tray icon keeps running.
        event.ignore()
        self.hide()


class WindowsOverlayApp:
    def __init__(self) -> None:
        QApplication.setQuitOnLastWindowClosed(False)
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.window = WindowsOverlayWindow()
        self.hotkey_handle = None
        self.hotkey = _load_hotkey()
        self._hotkey_thread: Optional[threading.Thread] = None
        self.tray = self._create_tray_icon()
        self._register_hotkey(self.hotkey)
        self.app.aboutToQuit.connect(self.cleanup)

    def _create_tray_icon(self) -> QSystemTrayIcon:
        icon_path = Path(__file__).resolve().parent / LOGO_WHITE_PATH
        icon = QIcon(str(icon_path))
        tray = QSystemTrayIcon(icon, self.app)
        menu = QMenu()

        show_action = QAction(f"Show {APP_TITLE}", self.app)
        show_action.triggered.connect(self.show_window)
        menu.addAction(show_action)

        hide_action = QAction(f"Hide {APP_TITLE}", self.app)
        hide_action.triggered.connect(self.hide_window)
        menu.addAction(hide_action)

        home_action = QAction("Home", self.app)
        home_action.triggered.connect(self.window.navigate_home)
        menu.addAction(home_action)

        clear_action = QAction("Clear Web Cache", self.app)
        clear_action.triggered.connect(self.window.clear_cache)
        menu.addAction(clear_action)

        trigger_action = QAction("Set New Trigger", self.app)
        trigger_action.triggered.connect(self._set_new_trigger)
        trigger_action.setEnabled(keyboard is not None)
        menu.addAction(trigger_action)

        install_action = QAction("Install Autolauncher", self.app)
        install_action.triggered.connect(lambda: windows_launcher.install_startup())
        menu.addAction(install_action)

        uninstall_action = QAction("Uninstall Autolauncher", self.app)
        uninstall_action.triggered.connect(lambda: windows_launcher.uninstall_startup())
        menu.addAction(uninstall_action)

        quit_action = QAction("Quit", self.app)
        quit_action.triggered.connect(self.app.quit)
        menu.addAction(quit_action)

        tray.setContextMenu(menu)
        tray.setToolTip(f"{APP_TITLE} Overlay")
        tray.show()
        self.window.tray_icon = tray
        return tray

    def _register_hotkey(self, combo: str) -> None:
        if keyboard is None:
            if _KEYBOARD_ERROR:
                print(f"'keyboard' dependency unavailable: {_KEYBOARD_ERROR}")
            return
        if self.hotkey_handle is not None:
            keyboard.remove_hotkey(self.hotkey_handle)
        try:
            self.hotkey_handle = keyboard.add_hotkey(combo, self.toggle_window)
            self.hotkey = combo
            _save_hotkey(combo)
            print(f"Registered hotkey: {combo}")
        except Exception as exc:  # pragma: no cover - depends on OS capabilities
            print(f"Failed to register hotkey '{combo}': {exc}")
            self.hotkey_handle = None

    def _set_new_trigger(self) -> None:
        if keyboard is None:
            QMessageBox.warning(
                self.window,
                "Set Trigger",
                "The 'keyboard' dependency is unavailable. Install it to set a custom trigger.",
            )
            return
        if self._hotkey_thread and self._hotkey_thread.is_alive():
            return

        self.tray.showMessage(
            f"{APP_TITLE} Overlay",
            "Press the new key combination now…",
            QSystemTrayIcon.Information,
            4000,
        )

        def worker():
            try:
                combo = keyboard.read_hotkey(suppress=False)
            except Exception as exc:  # pragma: no cover
                print(f"Failed to read new hotkey: {exc}")
                return
            self._register_hotkey(combo)
            self.tray.showMessage(
                f"{APP_TITLE} Overlay",
                f"New trigger set to {combo}",
                QSystemTrayIcon.Information,
                4000,
            )

        self._hotkey_thread = threading.Thread(target=worker, daemon=True)
        self._hotkey_thread.start()

    def show_window(self) -> None:
        self.window.show()
        self.window.activateWindow()
        self.window.raise_()
        self.window._focus_textarea(True)  # focus input

    def hide_window(self) -> None:
        self.window.hide()

    def toggle_window(self) -> None:
        if self.window.isVisible():
            self.hide_window()
        else:
            self.show_window()

    def cleanup(self) -> None:
        if keyboard is not None and self.hotkey_handle is not None:
            keyboard.remove_hotkey(self.hotkey_handle)
            self.hotkey_handle = None

    def run(self) -> None:
        self.show_window()
        self.app.exec()
