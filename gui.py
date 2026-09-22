"""
gui.py
------
Головний GUI Tlumach Kotoba на PySide6 (Qt).

Структура вкладки «Новий урок» — три кроки (1 Створи урок →
2 Налаштуй голоси → 3 Практикуйся) замість довгої стрічки карток:
наступний крок стає доступним лише тоді, коли попередній завершено.
Статуси й попередження показуються прямо на місці (inline), а не у
спливаючих вікнах; спливаючі вікна лишились тільки для підтверджень
(замінити урок, перезаписати файл, видалити) і для помилок.

Розмір вікна: відкривається в оптимальному розмірі BASE_WIDTH ×
BASE_HEIGHT (не на весь екран), обмеженому доступною площею екрана;
розмір і позиція запам'ятовуються. Вміст обмежений по ширині
(CONTENT_MAX) і розташований по центру — розтягування вікна не
розповзає інтерфейс. Замість розтягування — масштаб (Ctrl + / Ctrl − /
Ctrl 0 або кнопки в шапці): усі розміри в QSS і відступи макетів
перераховуються з коефіцієнтом, вікно пропорційно змінює розмір у
межах екрана. Масштабування самої Windows Qt 6 враховує автоматично.

Бізнес-логіка (SessionManager, DatabaseManager, ExerciseGenerator,
AudioAssembler, AudioPlayer, content.py, settings.py) цим модулем НЕ
змінюється — він лише показує її.

Довгі операції (TTS + FFmpeg) — в AudioWorker(QThread) із сигналами;
Qt забороняє чіпати віджети з фонового потоку.
"""

from __future__ import annotations

import base64
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QByteArray, QCoreApplication, QStandardPaths, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QDesktopServices,
    QFontDatabase,
    QGuiApplication,
    QIcon,
    QKeySequence,
    QPixmap,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .audio import AudioAssembler, AudioError
from .content import (
    ABOUT_TEXT,
    ABOUT_TITLE,
    COUNT_FORMS,
    JSON_SECTION_TITLE,
    MESSAGES,
    METHODOLOGY_TEXT,
    METHODOLOGY_TITLE,
    MY_LESSONS_HINT,
    NAV_LABELS,
    RESTART_NOTICE,
    UI_STRINGS,
)
from .database import DatabaseManager
from .exercises import AudioSettings, ExerciseGenerator, MissingVoiceError
from .japanese_reading import JapaneseReadingProvider
from .languages import TARGET_LANGUAGES, code_by_label, get_language, language_labels
from .parser import find_glued_speaker_marker
from .player import AudioPlayer
from .session import LessonSession, SessionManager
from .settings import load_settings, save_settings
from .tts import EDGE_TTS_AVAILABLE, TTSManager
from .wizard import PromptWizard

APP_NAME = "Tlumach Kotoba"
# Вбудовані ресурси (приклади, іконки, інфографіка). У зібраному .exe
# PyInstaller розпаковує їх у тимчасову теку sys._MEIPASS — читати звідти
# можна, а ЗАПИСУВАТИ туди нічого не можна: Windows видаляє цю теку
# після закриття програми.
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
SOURCE_DIR = Path(__file__).resolve().parent.parent
ICON_PATH = BASE_DIR / "assets" / "icon.ico"
FONTS_DIR = BASE_DIR / "assets" / "fonts"
ICONS_DIR = BASE_DIR / "assets" / "icons"
CHEVRON_DOWN_PATH = ICONS_DIR / "chevron_down.png"
INFOGRAPHIC_PATH = BASE_DIR / "assets" / "images" / "infographic.png"

# Постійні дані — визначаються в init_paths() після створення QApplication
# (QStandardPaths потребує назви застосунку). Значення нижче — лише
# заглушки до виклику init_paths().
DATA_DIR = SOURCE_DIR
OUT_DIR = SOURCE_DIR / "output"
TEMP_DIR = SOURCE_DIR / "temporary"
DB_PATH = SOURCE_DIR / "studio.db"
SETTINGS_PATH = SOURCE_DIR / "settings.json"


def init_paths() -> None:
    """Визначає, де програма зберігає те, що створює сама.

    - Уроки й налаштування: системна тека даних застосунку —
      Windows %APPDATA%\\Tlumach Kotoba, macOS ~/Library/Application
      Support/Tlumach Kotoba, Linux ~/.local/share/Tlumach Kotoba.
    - MP3: «Музика/Tlumach Kotoba» — звичне місце для аудіо.
    - Змінна середовища APP_DATA_DIR (для розробки й тестів) кладе все
      в одну вказану теку.

    Одноразово переносить уроки й налаштування, створені раніше при
    запуску з вихідного коду (тоді вони лежали поруч із кодом)."""
    global DATA_DIR, OUT_DIR, TEMP_DIR, DB_PATH, SETTINGS_PATH
    override = os.environ.get("APP_DATA_DIR")
    if override:
        DATA_DIR = Path(override)
        OUT_DIR = DATA_DIR / "output"
    else:
        app_data = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        DATA_DIR = Path(app_data) if app_data else Path.home() / ".tlumach-kotoba"
        music = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MusicLocation)
        OUT_DIR = Path(music) / APP_NAME if music else DATA_DIR / "output"
    TEMP_DIR = DATA_DIR / "temporary"
    DB_PATH = DATA_DIR / "studio.db"
    SETTINGS_PATH = DATA_DIR / "settings.json"
    for folder in (DATA_DIR, OUT_DIR, TEMP_DIR):
        folder.mkdir(parents=True, exist_ok=True)

    if not getattr(sys, "frozen", False):
        for name, target in (("studio.db", DB_PATH), ("settings.json", SETTINGS_PATH)):
            legacy = SOURCE_DIR / name
            if legacy.exists() and not target.exists() and legacy.resolve() != target.resolve():
                try:
                    shutil.copy2(legacy, target)
                except OSError:
                    pass  # перенесення не критичне — програма просто почне з порожньої історії

# --- Розміри (при масштабі 100%) ---------------------------------------
BASE_WIDTH = 1120      # оптимальний розмір вікна при першому запуску
BASE_HEIGHT = 720      # вміщується навіть на ноутбуці 1366×768
MIN_WIDTH = 900
MIN_HEIGHT = 600
CONTENT_MAX = 1008     # максимальна ширина робочої колонки
READING_MAX = 720      # ширина колонки тексту методології
ZOOM_LEVELS = [0.9, 1.0, 1.1, 1.25, 1.5]

# --- Палітра (узгоджена з дизайн-макетом) -------------------------------
COLOR_INK = "#1E2F4D"
COLOR_INK_HOVER = "#16233B"
COLOR_BG = "#EEF0F3"
COLOR_CARD = "#FFFFFF"
COLOR_BORDER = "#E1E4E9"
COLOR_TEXT = "#1B2430"
COLOR_TEXT_MUTED = "#6B7686"
COLOR_SECONDARY_BG = "#F4F5F7"
COLOR_SUCCESS = "#1A7F37"

AVATAR_COLORS = [
    ("#F9E3E7", "#A33A55"),
    ("#E2EAF6", "#2F4F80"),
    ("#E4F2E7", "#2E6B3F"),
    ("#F4ECDD", "#7A5A1E"),
]

UI_LANGUAGE_CODES = ("uk", "en")

EXAMPLE_FILES = {
    "english": BASE_DIR / "examples" / "demo_lesson_english.txt",
    "japanese": BASE_DIR / "examples" / "demo_lesson_japanese.txt",
    "french": BASE_DIR / "examples" / "demo_lesson_french.txt",
    "spanish": BASE_DIR / "examples" / "demo_lesson_spanish.txt",
}

