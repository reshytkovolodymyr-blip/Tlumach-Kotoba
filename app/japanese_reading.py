"""
japanese_reading.py
--------------------
Автоматична романізація (romaji) японського тексту через pykakasi —
офлайн Python-бібліотеку з відкритим кодом (MIT). Дані для конвертації
постачаються разом із пакетом: Internet потрібен лише один раз, під
час `pip install pykakasi`, а НЕ під час роботи програми.

Це НЕ переклад: romaji — однозначна фонетична транслітерація того
самого тексту, що звучить в аудіо. Тому це не порушує головне правило
проєкту "не вигадувати переклад" — значення (meaning_uk) і надалі
береться тільки якщо користувач сам додав його в текст (parser.py).
"""

from __future__ import annotations

try:
    import pykakasi
    PYKAKASI_AVAILABLE = True
except ImportError:  # pragma: no cover — залежить від встановленого оточення
    pykakasi = None
    PYKAKASI_AVAILABLE = False


class JapaneseReadingProvider:
    """Тонка обгортка над pykakasi.kakasi(). Один екземпляр варто
    перевикористовувати — ініціалізація конвертера дорожча за сам виклик."""

    def __init__(self):
        self._kks = pykakasi.kakasi() if PYKAKASI_AVAILABLE else None

    @property
    def available(self) -> bool:
        return self._kks is not None

    def romaji(self, text: str) -> str:
        """Повертає латинізовану (Hepburn) вимову japanese-тексту.

        Якщо pykakasi не встановлено — повертає порожній рядок:
        GUI в такому разі показує позначку "romaji недоступний",
        а не вигаданий текст.
        """
        if not text or not text.strip() or not self.available:
            return ""
        result = self._kks.convert(text)
        return " ".join(item["hepburn"] for item in result if item.get("hepburn"))
