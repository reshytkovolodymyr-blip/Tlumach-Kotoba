"""
player.py
---------
Мінімальний аудіоплеєр для прослуховування згенерованих MP3 прямо в
застосунку, без потреби відкривати сторонню програму. Побудований на
pygame.mixer.music — програє один файл за раз (play/pause/stop),
цього достатньо для прослуховування уроку.

Залежність у requirements.txt — саме "pygame-ce" (Community Edition),
а не класичний "pygame": останній не публікує готові збірки (wheels)
для нових версій Python на Windows, через що встановлення падає з
ModuleNotFoundError на "setuptools._distutils.msvccompiler" (distutils
прибрано з Python 3.12+, а стара система збірки pygame досі його
шукає). pygame-ce — активно підтримуваний drop-in форк: імпортується
так само (`import pygame` нижче), але має готові wheels для сучасних
версій Python.

Якщо pygame(-ce) не встановлено — PLAYER_AVAILABLE=False, і GUI
показує про це зрозуміле повідомлення замість падіння програми.
"""

from __future__ import annotations

try:
    import pygame
    PLAYER_AVAILABLE = True
except ImportError:  # pragma: no cover — залежить від встановленого оточення
    pygame = None
    PLAYER_AVAILABLE = False


class PlayerError(Exception):
    """Аудіоплеєр недоступний або файл не вдалось відкрити."""


class AudioPlayer:
    """Тонка обгортка над pygame.mixer.music. Один екземпляр на застосунок."""

    def __init__(self):
        self._ready = False
        self._paused = False
        self._loaded_path: str | None = None
        if PLAYER_AVAILABLE:
            try:
                pygame.mixer.init()
                self._ready = True
            except Exception:  # noqa: BLE001 — немає звукового пристрою тощо
                self._ready = False

    @property
    def available(self) -> bool:
        return self._ready

    @property
    def loaded_path(self) -> str | None:
        return self._loaded_path

    def load(self, path: str) -> None:
        """Лише завантажує файл (курсор на початок), НЕ починає
        відтворення — щоб генерація MP3 більше не запускала звук
        автоматично. Щоб почати грати, викликати play() окремо."""
        if not self._ready:
            raise PlayerError("Аудіоплеєр недоступний (pygame не встановлено або немає звукового пристрою).")
        try:
            pygame.mixer.music.load(path)
            self._paused = False
            self._loaded_path = path
        except Exception as exc:  # noqa: BLE001
            raise PlayerError(f"Не вдалося відкрити файл: {exc}") from exc

    def unload(self) -> None:
        """Явно звільняє файл, завантажений у плеєр. КРИТИЧНО важливо
        викликати це перед тим, як щось інше (напр. FFmpeg) спробує
        ПЕРЕЗАПИСАТИ той самий файл — інакше Windows тримає дескриптор
        зайнятим через pygame/SDL_mixer, і запис падає з "Permission
        denied", навіть коли відтворення вже зупинено через stop()."""
        if not self._ready:
            return
        self.stop()
        unload_fn = getattr(pygame.mixer.music, "unload", None)
        if unload_fn is not None:
            try:
                unload_fn()
            except Exception:  # noqa: BLE001 — best-effort, немає що вдіяти далі
                pass
        self._loaded_path = None

    def play(self) -> None:
        """Починає відтворення з початку завантаженого файлу, або
        продовжує з місця паузи, якщо було поставлено на паузу."""
        if not self._ready:
            return
        if self._paused:
            pygame.mixer.music.unpause()
            self._paused = False
        else:
            pygame.mixer.music.play()

    def pause(self) -> None:
        if self._ready and pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self._paused = True

    def stop(self) -> None:
        if self._ready:
            pygame.mixer.music.stop()
            self._paused = False

    def is_busy(self) -> bool:
        return self._ready and pygame.mixer.music.get_busy()

    def position_seconds(self) -> float:
        """Скільки секунд від початку відтворення. pygame не дає точну
        загальну тривалість треку без додаткової бібліотеки (mutagen) —
        тому показуємо лише пройдений час, без "/ загальна тривалість"."""
        if not self._ready:
            return 0.0
        ms = pygame.mixer.music.get_pos()
        return max(ms, 0) / 1000.0