RATES = ["-30%", "-20%", "-10%", "0%", "+10%"]
DEFAULT_RATE = "-10%"
PAUSE_VALUES = ["0.5", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
DEFAULT_PAUSE = "2"

MODES = [
    ("full_dialogue", "mode_full_dialogue", "mode_full_desc"),
    ("shadowing", "mode_shadowing_short", "mode_shadowing_desc"),
    ("phrase_trainer", "mode_phrases", "mode_phrases_desc"),
    ("recall", "mode_recall", "mode_recall_desc"),
]


def load_app_fonts() -> tuple[str, str]:
    """Вантажить власні .ttf з assets/fonts/, якщо вони там є (IBM Plex
    Sans — основний текст, Fraunces — назва застосунку). Якщо файлів
    немає — системні Segoe UI / Georgia; застосунок працює однаково."""
    body, title = "Segoe UI", "Georgia"
    if FONTS_DIR.exists():
        for font_file in FONTS_DIR.glob("*.ttf"):
            font_id = QFontDatabase.addApplicationFont(str(font_file))
            if font_id == -1:
                continue
            families = QFontDatabase.applicationFontFamilies(font_id)
            if not families:
                continue
            stem = font_file.stem.lower()
            if "plex" in stem:
                body = families[0]
            elif "fraunces" in stem:
                title = families[0]
    return body, title


def build_stylesheet(scale: float, body_font: str, title_font: str) -> str:
    """QSS усього застосунку. Кожен розмір проходить через px() — саме
    так працює масштаб інтерфейсу: при зміні масштабу стилі просто
    генеруються заново з іншим коефіцієнтом."""

    def px(v: float) -> str:
        return f"{max(1, round(v * scale))}px"

    chev = CHEVRON_DOWN_PATH.as_posix()
    return f"""
    QWidget {{ color: {COLOR_TEXT}; font-family: "{body_font}"; font-size: {px(13)}; }}
    QMainWindow, QDialog, QWidget#mainBackground {{ background-color: {COLOR_BG}; }}
    QLabel {{ background: transparent; }}
    QToolTip {{ background: {COLOR_TEXT}; color: #FFFFFF; border: none; padding: {px(5)} {px(8)}; border-radius: {px(6)}; }}

    QFrame#appbar {{ background: {COLOR_CARD}; border: none; border-bottom: 1px solid {COLOR_BORDER}; }}
    QLabel#brand {{ font-family: "{title_font}", "Georgia", serif; font-size: {px(21)}; font-weight: 700; color: {COLOR_INK}; }}
    QLabel#tagline, QLabel#footer {{ color: {COLOR_TEXT_MUTED}; font-size: {px(12)}; }}
    QFrame#footerBar {{ background: transparent; border-top: 1px solid {COLOR_BORDER}; }}

    QPushButton {{ background: {COLOR_SECONDARY_BG}; color: #2E3746; border: 1px solid {COLOR_BORDER};
                   border-radius: {px(9)}; padding: {px(8)} {px(15)}; font-size: {px(13.5)}; }}
    QPushButton:hover {{ border-color: #C4CAD3; }}
    QPushButton:pressed {{ background: {COLOR_BORDER}; }}
    QPushButton:disabled {{ color: #A0A8B5; }}
    QPushButton#primary {{ background: {COLOR_INK}; color: #FFFFFF; border: 1px solid {COLOR_INK}; font-weight: 600; }}
    QPushButton#primary:hover {{ background: {COLOR_INK_HOVER}; }}
    QPushButton#primary:disabled {{ background: #9AA3B2; border-color: #9AA3B2; color: #F1F3F6; }}
    QPushButton#ghost {{ background: transparent; border-color: transparent; color: {COLOR_INK}; }}
    QPushButton#ghost:hover {{ background: {COLOR_SECONDARY_BG}; }}

    QPushButton#navButton {{ background: transparent; border: none; border-radius: {px(8)};
                             padding: {px(7)} {px(13)}; color: #3A4354; font-size: {px(13.5)}; }}
    QPushButton#navButton:hover {{ background: {COLOR_SECONDARY_BG}; }}
    QPushButton#navButton:checked {{ background: {COLOR_INK}; color: #FFFFFF; font-weight: 600; }}

    QFrame#zoomBox {{ background: {COLOR_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: {px(8)}; }}
    QPushButton#zoomBtn {{ background: transparent; border: none; padding: 0; min-width: {px(26)}; min-height: {px(26)};
                           font-size: {px(15)}; color: #3A4354; border-radius: {px(6)}; }}
    QPushButton#zoomBtn:hover {{ background: {COLOR_SECONDARY_BG}; }}
    QLabel#zoomLabel {{ font-size: {px(12)}; min-width: {px(40)}; color: #3A4354; }}

    QPushButton#seg {{ background: {COLOR_SECONDARY_BG}; border: 1px solid {COLOR_BORDER}; border-radius: 0;
                       padding: {px(6)} {px(11)}; font-size: {px(12)}; color: #5B6574; font-weight: 400; }}
    QPushButton#seg[size="lg"] {{ padding: {px(8)} {px(14)}; font-size: {px(13)}; }}
    QPushButton#seg[pos="first"] {{ border-top-left-radius: {px(8)}; border-bottom-left-radius: {px(8)}; }}
    QPushButton#seg[pos="mid"], QPushButton#seg[pos="last"] {{ border-left: none; }}
    QPushButton#seg[pos="last"] {{ border-top-right-radius: {px(8)}; border-bottom-right-radius: {px(8)}; }}
    QPushButton#seg:hover {{ background: #EAEDF1; }}
    QPushButton#seg:checked {{ background: {COLOR_INK}; color: #FFFFFF; border-color: {COLOR_INK}; font-weight: 600; }}

    QFrame#stepItem {{ background: transparent; }}
    QLabel#stepDot {{ min-width: {px(24)}; max-width: {px(24)}; min-height: {px(24)}; max-height: {px(24)};
                      border-radius: {px(12)}; background: #E1E4E9; color: {COLOR_TEXT_MUTED};
                      font-size: {px(12)}; font-weight: 600; }}
    QLabel#stepDot[state="active"] {{ background: {COLOR_INK}; color: #FFFFFF; }}
    QLabel#stepDot[state="done"] {{ background: #DDEFE2; color: {COLOR_SUCCESS}; }}
    QLabel#stepText {{ font-size: {px(13)}; color: {COLOR_TEXT_MUTED}; }}
    QLabel#stepText[state="active"] {{ color: {COLOR_TEXT}; font-weight: 600; }}
    QLabel#stepText[state="done"] {{ color: {COLOR_TEXT}; }}
    QLabel#stepText[state="locked"] {{ color: #A7AFBB; }}
    QFrame#stepBar {{ background: #DDE1E6; border: none; min-height: 2px; max-height: 2px;
                      min-width: {px(40)}; max-width: {px(90)}; }}
    QFrame#stepBar[state="done"] {{ background: #9FCFAE; }}

    QFrame#card {{ background: {COLOR_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: {px(14)}; }}
    QLabel#cardTitle {{ font-size: {px(17)}; font-weight: 600; }}
    QLabel#cardTitleSm {{ font-size: {px(15)}; font-weight: 600; }}
    QLabel#cardSub {{ color: {COLOR_TEXT_MUTED}; font-size: {px(13)}; }}
    QLabel#fieldLabel {{ color: {COLOR_TEXT_MUTED}; font-size: {px(12)}; }}
    QLabel#hint {{ color: #8891A0; font-size: {px(12)}; }}
    QLabel#chip {{ background: #F1F3F6; color: #5B6574; border-radius: {px(10)}; padding: {px(3)} {px(10)}; font-size: {px(12)}; }}
    QLabel#noteOk {{ background: #EEF7F1; color: #1C5D31; border-radius: {px(10)}; padding: {px(9)} {px(13)}; font-size: {px(13)}; }}
    QLabel#noteWarn {{ background: #FDF4E4; color: #77500E; border-radius: {px(10)}; padding: {px(9)} {px(13)}; font-size: {px(13)}; }}

    QFrame#spkCard {{ background: {COLOR_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: {px(12)}; }}
    QFrame#spkCard[missing="true"] {{ background: #FFFCF6; border: 1px solid #F0D39A; }}
    QLabel#spkName {{ font-size: {px(15)}; font-weight: 600; }}
    QLabel#avatar {{ min-width: {px(40)}; max-width: {px(40)}; min-height: {px(40)}; max-height: {px(40)};
                     border-radius: {px(20)}; font-size: {px(15)}; font-weight: 600; }}

    QFrame#modeCard {{ background: #FAFBFC; border: 1px solid {COLOR_BORDER}; border-radius: {px(12)}; }}
    QFrame#modeCard:hover {{ border: 1px solid #C4CAD3; }}
    QFrame#modeCard[selected="true"] {{ background: #F3F5F9; border: 2px solid {COLOR_INK}; }}
    QLabel#modeTitle {{ font-size: {px(14)}; font-weight: 600; }}
    QLabel#modeDesc {{ font-size: {px(12.5)}; color: #5B6574; }}

    QFrame#progressBox {{ background: {COLOR_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: {px(12)}; }}
    QProgressBar {{ background: #E8EBEF; border: none; border-radius: {px(3)}; min-height: {px(6)}; max-height: {px(6)}; }}
    QProgressBar::chunk {{ background: {COLOR_INK}; border-radius: {px(3)}; }}

    QPushButton#round {{ min-width: {px(40)}; max-width: {px(40)}; min-height: {px(40)}; max-height: {px(40)};
                         border-radius: {px(20)}; padding: 0; font-size: {px(13)}; }}
    QPushButton#roundPlay {{ min-width: {px(40)}; max-width: {px(40)}; min-height: {px(40)}; max-height: {px(40)};
                             border-radius: {px(20)}; padding: 0; font-size: {px(13)};
                             background: {COLOR_INK}; color: #FFFFFF; border: 1px solid {COLOR_INK}; }}
    QPushButton#roundPlay:hover {{ background: {COLOR_INK_HOVER}; }}
    QPushButton#roundPlay:disabled, QPushButton#round:disabled {{ background: #E8EBEF; border-color: #E8EBEF; color: #A0A8B5; }}
    QLabel#fileName {{ font-size: {px(14)}; font-weight: 500; }}

    QLineEdit, QComboBox, QPlainTextEdit, QListWidget {{
        background: #FAFBFC; border: 1px solid #D9DDE3; border-radius: {px(9)};
        padding: {px(7)} {px(11)}; font-size: {px(14)};
        selection-background-color: {COLOR_INK}; selection-color: #FFFFFF; }}
    QPlainTextEdit {{ font-size: {px(13.5)}; }}
    QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus {{ border: 1px solid {COLOR_INK}; }}
    QComboBox {{ padding-right: {px(30)}; }}
    QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: {px(28)};
                            border: none; background: transparent; }}
    QComboBox::down-arrow {{ image: url({chev}); width: {px(11)}; height: {px(11)}; }}
    QComboBox QAbstractItemView {{ background: {COLOR_CARD}; border: 1px solid {COLOR_BORDER}; outline: none;
                                   padding: {px(4)}; selection-background-color: {COLOR_INK}; selection-color: #FFFFFF; }}
    QListWidget {{ padding: {px(4)}; }}
    QListWidget::item {{ padding: {px(9)} {px(10)}; border-radius: {px(8)}; }}
    QListWidget::item:selected {{ background: {COLOR_INK}; color: #FFFFFF; }}
    QListWidget::item:hover:!selected {{ background: {COLOR_SECONDARY_BG}; }}

    QTextBrowser {{ background: #FAFBFC; border: 1px solid {COLOR_BORDER}; border-radius: {px(10)}; padding: {px(6)}; }}
    QTextBrowser#reading {{ background: {COLOR_CARD}; border: none; border-radius: 0; padding: 0; }}
    QWidget#readingPage, QWidget#dialogSheet {{ background: {COLOR_CARD}; }}
    QFrame#dialogFooter {{ background: {COLOR_CARD}; border: none; border-top: 1px solid {COLOR_BG}; }}

    QMenu {{ background: {COLOR_CARD}; border: 1px solid {COLOR_BORDER}; padding: {px(4)}; }}
    QMenu::item {{ padding: {px(6)} {px(16)}; border-radius: {px(6)}; }}
    QMenu::item:selected {{ background: {COLOR_SECONDARY_BG}; color: {COLOR_TEXT}; }}

    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: {px(12)}; margin: {px(2)} 0; }}
    QScrollBar::handle:vertical {{ background: #C4CAD3; border-radius: {px(3)}; min-height: {px(32)}; margin: 0 {px(3)}; }}
    QScrollBar::handle:vertical:hover {{ background: #8F99A8; }}
    QScrollBar:horizontal {{ background: transparent; height: {px(12)}; margin: 0 {px(2)}; }}
    QScrollBar::handle:horizontal {{ background: #C4CAD3; border-radius: {px(3)}; min-width: {px(32)}; margin: {px(3)} 0; }}
    QScrollBar::handle:horizontal:hover {{ background: #8F99A8; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; border: none; background: none; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
    """


def repolish(widget: QWidget) -> None:
    """Після зміни динамічної властивості (setProperty) Qt не
    перечитує стилі сам — потрібно явно перезастосувати."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class ClickableFrame(QFrame):
    """QFrame, що реагує на клік (картки режимів, кроки)."""

    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.isEnabled():
            self.clicked.emit()
        super().mousePressEvent(event)


class ReadingView(QTextBrowser):
    """Перегляд статті (методологія): текст — колонкою фіксованої
    ширини по центру, смуга прокрутки — біля краю вікна."""

    def __init__(self):
        super().__init__()
        self.setObjectName("reading")
        self.setOpenExternalLinks(True)
        self.column_width = READING_MAX

    def update_margins(self):
        side = max(24, (self.width() - self.column_width) // 2)
        self.setViewportMargins(side, 0, side, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_margins()


class ScaledImage(QLabel):
    """Зображення, що завжди вписується в ширину вікна (без
    горизонтального скролу) і лишається чітким на екранах із високою
    щільністю пікселів. Клік відкриває оригінал у переглядачі Windows."""

    def __init__(self, path: Path):
        super().__init__()
        self._path = path
        self._src = QPixmap(str(path))
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed))

    def is_valid(self) -> bool:
        return not self._src.isNull()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._src.isNull():
            return
        dpr = self.devicePixelRatioF()
        width = max(1, self.width())
        scaled = self._src.scaledToWidth(int(width * dpr), Qt.SmoothTransformation)
        scaled.setDevicePixelRatio(dpr)
        self.setPixmap(scaled)
        height = int(scaled.height() / dpr)
        if self.height() != height:
            self.setFixedHeight(height)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._path)))
        super().mousePressEvent(event)


class AudioWorker(QThread):
    """Синтез TTS + склеювання FFmpeg у фоновому потоці. Спілкується з
    головним потоком ВИКЛЮЧНО через сигнали."""

    status_changed = Signal(str)
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, assembler, segments, default_rate, title, mode_label, final_path):
        super().__init__()
        self._assembler = assembler
        self._segments = segments
        self._default_rate = default_rate
        self._title = title
        self._mode_label = mode_label
        self._final_path = final_path

    def run(self):
        try:
            path = self._assembler.build(
                segments=self._segments,
                default_rate=self._default_rate,
                title=self._title,
                mode_label=self._mode_label,
                status=lambda s: self.status_changed.emit(s),
                final_path=self._final_path,
            )
            self.finished_ok.emit(path)
        except AudioError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"__UNEXPECTED__{exc}")


class MainWindow(QMainWindow):
    def __init__(self, body_font: str, title_font: str):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))


        self._body_font = body_font
        self._title_font = title_font
        self.app_settings = load_settings(SETTINGS_PATH)
        self.ui_lang = self.app_settings.get("ui_language", "uk")
        if self.ui_lang not in UI_LANGUAGE_CODES:
            self.ui_lang = "uk"
        self.zoom = self._closest_zoom(self.app_settings.get("zoom", "1.0"))

        # --- Бізнес-логіка (незмінна) --------------------------------
        self.reading_provider = JapaneseReadingProvider()
        self.sessions = SessionManager(reading_provider=self.reading_provider)
        self.db = DatabaseManager(DB_PATH)
        self.tts = TTSManager()
        self.player = AudioPlayer()

        # --- Стан інтерфейсу -----------------------------------------
        self._layouts: list = []          # (layout, margins, spacing) — масштабуються
        self._max_widths: list = []       # (widget, base_px)
        self._fixed_heights: list = []    # (widget, base_px)
        self._fixed_widths: list = []     # (widget, base_px)
        self._nav_buttons: dict[str, QPushButton] = {}
        self._pages: dict[str, QWidget] = {}
        self._step_items: dict[int, tuple] = {}
        self._step_bars: list[QFrame] = []
        self._step_widgets: dict[int, QWidget] = {}
        self._current_step = 1
        self._voice_cards: dict[str, QFrame] = {}
        self._mode_cards: dict[str, ClickableFrame] = {}
        self._selected_mode = "full_dialogue"
        self._audio_worker: Optional[AudioWorker] = None
        self._generating = False
        self._segments_total = 0
        self._player_timer: Optional[QTimer] = None

        QApplication.instance().setStyleSheet(build_stylesheet(self.zoom, body_font, title_font))
        self._build_ui()
        self._install_shortcuts()
        self._refresh_history()
        self._refresh_stats()
        self._on_session_changed(auto_step=False)
        self._show_page("new_lesson")
        self._apply_zoom(self.zoom, resize=False)
        self._restore_or_fit_window()

        warnings = []
        if not EDGE_TTS_AVAILABLE:
            warnings.append(self.m("warn_no_edge_tts"))
        if not self.reading_provider.available:
            warnings.append(self.m("warn_no_pykakasi"))
        if not self.player.available:
            warnings.append(self.m("warn_no_player"))
        if warnings:
            self.status_label.setText(self.m("warn_prefix") + "; ".join(warnings) + ".")

        QTimer.singleShot(150, self._open_wizard)

    # ==================================================================
    # ДОПОМІЖНЕ
    # ==================================================================
    def t(self, key: str) -> str:
        return UI_STRINGS.get(self.ui_lang, UI_STRINGS["uk"]).get(key, key)

    def m(self, key: str, **kwargs) -> str:
        template = MESSAGES.get(self.ui_lang, MESSAGES["uk"]).get(key, key)
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template

    def _count(self, n: int, kind: str) -> str:
        forms = COUNT_FORMS.get(self.ui_lang, COUNT_FORMS["uk"])[kind]
        if self.ui_lang == "uk":
            if n % 10 == 1 and n % 100 != 11:
                word = forms[0]
            elif 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
                word = forms[1]
            else:
                word = forms[2]
        else:
            word = forms[0] if n == 1 else forms[1]
        return f"{n} {word}"

    def _px(self, v: float) -> int:
        return max(0, round(v * self.zoom))

    def _lay(self, layout, margins=(0, 0, 0, 0), spacing=0):
        """Реєструє макет, щоб його відступи масштабувались разом з
        інтерфейсом (відступи макетів задаються в коді, не в QSS)."""
        self._layouts.append((layout, margins, spacing))
        layout.setContentsMargins(*(self._px(v) for v in margins))
        layout.setSpacing(self._px(spacing))
        return layout

    def _centered(self, inner: QWidget, max_width: int) -> QWidget:
        outer = QWidget()
        row = QHBoxLayout(outer)
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        row.addWidget(inner, 100)
        row.addStretch(1)
        self._max_widths.append((inner, max_width))
        inner.setMaximumWidth(self._px(max_width))
        return outer

    def _label(self, text: str, name: str = "", wrap: bool = False) -> QLabel:
        lbl = QLabel(text)
        if name:
            lbl.setObjectName(name)
        lbl.setWordWrap(wrap)
        return lbl

    def _button(self, text: str, handler=None, name: str = "", tooltip: str = "") -> QPushButton:
        btn = QPushButton(text)
        if name:
            btn.setObjectName(name)
        btn.setCursor(Qt.PointingHandCursor)
        if tooltip:
            btn.setToolTip(tooltip)
        if handler:
            btn.clicked.connect(handler)
        return btn

    def _card(self) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("card")
        layout = self._lay(QVBoxLayout(card), (24, 22, 24, 22), 14)
        return card, layout

    def _seg(self, items, size: str = "sm"):
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        group = QButtonGroup(box)
        group.setExclusive(True)
        buttons = []
        for idx, (value, label) in enumerate(items):
            btn = QPushButton(label)
            btn.setObjectName("seg")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("size", size)
            btn.setProperty("pos", "first" if idx == 0 else ("last" if idx == len(items) - 1 else "mid"))
            btn.setProperty("value", value)
            group.addButton(btn)
            row.addWidget(btn)
            buttons.append(btn)
        return box, group, buttons

    def _set_note(self, label: QLabel, kind: Optional[str], text: str = ""):
        """kind: 'ok' | 'warn' | None (сховати)."""
        if not kind:
            label.hide()
            return
        label.setObjectName("noteOk" if kind == "ok" else "noteWarn")
        label.setText(("✓  " if kind == "ok" else "⚠  ") + text)
        repolish(label)
        label.show()

    # ==================================================================
    # ВІКНО ТА МАСШТАБ
    # ==================================================================
    @staticmethod
    def _closest_zoom(value) -> float:
        try:
            v = float(value)
        except (TypeError, ValueError):
            v = 1.0
        return min(ZOOM_LEVELS, key=lambda z: abs(z - v))

    def _available_geometry(self):
        screen = self.screen() or QGuiApplication.primaryScreen()
        return screen.availableGeometry()

    def _fit_window(self, center: bool):
        if self.isMaximized() or self.isFullScreen():
            return
        avail = self._available_geometry()
        w = min(self._px(BASE_WIDTH), int(avail.width() * 0.96))
        h = min(self._px(BASE_HEIGHT), int(avail.height() * 0.94))
        self.resize(w, h)
        geo = self.frameGeometry()
        if center:
            geo.moveCenter(avail.center())
        # Не даємо вікну вилізти за межі екрана після збільшення масштабу.
        x = min(max(geo.left(), avail.left()), avail.right() - geo.width())
        y = min(max(geo.top(), avail.top()), avail.bottom() - geo.height())
        self.move(max(x, avail.left()), max(y, avail.top()))

    def _restore_or_fit_window(self):
        avail = self._available_geometry()
        self.setMinimumSize(min(MIN_WIDTH, avail.width()), min(MIN_HEIGHT, avail.height()))
        saved = self.app_settings.get("window_geometry", "")
        if saved:
            try:
                if self.restoreGeometry(QByteArray(base64.b64decode(saved))):
                    return
            except Exception:  # noqa: BLE001 — пошкоджене значення не критичне
                pass
        self._fit_window(center=True)

    def _apply_zoom(self, scale: float, resize: bool = True):
        self.zoom = scale
        QApplication.instance().setStyleSheet(build_stylesheet(scale, self._body_font, self._title_font))
        for layout, margins, spacing in self._layouts:
            layout.setContentsMargins(*(self._px(v) for v in margins))
            layout.setSpacing(self._px(spacing))
        for widget, base in self._max_widths:
            widget.setMaximumWidth(self._px(base))
        for widget, base in self._fixed_heights:
            widget.setFixedHeight(self._px(base))
        for widget, base in self._fixed_widths:
            widget.setFixedWidth(self._px(base))
        self.zoom_label.setText(f"{round(scale * 100)}%")
        self.reading.column_width = self._px(READING_MAX)
        self.reading.setHtml(self._methodology_html())
        self.reading.update_margins()
        self._rebuild_voice_panel()
        self._render_preview()
        if resize:
            self._fit_window(center=False)

    def _zoom_step(self, direction: int):
        idx = ZOOM_LEVELS.index(self.zoom)
        new_idx = min(max(idx + direction, 0), len(ZOOM_LEVELS) - 1)
        if new_idx != idx:
            self._apply_zoom(ZOOM_LEVELS[new_idx])

    def _zoom_reset(self):
        if self.zoom != 1.0:
            self._apply_zoom(1.0)

    def closeEvent(self, event):
        self.player.stop()
        self.app_settings["zoom"] = str(self.zoom)
        self.app_settings["window_geometry"] = base64.b64encode(self.saveGeometry().data()).decode("ascii")
        try:
            save_settings(SETTINGS_PATH, self.app_settings)
        except Exception:  # noqa: BLE001 — не блокуємо закриття через налаштування
            pass
        super().closeEvent(event)

    def _install_shortcuts(self):
        bindings = [
            (QKeySequence(QKeySequence.StandardKey.ZoomIn), lambda: self._zoom_step(+1)),
            (QKeySequence("Ctrl+="), lambda: self._zoom_step(+1)),
            (QKeySequence(QKeySequence.StandardKey.ZoomOut), lambda: self._zoom_step(-1)),
            (QKeySequence("Ctrl+0"), self._zoom_reset),
            (QKeySequence("Ctrl+Return"), self._shortcut_parse),
            (QKeySequence("Ctrl+Enter"), self._shortcut_parse),
            (QKeySequence("Ctrl+M"), self._shortcut_create),
        ]
        self._shortcuts = []
        for sequence, handler in bindings:
            shortcut = QShortcut(sequence, self)
            shortcut.activated.connect(handler)
            self._shortcuts.append(shortcut)

    def _shortcut_parse(self):
        if self.stack.currentWidget() is self._pages["new_lesson"] and self._current_step == 1:
            self._on_parse_new()

    def _shortcut_create(self):
        if (self.stack.currentWidget() is self._pages["new_lesson"] and self._current_step == 3
                and self.create_audio_btn.isEnabled()):
            self._on_create_audio()

    # ==================================================================
    # ПОБУДОВА ІНТЕРФЕЙСУ
    # ==================================================================
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("mainBackground")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_appbar())

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self._pages["new_lesson"] = self._build_new_lesson_page()
        self._pages["my_lessons"] = self._build_my_lessons_page()
        self._pages["methodology"] = self._build_methodology_page()
        for page in self._pages.values():
            self.stack.addWidget(page)

        footer = QFrame()
        footer.setObjectName("footerBar")
        frow = self._lay(QHBoxLayout(footer), (16, 5, 16, 6), 12)
        self.stat_label = self._label("", "footer")
        self.status_label = self._label(self.m("ready"), "footer")
        frow.addWidget(self.stat_label)
        frow.addStretch(1)
        frow.addWidget(self.status_label)
        root.addWidget(footer)

    def _build_appbar(self) -> QFrame:
        L = NAV_LABELS[self.ui_lang]
        bar = QFrame()
        bar.setObjectName("appbar")
        outer = QVBoxLayout(bar)
        outer.setContentsMargins(0, 0, 0, 0)

        inner = QWidget()
        row = self._lay(QHBoxLayout(inner), (24, 12, 24, 12), 22)

        brand_box = QVBoxLayout()
        brand_box.setSpacing(2)
        brand_box.addWidget(self._label(APP_NAME, "brand"))
        brand_box.addWidget(self._label(self.t("tagline"), "tagline"))
        row.addLayout(brand_box)

        nav = QHBoxLayout()
        nav.setSpacing(4)
        for key in ("new_lesson", "my_lessons", "methodology"):
            btn = self._button(L[key], lambda _=False, k=key: self._show_page(k), "navButton")
            btn.setCheckable(True)
            nav.addWidget(btn)
            self._nav_buttons[key] = btn
        nav.addWidget(self._button(L["about"], self._open_about_window, "navButton"))
        row.addLayout(nav)
        row.addStretch(1)

        zoom_box = QFrame()
        zoom_box.setObjectName("zoomBox")
        zoom_box.setToolTip(self.t("zoom_tooltip"))
        zrow = QHBoxLayout(zoom_box)
        zrow.setContentsMargins(2, 1, 2, 1)
        zrow.setSpacing(0)
        zrow.addWidget(self._button("−", lambda: self._zoom_step(-1), "zoomBtn", self.t("zoom_out")))
        self.zoom_label = self._label("100%", "zoomLabel")
        self.zoom_label.setAlignment(Qt.AlignCenter)
        zrow.addWidget(self.zoom_label)
        zrow.addWidget(self._button("+", lambda: self._zoom_step(+1), "zoomBtn", self.t("zoom_in")))
        row.addWidget(zoom_box)

        lang_box, lang_group, lang_buttons = self._seg([("uk", "UK"), ("en", "EN")])
        lang_box.setToolTip(L["interface_language"])
        for btn in lang_buttons:
            btn.setChecked(btn.property("value") == self.ui_lang)
            btn.clicked.connect(lambda _=False, code=btn.property("value"): self._on_ui_language_changed(code))
        row.addWidget(lang_box)

        outer.addWidget(self._centered(inner, CONTENT_MAX + 48))
        return bar

    def _show_page(self, name: str):
        self.stack.setCurrentWidget(self._pages[name])
        for key, btn in self._nav_buttons.items():
            btn.setChecked(key == name)

    # ------------------------------------------------------------------
    # СТОРІНКА «НОВИЙ УРОК» — кроки
    # ------------------------------------------------------------------
    def _build_new_lesson_page(self) -> QWidget:
        self.new_scroll = QScrollArea()
        self.new_scroll.setWidgetResizable(True)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)

        column = QWidget()
        col = self._lay(QVBoxLayout(column), (24, 18, 24, 28), 14)
        col.addLayout(self._build_stepper())

        self._step_widgets[1] = self._build_step1()
        self._step_widgets[2] = self._build_step2()
        self._step_widgets[3] = self._build_step3()
        for widget in self._step_widgets.values():
            col.addWidget(widget)
        col.addStretch(1)

        body_layout.addWidget(self._centered(column, CONTENT_MAX))
        self.new_scroll.setWidget(body)
        return self.new_scroll

    def _build_stepper(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(self._px(12))
        for i in (1, 2, 3):
            frame = ClickableFrame()
            frame.setObjectName("stepItem")
            frame.setCursor(Qt.PointingHandCursor)
            fl = self._lay(QHBoxLayout(frame), (0, 2, 0, 2), 8)
            dot = self._label(str(i), "stepDot")
            dot.setAlignment(Qt.AlignCenter)
            text = self._label(self.t(f"step{i}_label"), "stepText")
            fl.addWidget(dot)
            fl.addWidget(text)
            frame.clicked.connect(lambda i=i: self._go_step(i))
            row.addWidget(frame)
            self._step_items[i] = (frame, dot, text)
            if i < 3:
                bar = QFrame()
                bar.setObjectName("stepBar")
                row.addWidget(bar, 1)
                self._step_bars.append(bar)
        row.addStretch(3)
        return row

    def _step_allowed(self, step: int) -> bool:
        session = self.sessions.current
        if step == 1:
            return True
        if not session or not session.dialogue:
            return False
        if step == 2:
            return True
        return not session.missing_speaker_voices()

    def _go_step(self, step: int):
        if not self._step_allowed(step):
            return
        self._current_step = step
        for n, widget in self._step_widgets.items():
            widget.setVisible(n == step)
        self._refresh_stepper()
        self.new_scroll.verticalScrollBar().setValue(0)

    def _refresh_stepper(self):
        for n, (frame, dot, text) in self._step_items.items():
            allowed = self._step_allowed(n)
            if n == self._current_step:
                state = "active"
            elif n < self._current_step:
                state = "done"
            else:
                state = "pending" if allowed else "locked"
            dot.setText("✓" if state == "done" else str(n))
            for widget in (dot, text):
                widget.setProperty("state", state)
                repolish(widget)
            frame.setEnabled(allowed)
            frame.setCursor(Qt.PointingHandCursor if allowed else Qt.ArrowCursor)
        for idx, bar in enumerate(self._step_bars, 1):
            bar.setProperty("state", "done" if idx < self._current_step else "pending")
            repolish(bar)

    def _build_step1(self) -> QWidget:
        card, layout = self._card()

        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(self._px(4))
        titles.addWidget(self._label(self.t("s1_title"), "cardTitle"))
        titles.addWidget(self._label(self.t("s1_sub"), "cardSub", wrap=True))
        head.addLayout(titles, 1)
        head.addWidget(self._button(self.t("btn_new_prompt"), self._open_wizard))
        head.addWidget(self._button(self.t("btn_import_json"), self._on_import_json))
        head.addWidget(self._button(self.t("btn_example"), self._on_load_example, "ghost"))
        layout.addLayout(head)

        grid = QGridLayout()
        grid.setHorizontalSpacing(self._px(14))
        grid.setVerticalSpacing(self._px(6))
        grid.addWidget(self._label(self.t("label_title"), "fieldLabel"), 0, 0)
        grid.addWidget(self._label(self.t("label_language"), "fieldLabel"), 0, 1)
        grid.addWidget(self._label(self.t("label_level"), "fieldLabel"), 0, 2)
        self.title_edit = QLineEdit()
        self.language_combo = QComboBox()
        self.language_combo.addItems(language_labels())
        self.language_combo.currentTextChanged.connect(lambda _t: self._sync_levels_with_language())
        self.level_combo = QComboBox()
        grid.addWidget(self.title_edit, 1, 0)
        grid.addWidget(self.language_combo, 1, 1)
        grid.addWidget(self.level_combo, 1, 2)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 1)
        layout.addLayout(grid)
        self._sync_levels_with_language()

        layout.addWidget(self._label(self.t("label_dialog"), "fieldLabel"))
        self.source_text = QPlainTextEdit()
        self.source_text.setPlaceholderText(self.t("s1_placeholder"))
        self._fixed_heights.append((self.source_text, 200))
        layout.addWidget(self.source_text)

        self.parse_note = self._label("", "noteOk", wrap=True)
        self.parse_note.hide()
        layout.addWidget(self.parse_note)
        self.glued_note = self._label("", "noteWarn", wrap=True)
        self.glued_note.hide()
        layout.addWidget(self.glued_note)

        actions = QHBoxLayout()
        actions.setSpacing(self._px(10))
        actions.addWidget(self._button(self.t("btn_paste"), self._paste_into_source))
        actions.addWidget(self._button(self.t("btn_clear"), self._on_clear_source))
        actions.addStretch(1)
        self.next_voices_btn = self._button(self.t("btn_next_voices"), lambda: self._go_step(2))
        self.next_voices_btn.hide()
        actions.addWidget(self.next_voices_btn)
        actions.addWidget(self._button(self.t("btn_parse"), self._on_parse_new, "primary", self.t("parse_tooltip")))
        layout.addLayout(actions)
        return card

    def _build_step2(self) -> QWidget:
        wrap = QWidget()
        wl = self._lay(QVBoxLayout(wrap), (0, 0, 0, 0), 16)

        card, layout = self._card()
        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(self._px(4))
        titles.addWidget(self._label(self.t("s2_title"), "cardTitle"))
        titles.addWidget(self._label(self.t("voice_hint"), "cardSub", wrap=True))
        head.addLayout(titles, 1)
        self.speakers_chip = self._label("", "chip")
        head.addWidget(self.speakers_chip, 0, Qt.AlignTop)
        layout.addLayout(head)

        self.speakers_grid = QGridLayout()
        self.speakers_grid.setHorizontalSpacing(self._px(14))
        self.speakers_grid.setVerticalSpacing(self._px(14))
        layout.addLayout(self.speakers_grid)

        self.voice_note = self._label("", "noteWarn", wrap=True)
        self.voice_note.hide()
        layout.addWidget(self.voice_note)

        actions = QHBoxLayout()
        actions.addWidget(self._button(self.t("btn_back"), lambda: self._go_step(1)))
        actions.addStretch(1)
        self.next_practice_btn = self._button(self.t("btn_next_practice"), lambda: self._go_step(3), "primary")
        actions.addWidget(self.next_practice_btn)
        layout.addLayout(actions)
        wl.addWidget(card)

        preview_card, pl = self._card()
        pl.addWidget(self._label(self.t("preview_card_title"), "cardTitleSm"))
        self.preview_meta = self._label("", "cardSub")
        pl.addWidget(self.preview_meta)
        self.preview = QTextBrowser()
        self._fixed_heights.append((self.preview, 220))
        pl.addWidget(self.preview)
        wl.addWidget(preview_card)
        return wrap

    def _build_step3(self) -> QWidget:
        wrap = QWidget()
        wl = self._lay(QVBoxLayout(wrap), (0, 0, 0, 0), 16)

        card, layout = self._card()
        titles = QVBoxLayout()
        titles.setSpacing(self._px(4))
        titles.addWidget(self._label(self.t("s3_title"), "cardTitle"))
        titles.addWidget(self._label(self.t("s3_sub"), "cardSub", wrap=True))
        layout.addLayout(titles)

        modes = QGridLayout()
        modes.setHorizontalSpacing(self._px(10))
        for col, (value, title_key, desc_key) in enumerate(MODES):
            mode_card = ClickableFrame()
            mode_card.setObjectName("modeCard")
            mode_card.setCursor(Qt.PointingHandCursor)
            ml = self._lay(QVBoxLayout(mode_card), (14, 13, 14, 14), 6)
            ml.addWidget(self._label(self.t(title_key), "modeTitle"))
            ml.addWidget(self._label(self.t(desc_key), "modeDesc", wrap=True))
            ml.addStretch(1)
            mode_card.clicked.connect(lambda v=value: self._select_mode(v))
            modes.addWidget(mode_card, 0, col)
            modes.setColumnStretch(col, 1)
            self._mode_cards[value] = mode_card
        layout.addLayout(modes)
        self._select_mode(self._selected_mode)

        settings = QHBoxLayout()
        settings.setSpacing(self._px(32))
        rate_col = QVBoxLayout()
        rate_col.setSpacing(self._px(6))
        rate_col.addWidget(self._label(self.t("label_rate"), "fieldLabel"))
        rate_box, self.rate_group, rate_buttons = self._seg([(r, r.replace("-", "−")) for r in RATES], "lg")
        for btn in rate_buttons:
            btn.setChecked(btn.property("value") == DEFAULT_RATE)
        rate_col.addWidget(rate_box)
        settings.addLayout(rate_col)

        pause_col = QVBoxLayout()
        pause_col.setSpacing(self._px(6))
        pause_col.addWidget(self._label(self.t("label_pause"), "fieldLabel"))
        pause_row = QHBoxLayout()
        pause_row.setSpacing(self._px(10))
        pause_row.addWidget(self._label(self.t("pause_recommendation"), "hint"))
        self.pause_combo = QComboBox()
        for value in PAUSE_VALUES:
            self.pause_combo.addItem(f"{value} {self.t('pause_sec_suffix')}", value)
        self.pause_combo.setCurrentIndex(PAUSE_VALUES.index(DEFAULT_PAUSE))
        self._fixed_widths.append((self.pause_combo, 110))
        pause_row.addWidget(self.pause_combo)
        pause_col.addLayout(pause_row)
        settings.addLayout(pause_col)
        settings.addStretch(1)
        layout.addLayout(settings)

        actions = QHBoxLayout()
        actions.setSpacing(self._px(10))
        actions.addWidget(self._button(self.t("btn_back"), lambda: self._go_step(2)))
        actions.addWidget(self._button(self.t("btn_export_json"), self._on_export_json))
        actions.addStretch(1)
        actions.addWidget(self._button(self.t("btn_open_folder"), self._on_open_output))
        self.create_audio_btn = self._button(
            self.t("btn_create_mp3"), self._on_create_audio, "primary", self.t("create_tooltip"),
        )
        actions.addWidget(self.create_audio_btn)
        layout.addLayout(actions)

        self.progress_box = QFrame()
        self.progress_box.setObjectName("progressBox")
        pbl = self._lay(QVBoxLayout(self.progress_box), (16, 12, 16, 14), 8)
        ptop = QHBoxLayout()
        self.progress_label = self._label("")
        self.progress_pct = self._label("", "hint")
        ptop.addWidget(self.progress_label)
        ptop.addStretch(1)
        ptop.addWidget(self.progress_pct)
        pbl.addLayout(ptop)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        pbl.addWidget(self.progress_bar)
        self.progress_box.hide()
        layout.addWidget(self.progress_box)
        wl.addWidget(card)

        player_card, pl = self._card()
        pl.addWidget(self._label(self.t("player_title"), "cardTitleSm"))
        prow = QHBoxLayout()
        prow.setSpacing(self._px(10))
        self.player_play_btn = self._button("▶", self._on_player_play, "roundPlay")
        self.player_pause_btn = self._button("❚❚", self._on_player_pause, "round")
        self.player_stop_btn = self._button("■", self._on_player_stop, "round")
        for btn in (self.player_play_btn, self.player_pause_btn, self.player_stop_btn):
            prow.addWidget(btn)
        file_box = QVBoxLayout()
        file_box.setSpacing(self._px(2))
        self.player_track_label = self._label(self.t("player_no_file"), "fileName")
        self.player_time_label = self._label("00:00", "hint")
        file_box.addWidget(self.player_track_label)
        file_box.addWidget(self.player_time_label)
        prow.addSpacing(self._px(6))
        prow.addLayout(file_box)
        prow.addStretch(1)
        prow.addWidget(self._button(self.t("player_open"), self._on_player_open))
        pl.addLayout(prow)
        if not self.player.available:
            for btn in (self.player_play_btn, self.player_pause_btn, self.player_stop_btn):
                btn.setEnabled(False)
        wl.addWidget(player_card)
        return wrap

    def _select_mode(self, value: str):
        self._selected_mode = value
        for key, card in self._mode_cards.items():
            card.setProperty("selected", "true" if key == value else "false")
            repolish(card)

    # ------------------------------------------------------------------
    # СТОРІНКА «МОЇ УРОКИ»
    # ------------------------------------------------------------------
    def _build_my_lessons_page(self) -> QWidget:
        page = QWidget()
        pl = QVBoxLayout(page)
        pl.setContentsMargins(0, 0, 0, 0)

        column = QWidget()
        row = self._lay(QHBoxLayout(column), (24, 22, 24, 24), 16)

        history_card, hl = self._card()
        head = QHBoxLayout()
        head.addWidget(self._label(self.t("history_title"), "cardTitle"), 1)
        self.clear_history_btn = self._button(self.t("btn_clear_history"), self._on_clear_history, "ghost")
        head.addWidget(self.clear_history_btn)
        hl.addLayout(head)
        hl.addWidget(self._label(MY_LESSONS_HINT[self.ui_lang], "cardSub", wrap=True))

        self.history_stack = QStackedWidget()
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self._on_load_history_item)
        self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self._show_history_context_menu)
        self.history_stack.addWidget(self.history_list)

        empty = QWidget()
        el = QVBoxLayout(empty)
        el.addStretch(1)
        empty_label = self._label(self.t("empty_history"), "cardSub")
        empty_label.setAlignment(Qt.AlignCenter)
        el.addWidget(empty_label)
        first_btn = self._button(self.t("btn_first_lesson"), self._start_first_lesson, "primary")
        el.addWidget(first_btn, 0, Qt.AlignCenter)
        el.addStretch(2)
        self.history_stack.addWidget(empty)
        hl.addWidget(self.history_stack, 1)
        row.addWidget(history_card, 3)

        json_card, jl = self._card()
        jl.addWidget(self._label(JSON_SECTION_TITLE[self.ui_lang], "cardTitle"))
        jl.addWidget(self._button(self.t("btn_export_json"), self._on_export_json, "primary"))
        jl.addWidget(self._button(self.t("btn_import_json"), self._on_import_json))
        jl.addStretch(1)
        self._fixed_widths.append((json_card, 300))
        row.addWidget(json_card, 0)

        pl.addWidget(self._centered(column, CONTENT_MAX))
        return page

    def _start_first_lesson(self):
        self._show_page("new_lesson")
        self._go_step(1)
        self.source_text.setFocus()

    def _show_history_context_menu(self, pos):
        item = self.history_list.itemAt(pos)
        if item is None:
            return
        self.history_list.setCurrentItem(item)
        menu = QMenu(self)
        delete_action = menu.addAction(self.t("menu_delete"))
        if menu.exec(self.history_list.mapToGlobal(pos)) == delete_action:
            self._on_delete_history_item()

    # ------------------------------------------------------------------
    # СТОРІНКА «МЕТОДОЛОГІЯ»
    # ------------------------------------------------------------------
    def _build_methodology_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("readingPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        self.reading = ReadingView()
        layout.addWidget(self.reading)
        return page

    @staticmethod
    def _inline_md(text: str) -> str:
        escaped = html.escape(text)
        return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)

    def _methodology_html(self) -> str:
        """Перетворює простий розмітник content.py на HTML для статті:
        склеює жорстко перенесені рядки в цілі абзаци (саме через ці
        переноси раніше текст рвався посеред речення), підтримує
        заголовки '# ', пункти '- ' і **жирний**."""
        blocks: list[tuple[str, str]] = []
        para: list[str] = []
        bullet: list[str] = []

        def flush():
            if para:
                blocks.append(("p", " ".join(para)))
                para.clear()
            if bullet:
                blocks.append(("li", " ".join(bullet)))
                bullet.clear()

        for line in METHODOLOGY_TEXT[self.ui_lang].strip("\n").split("\n"):
            s = line.strip()
            if not s:
                flush()
            elif s.startswith("# "):
                flush()
                blocks.append(("h2", re.sub(r"^\d+\.\s*", "", s[2:])))
            elif s.startswith("- "):
                flush()
                bullet.append(s[2:])
            elif bullet:
                bullet.append(s)
            else:
                para.append(s)
        flush()

        z = self.zoom
        fs = lambda v: f"{round(v * z)}px"  # noqa: E731
        parts = [
            f'<h1 style="font-size:{fs(28)}; color:{COLOR_INK}; font-weight:700; margin:{fs(32)} 0 {fs(14)} 0;">'
            f"{html.escape(METHODOLOGY_TITLE[self.ui_lang])}</h1>"
        ]
        in_list = False
        for kind, text in blocks:
            if kind == "li" and not in_list:
                parts.append(f'<ul style="margin:0 0 {fs(10)} {fs(4)};">')
                in_list = True
            if kind != "li" and in_list:
                parts.append("</ul>")
                in_list = False
            body = self._inline_md(text)
            if kind == "h2":
                parts.append(
                    f'<h2 style="font-size:{fs(18)}; font-weight:600; margin:{fs(26)} 0 {fs(8)} 0;">{body}</h2>'
                )
            elif kind == "li":
                parts.append(f'<li style="font-size:{fs(15)}; line-height:165%; margin-bottom:{fs(8)};">{body}</li>')
            else:
                parts.append(
                    f'<p style="font-size:{fs(15)}; line-height:170%; margin:0 0 {fs(12)} 0; color:#2A3342;">{body}</p>'
                )
        if in_list:
            parts.append("</ul>")
        parts.append(
            f'<table width="100%" cellpadding="{round(16 * z)}" style="margin:{fs(24)} 0 {fs(36)} 0;">'
            f'<tr><td bgcolor="#F4F6F9" align="center" style="font-size:{fs(16)}; font-weight:600; color:{COLOR_INK};">'
            f"{html.escape(self.t('method_formula'))}</td></tr></table>"
        )
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # «ПРО ПРОГРАМУ»
    # ------------------------------------------------------------------
    def _open_about_window(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(ABOUT_TITLE[self.ui_lang])
        avail = self._available_geometry()
        dlg.resize(min(self._px(900), int(avail.width() * 0.9)), min(self._px(760), int(avail.height() * 0.9)))
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sheet = QWidget()
        sheet.setObjectName("dialogSheet")
        sl = QVBoxLayout(sheet)
        sl.setContentsMargins(self._px(32), self._px(26), self._px(32), self._px(20))
        sl.setSpacing(self._px(8))

        sl.addWidget(self._label(APP_NAME, "brand"))
        about = ABOUT_TEXT[self.ui_lang]
        lead = about.split(" - ", 1)[-1] if " - " in about else about
        lead_label = self._label(lead[:1].upper() + lead[1:], "cardSub", wrap=True)
        sl.addWidget(lead_label)
        sl.addSpacing(self._px(10))

        if INFOGRAPHIC_PATH.exists():
            image = ScaledImage(INFOGRAPHIC_PATH)
            if image.is_valid():
                image.setToolTip(self.t("about_zoom_hint"))
                sl.addWidget(image)
                hint = self._label(self.t("about_zoom_hint"), "hint")
                hint.setAlignment(Qt.AlignCenter)
                sl.addWidget(hint)
        sl.addStretch(1)
        scroll.setWidget(sheet)
        layout.addWidget(scroll, 1)

        footer = QFrame()
        footer.setObjectName("dialogFooter")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(self._px(24), self._px(12), self._px(24), self._px(12))
        fl.addStretch(1)
        ok_btn = self._button(self.t("ok"), dlg.accept, "primary")
        ok_btn.setMinimumWidth(self._px(96))
        fl.addWidget(ok_btn)
        layout.addWidget(footer)
        dlg.exec()

    def _on_ui_language_changed(self, code: str):
        if code == self.ui_lang:
            return
        self.app_settings["ui_language"] = code
        save_settings(SETTINGS_PATH, self.app_settings)
        QMessageBox.information(self, APP_NAME, RESTART_NOTICE[code])
        self.close()

    # ==================================================================
    # КРОК 1 — ТЕКСТ УРОКУ
    # ==================================================================
    def _paste_into_source(self):
        text = QApplication.clipboard().text()
        if not text:
            QMessageBox.warning(self, APP_NAME, self.m("clipboard_empty"))
            return
        self.source_text.insertPlainText(text)
        self.source_text.setFocus()

    def _on_clear_source(self):
        self.source_text.clear()
        self._set_note(self.parse_note, None)
        self._set_note(self.glued_note, None)

    def _current_language_code(self) -> str:
        return code_by_label(self.language_combo.currentText())

    def _sync_levels_with_language(self):
        cfg = get_language(self._current_language_code())
        self.level_combo.clear()
        self.level_combo.addItems(cfg.levels)

    def _set_form_from_session(self, session: LessonSession):
        idx = self.language_combo.findText(get_language(session.target_language).label)
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        self._sync_levels_with_language()
        level_idx = self.level_combo.findText(session.level)
        if level_idx >= 0:
            self.level_combo.setCurrentIndex(level_idx)
        self.title_edit.setText(session.title)
        self.source_text.setPlainText(session.raw_text)

    def _open_wizard(self):
        dlg = PromptWizard(self, ui_lang=self.ui_lang)
        avail = self._available_geometry()
        dlg.resize(min(dlg.width(), int(avail.width() * 0.9)), min(dlg.height(), int(avail.height() * 0.9)))
        if dlg.exec() == QDialog.Accepted:
            code, level, topic = dlg.result_values()
            self._apply_wizard_choice(code, level, topic)

    def _apply_wizard_choice(self, language_code, level, topic):
        if not language_code:
            return
        idx = self.language_combo.findText(get_language(language_code).label)
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        self._sync_levels_with_language()
        if level:
            level_idx = self.level_combo.findText(level)
            if level_idx >= 0:
                self.level_combo.setCurrentIndex(level_idx)
        if topic:
            self.title_edit.setText(topic)
        self._show_page("new_lesson")
        self._go_step(1)
        self.source_text.setFocus()
        self.status_label.setText(self.m("wizard_prompt_ready"))

    def _on_parse_new(self):
        current = self.sessions.current
        if current and current.dialogue:
            if QMessageBox.question(
                self, APP_NAME, self.m("confirm_replace_lesson", title=current.title),
            ) != QMessageBox.Yes:
                return
        try:
            session = self.sessions.create_from_text(
                raw_text=self.source_text.toPlainText(), title=self.title_edit.text(),
                level=self.level_combo.currentText(), target_language=self._current_language_code(),
            )
        except ValueError as exc:
            key = "paste_dialog_text" if str(exc) == "EMPTY_TEXT" else "no_lines_found"
            self._set_note(self.parse_note, "warn", self.m(key))
            self._set_note(self.glued_note, None)
            return

        session.id = self.db.save_session(session)
        self.status_label.setText(self.m("session_created", title=session.title, id=session.id))
        self._refresh_history()
        self._refresh_stats()
        self._on_session_changed(auto_step=True)

    def _on_load_example(self):
        lang_code = self._current_language_code()
        example_file = EXAMPLE_FILES.get(lang_code)
        if not example_file or not example_file.exists():
            self._set_note(self.parse_note, "warn", self.m("example_not_found", lang=get_language(lang_code).label))
            return
        self.source_text.setPlainText(example_file.read_text(encoding="utf-8"))
        if not self.title_edit.text().strip():
            self.title_edit.setText(f"{get_language(lang_code).label} example")
        self._set_note(self.glued_note, None)
        self._set_note(self.parse_note, "ok", self.m("example_loaded_hint", btn=self.t("btn_parse")))

    def _on_session_changed(self, auto_step: bool):
        """Єдина точка оновлення інтерфейсу після зміни CURRENT SESSION
        (новий розбір, урок з історії, імпорт, видалення)."""
        session = self.sessions.current
        self._rebuild_voice_panel()
        self._render_preview()

        if not session or not session.dialogue:
            self._set_note(self.parse_note, None)
            self._set_note(self.glued_note, None)
            self.next_voices_btn.hide()
            self._go_step(1)
            return

        s = session.summary()
        self._set_note(self.parse_note, "ok", self.m(
            "parsed_ok",
            lines=self._count(s["lines"], "line"),
            speakers=self._count(s["speakers"], "speaker"),
            phrases=self._count(s["phrases"], "phrase"),
        ))
        glued = None
        for row, line in enumerate(session.dialogue, 1):
            name = find_glued_speaker_marker(line.text)
            if name:
                glued = (row, name)
                break
        if glued:
            self._set_note(self.glued_note, "warn", self.m("glued_inline", row=glued[0], name=glued[1]))
        else:
            self._set_note(self.glued_note, None)
        self.next_voices_btn.show()

        if not auto_step:
            self._refresh_stepper()
        elif glued:
            self._go_step(1)       # лишаємось на кроці 1, щоб користувач побачив попередження
        elif not session.missing_speaker_voices():
            self._go_step(3)       # урок з історії з уже обраними голосами
        else:
            self._go_step(2)

    # ==================================================================
    # КРОК 2 — ГОЛОСИ
    # ==================================================================
    def _rebuild_voice_panel(self):
        while self.speakers_grid.count():
            item = self.speakers_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._voice_cards.clear()

        session = self.sessions.current
        if not session or not session.dialogue:
            self.speakers_chip.setText("")
            self._update_voice_state()
            return

        speakers = session.unique_speakers()
        counts = {sp: sum(1 for d in session.dialogue if d.speaker == sp) for sp in speakers}
        for idx, speaker in enumerate(speakers):
            card = QFrame()
            card.setObjectName("spkCard")
            row = QHBoxLayout(card)
            row.setContentsMargins(*(self._px(16),) * 4)
            row.setSpacing(self._px(14))

            bg, fg = AVATAR_COLORS[idx % len(AVATAR_COLORS)]
            avatar = self._label(speaker[:1].upper(), "avatar")
            avatar.setAlignment(Qt.AlignCenter)
            avatar.setStyleSheet(f"background: {bg}; color: {fg};")
            row.addWidget(avatar)

            info = QVBoxLayout()
            info.setSpacing(self._px(2))
            info.addWidget(self._label(speaker, "spkName", wrap=True))
            info.addWidget(self._label(self._count(counts[speaker], "line"), "hint"))
            row.addLayout(info, 1)

            seg_box, _group, buttons = self._seg(
                [("female", self.t("gender_female")), ("male", self.t("gender_male"))], "lg",
            )
            saved = session.speaker_voices.get(speaker)
            for btn in buttons:
                btn.setChecked(btn.property("value") == saved)
                btn.clicked.connect(
                    lambda _=False, sp=speaker, code=btn.property("value"): self._on_gender_clicked(sp, code)
                )
            row.addWidget(seg_box)

            self.speakers_grid.addWidget(card, idx // 2, idx % 2)
            self._voice_cards[speaker] = card

        self.speakers_chip.setText(self.m("speakers_chip", n=len(speakers)))
        self._update_voice_state()

    def _on_gender_clicked(self, speaker: str, code: str):
        session = self.sessions.current
        if not session:
            return
        session.set_speaker_gender(speaker, code)
        self.db.update_session(session)
        self._update_voice_state()

    def _update_voice_state(self):
        session = self.sessions.current
        missing = session.missing_speaker_voices() if session and session.dialogue else []
        for speaker, card in self._voice_cards.items():
            card.setProperty("missing", "true" if speaker in missing else "false")
            repolish(card)
        if not session or not session.dialogue:
            self._set_note(self.voice_note, None)
            self.next_practice_btn.setEnabled(False)
        elif missing:
            self._set_note(self.voice_note, "warn", self.m("voices_missing_inline", names=", ".join(missing)))
            self.next_practice_btn.setEnabled(False)
        else:
            self._set_note(self.voice_note, "ok", self.m("voices_ok_inline"))
            self.next_practice_btn.setEnabled(True)
        self._refresh_stepper()
        self._update_create_button_state()

    def _render_preview(self):
        session = self.sessions.current
        if not session or not session.dialogue:
            self.preview.setHtml("")
            self.preview_meta.setText("")
            return
        s = session.summary()
        self.preview_meta.setText(self.m("lesson_meta", title=s["title"], lang=s["target_language"], level=s["level"]))
        show_reading = get_language(session.target_language).needs_romaji
        colors = {sp: AVATAR_COLORS[i % len(AVATAR_COLORS)][1] for i, sp in enumerate(session.unique_speakers())}
        out = []
        for d in session.dialogue:
            line = (f'<p style="margin:0 0 6px 0;"><b style="color:{colors.get(d.speaker, COLOR_TEXT)}">'
                    f"{html.escape(d.speaker)}</b>&nbsp;&nbsp;{html.escape(d.text)}")
            if show_reading:
                reading = d.reading or self.t("preview_no_romaji")
                line += f'<br><span style="color:#8891A0;">[{html.escape(reading)}]</span>'
            out.append(line + "</p>")
        out.append(f'<p style="margin:14px 0 6px 0;"><b>{html.escape(self.t("preview_phrases"))}</b></p>')
        if not session.phrases:
            out.append(f'<p style="color:#8891A0;">{html.escape(self.t("preview_no_phrases"))}</p>')
        for p in session.phrases:
            meaning = p.meaning_uk or self.t("preview_no_translation")
            out.append(f'<p style="margin:0 0 4px 0;">{html.escape(p.phrase)} — '
                       f'<span style="color:#5B6574;">{html.escape(meaning)}</span></p>')
        self.preview.setHtml("\n".join(out))

    # ==================================================================
    # КРОК 3 — АУДІО
    # ==================================================================
    def _update_create_button_state(self):
        session = self.sessions.current
        ready = bool(session and session.dialogue and not session.missing_speaker_voices())
        self.create_audio_btn.setEnabled(ready and not self._generating)

    def _current_rate(self) -> str:
        checked = self.rate_group.checkedButton()
        return checked.property("value") if checked else DEFAULT_RATE

    def _on_create_audio(self):
        session = self.sessions.current
        if not session:
            QMessageBox.warning(self, APP_NAME, self.m("no_lesson_yet"))
            return
        missing = session.missing_speaker_voices()
        if missing:
            QMessageBox.warning(self, APP_NAME, self.m("missing_voices", names=", ".join(missing)))
            return

        settings = AudioSettings(
            speech_rate=self._current_rate(),
            pause_between_lines=float(self.pause_combo.currentData()),
        )
        generator = ExerciseGenerator(settings)
        builders = {
            "full_dialogue": ("Full Dialogue", generator.full_dialogue),
            "shadowing": ("Shadowing", generator.shadowing),
            "phrase_trainer": ("Key Phrases", generator.phrase_trainer),
            "recall": ("Recall", generator.recall),
        }
        label, builder = builders[self._selected_mode]
        try:
            segments = builder(session)
        except MissingVoiceError as exc:
            QMessageBox.warning(self, APP_NAME, self.m("missing_voice_error", names=", ".join(exc.speakers)))
            return
        except ValueError as exc:
            if str(exc) == "NO_PHRASES":
                QMessageBox.warning(self, APP_NAME, self.m("no_phrases_for_mode"))
            else:
                QMessageBox.critical(self, APP_NAME, str(exc))
            return

        assembler = AudioAssembler(self.tts, OUT_DIR, TEMP_DIR)
        lesson_title = f"{session.title}_{session.level}"
        planned_path = assembler.target_path(lesson_title, label)
        final_path: Optional[Path] = None
        if planned_path.exists():
            answer = QMessageBox.question(
                self, APP_NAME, self.m("file_exists_prompt", name=planned_path.name),
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            )
            if answer == QMessageBox.Cancel:
                return
            if answer == QMessageBox.Yes:
                final_path = planned_path
                # Файл, завантажений у плеєр, Windows тримає зайнятим —
                # звільняємо перед перезаписом (інакше Permission denied).
                if self.player.loaded_path and Path(self.player.loaded_path) == planned_path:
                    self.player.unload()
            else:
                final_path = assembler.next_available_path(lesson_title, label)

        self._generating = True
        self._segments_total = max(1, len(segments))
        self._update_create_button_state()
        self.progress_bar.setRange(0, self._segments_total)
        self.progress_bar.setValue(0)
        self.progress_label.setText(self.m("creating_mp3", label=label))
        self.progress_pct.setText("0%")
        self.progress_box.show()
        self.status_label.setText(self.m("creating_mp3", label=label))

        self._audio_worker = AudioWorker(assembler, segments, settings.speech_rate, lesson_title, label, final_path)
        self._audio_worker.status_changed.connect(self._on_worker_status)
        self._audio_worker.finished_ok.connect(lambda path, sid=session.id: self._on_audio_finished(path, sid))
        self._audio_worker.failed.connect(self._on_audio_failed)
        self._audio_worker.start()

    def _on_worker_status(self, text: str):
        """audio.py повідомляє прогрес рядками «Озвучення N: …» (N — номер
        сегмента серед усіх, включно з паузами) і «Об'єднання …». Беремо
        з них реальний номер кроку для смуги прогресу."""
        match = re.match(r"^Озвучення\s+(\d+)", text)
        if match:
            n = min(int(match.group(1)), self._segments_total)
            self.progress_bar.setRange(0, self._segments_total)
            self.progress_bar.setValue(n)
            self.progress_label.setText(self.m("progress_speaking", n=n, total=self._segments_total))
            self.progress_pct.setText(f"{round(n * 100 / self._segments_total)}%")
        elif text.startswith("Об'єднання"):
            self.progress_bar.setRange(0, 0)  # невизначений прогрес на час склеювання
            self.progress_label.setText(self.m("progress_merging"))
            self.progress_pct.setText("")

    def _finish_generation(self):
        self._generating = False
        self.progress_box.hide()
        self._update_create_button_state()

    def _on_audio_finished(self, path: str, session_id):
        self._finish_generation()
        self.db.log_event("audio_created", session_id)
        self._refresh_stats()
        self._load_into_player(path, auto_play=False)
        self.status_label.setText(self.m("mp3_ready_status"))

    def _on_audio_failed(self, message: str):
        self._finish_generation()
        if message.startswith("__UNEXPECTED__"):
            QMessageBox.critical(self, APP_NAME, self.m("unexpected_error", exc=message[len("__UNEXPECTED__"):]))
            self.status_label.setText(self.m("generic_error_status"))
        else:
            QMessageBox.critical(self, APP_NAME, message)
            self.status_label.setText(self.m("mp3_error_status"))

    def _on_open_output(self):
        # Працює однаково на Windows (Провідник), macOS (Finder) і Linux.
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(OUT_DIR))):
            QMessageBox.information(self, APP_NAME, self.m("open_folder_fallback", dir=OUT_DIR))

    # ==================================================================
    # ПЛЕЄР
    # ==================================================================
    def _load_into_player(self, path: str, auto_play: bool = False):
        if not self.player.available:
            QMessageBox.warning(self, APP_NAME, self.m("player_unavailable"))
            return
        try:
            self.player.load(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, APP_NAME, str(exc))
            return
        self.player_track_label.setText(Path(path).name)
        self.player_time_label.setText("00:00")
        if auto_play:
            self.player.play()
            self._start_player_ticking()

    def _on_player_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "", str(OUT_DIR), "MP3 (*.mp3)")
        if path:
            self._load_into_player(path, auto_play=True)

    def _on_player_play(self):
        if not self.player.available or self.player.is_busy():
            return
        self.player.play()
        self._start_player_ticking()

    def _on_player_pause(self):
        self.player.pause()

    def _on_player_stop(self):
        self.player.stop()
        self.player_time_label.setText("00:00")

    def _start_player_ticking(self):
        if self._player_timer is None:
            self._player_timer = QTimer(self)
            self._player_timer.timeout.connect(self._tick_player)
        self._player_timer.start(300)

    def _tick_player(self):
        if self.player.is_busy():
            seconds = int(self.player.position_seconds())
            self.player_time_label.setText(f"{seconds // 60:02d}:{seconds % 60:02d}")
        elif self._player_timer:
            self._player_timer.stop()

    # ==================================================================
    # JSON / ІСТОРІЯ / СТАТИСТИКА
    # ==================================================================
    def _on_export_json(self):
        session = self.sessions.current
        if not session:
            QMessageBox.warning(self, APP_NAME, self.m("no_lesson_yet"))
            return
        path, _ = QFileDialog.getSaveFileName(self, "", str(OUT_DIR / f"{session.title}.json"), "JSON (*.json)")
        if not path:
            return
        Path(path).write_text(session.to_json(), encoding="utf-8")
        self.status_label.setText(self.m("lesson_exported", path=path))

    def _on_import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "", str(OUT_DIR), "JSON (*.json)")
        if not path:
            return
        try:
            session = LessonSession.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, APP_NAME, self.m("json_read_error", exc=exc))
            return
        if not session.dialogue:
            QMessageBox.warning(self, APP_NAME, self.m("no_lines_found"))
            return
        if session.target_language not in TARGET_LANGUAGES:
            QMessageBox.warning(self, APP_NAME, self.m("unknown_language_json", lang=session.target_language))
            return
        session.id = self.db.save_session(session)
        self.sessions.set_current(session)
        self._set_form_from_session(session)
        self._refresh_history()
        self._refresh_stats()
        self._show_page("new_lesson")
        self._on_session_changed(auto_step=True)
        self.status_label.setText(self.m("lesson_imported", title=session.title))

    def _on_load_history_item(self, item: QListWidgetItem):
        session = self.db.load_session(item.data(Qt.UserRole))
        if not session:
            return
        self.sessions.set_current(session)
        self._set_form_from_session(session)
        self._show_page("new_lesson")
        self._on_session_changed(auto_step=True)
        self.status_label.setText(self.m("session_loaded_from_history", title=session.title))

    def _on_delete_history_item(self):
        item = self.history_list.currentItem()
        if item is None:
            return
        session_id = item.data(Qt.UserRole)
        if QMessageBox.question(self, APP_NAME, self.m("confirm_delete_lesson")) != QMessageBox.Yes:
            return
        self.db.delete_session(session_id)
        if self.sessions.current and self.sessions.current.id == session_id:
            self.sessions.clear()
            self._on_session_changed(auto_step=False)
        self._refresh_history()
        self._refresh_stats()
        self.status_label.setText(self.m("lesson_deleted"))

    def _on_clear_history(self):
        if QMessageBox.question(self, APP_NAME, self.m("confirm_clear_history")) != QMessageBox.Yes:
            return
        self.db.clear_history()
        self.sessions.clear()
        self._on_session_changed(auto_step=False)
        self._refresh_history()
        self._refresh_stats()
        self.status_label.setText(self.m("history_cleared"))

    def _refresh_history(self):
        rows = self.db.list_history()
        self.history_list.clear()
        for session_id, created_at, title, target_language, level in rows:
            lang_label = get_language(target_language).label if target_language in TARGET_LANGUAGES else target_language
            item = QListWidgetItem(f"{title}   ·   {lang_label} {level}   ·   {created_at[:16].replace('T', ' ')}")
            item.setData(Qt.UserRole, session_id)
            self.history_list.addItem(item)
        has_items = bool(rows)
        self.history_stack.setCurrentIndex(0 if has_items else 1)
        self.clear_history_btn.setEnabled(has_items)

    def _refresh_stats(self):
        s = self.db.stats()
        self.stat_label.setText(
            f"Сьогодні уроків: {s['today']}  ·  Всього: {s['total_sessions']}  ·  MP3: {s['audio_created']}"
            if self.ui_lang == "uk" else
            f"Lessons today: {s['today']}  ·  Total: {s['total_sessions']}  ·  MP3: {s['audio_created']}"
        )


def main():
    # Чіткий рендеринг при дробовому масштабуванні Windows (125%, 150%).
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    # Назва застосунку визначає імена системних тек даних (init_paths).
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setOrganizationName("")
    init_paths()
    body_font, title_font = load_app_fonts()
    window = MainWindow(body_font, title_font)
    window.show()
    sys.exit(app.exec())
