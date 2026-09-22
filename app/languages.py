"""
languages.py
------------
Централізована конфігурація мов, які підтримує застосунок.

Кожна мова має СПИСОК голосів на стать (пул), з якого програма сама
випадково обирає КОНКРЕТНУ модель голосу — користувач обирає лише
стать (чоловічий/жіночий), а яка саме модель залучена — не бачить і
не обирає. Це свідоме рішення: різноманітність без додаткового
навантаження на користувача (див. pick_voice/pick_native_voice нижче).

⚠️ ВАЖЛИВО — чому пул зараз саме такий (по одному голосу на стать):
Раніше тут був розширений пул (Davis, Jason, Tony, Daichi, Aoi...),
перевірений через ОФІЦІЙНУ Azure Cognitive Services документацію.
Це була помилка: edge-tts — НЕОФІЦІЙНА бібліотека, яка звертається до
вужчого внутрішнього сервісу "Читати вголос" у Microsoft Edge, а не
до платного Azure API. Належність голосу до офіційного каталогу Azure
НЕ означає, що він доступний саме через edge-tts. Розширений пул
призводив до постійної помилки "Не вдалося підключитися до TTS" для
голосів поза вузьким набором, який edge-tts реально підтримує.

Тому зараз лишені ЛИШЕ голоси, які підтверджено працювали в цьому
застосунку (Guy/Jenny, Keita/Nanami) — це навмисне звуження, а не
недогляд. Якщо колись знадобиться розширити пул для різноманітності —
ЄДИНИЙ надійний спосіб перевірити кандидата: запустити на машині з
Internet команду

    edge-tts --list-voices | findstr "en-US ja-JP"

і додавати сюди лише голоси з РЕАЛЬНОГО виводу цієї команди, а не з
документації Azure чи будь-якого стороннього списку.

Додати нову мову вивчення в майбутньому — один новий запис у
TARGET_LANGUAGES, без змін у tts.py/exercises.py/gui.py.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class LanguageConfig:
    code: str                        # внутрішній ідентифікатор, напр. "english"
    label: str                        # назва для GUI, напр. "English"
    voices: Dict[str, List[str]]      # {"male": [voice_id, ...], "female": [...]}
    levels: List[str] = field(default_factory=list)
    needs_romaji: bool = False


TARGET_LANGUAGES: Dict[str, LanguageConfig] = {
    "english": LanguageConfig(
        code="english",
        label="English",
        voices={
            # Лише підтверджено робочі в edge-tts голоси. НЕ додавати сюди
            # нові voice_id без реальної перевірки через
            # `edge-tts --list-voices` (див. пояснення на початку файлу).
            "male": ["en-US-GuyNeural"],
            "female": ["en-US-JennyNeural"],
        },
        levels=["A2", "B1", "B2", "C1"],
        needs_romaji=False,
    ),
    "japanese": LanguageConfig(
        code="japanese",
        label="Japanese (日本語)",
        voices={
            # Те саме застереження — лише підтверджено робочі голоси.
            "male": ["ja-JP-KeitaNeural"],
            "female": ["ja-JP-NanamiNeural"],
        },
        levels=["N5", "N4", "N3", "N2", "N1"],
        needs_romaji=True,
    ),
    "french": LanguageConfig(
        code="french",
        label="Français",
        voices={
            # Перевірено через кілька незалежних дампів РЕАЛЬНОГО виводу
            # edge-tts --list-voices (не документацію Azure) — той самий
            # стандарт, що й для English/Japanese вище.
            "male": ["fr-FR-HenriNeural"],
            "female": ["fr-FR-DeniseNeural"],
        },
        levels=["A2", "B1", "B2", "C1"],
        needs_romaji=False,
    ),
    "spanish": LanguageConfig(
        code="spanish",
        label="Español",
        voices={
            "male": ["es-ES-AlvaroNeural"],
            "female": ["es-ES-ElviraNeural"],
        },
        levels=["A2", "B1", "B2", "C1"],
        needs_romaji=False,
    ),
}

# Рідна мова користувача (аудиторія застосунку — україномовна). В
# edge-tts лише два голоси uk-UA — програма автоматично чергує між
# ними (pick_native_voice), користувач цей вибір не бачить і не робить.
NATIVE_LANGUAGE_VOICES: Dict[str, str] = {
    "female": "uk-UA-PolinaNeural",
    "male": "uk-UA-OstapNeural",
}


def get_language(code: str) -> LanguageConfig:
    try:
        return TARGET_LANGUAGES[code]
    except KeyError:
        raise ValueError(f"Непідтримувана мова вивчення: {code}") from None


def language_labels() -> List[str]:
    return [cfg.label for cfg in TARGET_LANGUAGES.values()]


def code_by_label(label: str) -> str:
    for cfg in TARGET_LANGUAGES.values():
        if cfg.label == label:
            return cfg.code
    return next(iter(TARGET_LANGUAGES))


def pick_voice(language_code: str, gender: str) -> str:
    """Випадково обирає КОНКРЕТНИЙ voice_id у межах обраної користувачем
    статі. Викликається з exercises.py при генерації аудіо — користувач
    бачить і обирає лише стать, конкретна модель голосу підбирається
    автоматично, без його відома."""
    cfg = get_language(language_code)
    pool = cfg.voices.get(gender)
    if not pool:
        raise ValueError(f"Немає голосів для {language_code}/{gender}")
    return random.choice(pool)


def pick_native_voice() -> str:
    """Те саме для голосу перекладу (рідна мова) — автоматично між
    наявними українськими голосами (Остап/Поліна)."""
    return random.choice(list(NATIVE_LANGUAGE_VOICES.values()))

