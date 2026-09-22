"""
tts.py
------
Абстракція TTS-рушія. Основний двигун — edge-tts (хмарний сервіс
Microsoft Edge, потребує Internet). Конкретні ідентифікатори голосів
для кожної мови навмисно НЕ тут — вони в languages.py, щоб додавання
нової мови не чіпало цей модуль.

TTSEngine дозволяє в майбутньому додати інші рушії (Piper, локальний
TTS тощо) без переписування решти програми.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:  # pragma: no cover
    edge_tts = None
    EDGE_TTS_AVAILABLE = False


class TTSError(Exception):
    """Помилка озвучення: немає рушія, немає Internet тощо."""


class TTSEngine(ABC):
    @abstractmethod
    async def synth_async(self, text: str, voice: str, rate: str, out_path: Path) -> None:
        ...

    def synth(self, text: str, voice: str, rate: str, out_path: Path) -> None:
        asyncio.run(self.synth_async(text, voice, rate, out_path))


class EdgeTTSEngine(TTSEngine):
    """Реалізація на основі edge-tts (хмарний сервіс Microsoft).
    Підтримує будь-яку мову, для якої є голос у каталозі edge-tts —
    саме тому вибір конкретного voice-id винесено в languages.py."""

    async def synth_async(self, text: str, voice: str, rate: str, out_path: Path) -> None:
        if not EDGE_TTS_AVAILABLE:
            raise TTSError("Не встановлено пакет edge-tts. Виконайте: pip install edge-tts")
        if not text or not text.strip():
            return
        try:
            communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
            await communicate.save(str(out_path))
        except Exception as exc:  # noqa: BLE001 — навмисно ловимо всі мережеві помилки
            raise TTSError("Не вдалося підключитися до TTS. Перевірте Internet.") from exc


class TTSManager:
    """Фасад, яким користується решта програми. Приховує вибір рушія."""

    def __init__(self, engine: TTSEngine | None = None):
        self.engine: TTSEngine = engine or EdgeTTSEngine()

    def synth(self, text: str, voice: str, rate: str, out_path: Path) -> None:
        self.engine.synth(text, voice, rate, out_path)
