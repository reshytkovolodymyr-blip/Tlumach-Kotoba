"""
session.py
----------
LessonSession — структура одного уроку.
SessionManager — гарантує, що в програмі в кожен момент часу існує
РІВНО ОДИН активний урок (CURRENT SESSION), і всі вправи використовують
тільки його.

Архітектурні рішення, які закривають неоднозначності технічного
завдання (docx):

  - Поля "vocabulary" і "translations" з чернетки ТЗ прибрано —
    вони ніде не мали чіткого визначення і дублювали "phrases".
    Переклад фрази — це просто необов'язкове поле meaning_uk
    всередині Phrase (parser.py), так само як і для English-версії.

  - "practice" (пари питання-відповідь для Recall) НІКОЛИ не
    зберігається в LessonSession і не є частиною JSON-моделі —
    це завжди похідні дані, що обчислюються на льоту з dialogue
    (властивість practice_pairs нижче). Це відповідає розділу 17
    ТЗ ("exercise_generator.py — вправи з current_session") і усуває
    суперечність зі старою моделлю, де practice виглядав як
    збережене поле.

  - speaker_voices: {ім'я спікера: "male" | "female"}. Стать
    призначається ВИКЛЮЧНО вручну через GUI (жодного автовизначення
    статі за іменем), і зберігається разом з уроком, щоб при
    повторному відкритті з History не доводилось призначати заново.

  - resolved_voices / resolved_native_voice — ЕФЕМЕРНІ поля (не
    зберігаються в to_dict()/JSON/SQLite). Конкретна модель голосу
    (напр. "en-US-DavisNeural") у межах обраної статі підбирається
    автоматично, випадково, exercises.py (languages.pick_voice) — і
    кешується тут, щоб той самий спікер звучав ОДНАКОВО у всіх файлах,
    згенерованих для цього конкретного екземпляра сесії (Full Dialogue
    і Shadowing одного уроку не повинні звучати різними голосами).
    Новий екземпляр сесії (новий розбір діалогу чи повторне завантаження
    з History) отримує новий випадковий вибір.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from .japanese_reading import JapaneseReadingProvider
from .languages import get_language
from .parser import DialogueLine, DialogueParser, Phrase


@dataclass
class QAPair:
    prompt_speaker: str
    prompt_text: str
    answer_speaker: str
    answer_text: str


@dataclass
class LessonSession:
    title: str
    target_language: str       # "english" | "japanese" (languages.py)
    level: str
    created: str
    dialogue: List[DialogueLine] = field(default_factory=list)
    phrases: List[Phrase] = field(default_factory=list)
    speaker_voices: Dict[str, str] = field(default_factory=dict)  # ім'я -> "male"/"female"
    raw_text: str = ""          # ПОВНИЙ оригінальний текст від AI, як вставив користувач
    id: Optional[int] = None
    resolved_voices: Dict[str, str] = field(default_factory=dict, repr=False)   # ефемерне, НЕ зберігається
    resolved_native_voice: str = field(default="", repr=False)                  # ефемерне, НЕ зберігається

    @property
    def practice_pairs(self) -> List[QAPair]:
        """Пари 'питання-відповідь' для Recall / Reverse Recall — завжди
        обчислюються з self.dialogue, ніколи не зберігаються окремо."""
        pairs: List[QAPair] = []
        d = self.dialogue
        for i in range(0, len(d) - 1, 2):
            pairs.append(QAPair(
                prompt_speaker=d[i].speaker, prompt_text=d[i].text,
                answer_speaker=d[i + 1].speaker, answer_text=d[i + 1].text,
            ))
        return pairs

    def unique_speakers(self) -> List[str]:
        """Список унікальних імен спікерів у порядку першої появи в діалозі.
        Використовується GUI для побудови панелі призначення голосів."""
        seen: List[str] = []
        for line in self.dialogue:
            if line.speaker not in seen:
                seen.append(line.speaker)
        return seen

    def missing_speaker_voices(self) -> List[str]:
        """Спікери, яким ще НЕ призначено стать вручну. Валідні значення —
        рівно "male" або "female"; будь-яке інше значення (порожньо,
        чи, скажімо, залишок формату з конкретним voice_id) трактується
        як "не призначено"."""
        return [s for s in self.unique_speakers() if self.speaker_voices.get(s) not in ("male", "female")]

    def set_speaker_gender(self, speaker: str, gender: str) -> None:
        """ЄДИНИЙ правильний спосіб призначити стать спікеру — робить
        це замість прямого self.speaker_voices[speaker] = ... навмисно,
        щоб гарантувати інвалідацію кешу.

        Реальний баг, який це виправляє: якщо стать УЖЕ була призначена
        раніше (напр. "male") і генерація аудіо вже відбулась, у
        resolved_voices[speaker] лежить конкретна закешована модель
        голосу (напр. "en-US-GuyNeural"). Якщо потім змінити стать на
        "female" напряму через словник, кеш лишається зі СТАРИМ
        чоловічим голосом, і наступна генерація видасть його, попри
        нову обрану стать. Тому зміна статі тут ЗАВЖДИ скидає кеш для
        цього конкретного спікера, якщо стать реально змінилась."""
        if self.speaker_voices.get(speaker) != gender:
            self.resolved_voices.pop(speaker, None)
        self.speaker_voices[speaker] = gender

    def summary(self) -> dict:
        return {
            "title": self.title,
            "target_language": get_language(self.target_language).label,
            "level": self.level,
            "lines": len(self.dialogue),
            "phrases": len(self.phrases),
            "recall_pairs": len(self.practice_pairs),
            "speakers": len(self.unique_speakers()),
        }

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "target_language": self.target_language,
            "level": self.level,
            "created": self.created,
            "dialogue": [asdict(x) for x in self.dialogue],
            "phrases": [asdict(x) for x in self.phrases],
            "speaker_voices": dict(self.speaker_voices),
            "raw_text": self.raw_text,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @staticmethod
    def from_dict(data: dict) -> "LessonSession":
        return LessonSession(
            id=data.get("id"),
            title=data.get("title", "Untitled Lesson"),
            target_language=data.get("target_language", "english"),
            level=data.get("level", ""),
            created=data.get("created", datetime.now().isoformat(timespec="seconds")),
            dialogue=[DialogueLine(**x) for x in data.get("dialogue", [])],
            phrases=[Phrase(**x) for x in data.get("phrases", [])],
            speaker_voices=dict(data.get("speaker_voices", {})),
            raw_text=data.get("raw_text", ""),
        )

    @staticmethod
    def from_json(raw: str) -> "LessonSession":
        return LessonSession.from_dict(json.loads(raw))


class SessionManager:
    """
    Утримує ЄДИНИЙ current_session — джерело істини для всієї програми.
    ExerciseGenerator, AudioAssembler та GUI завжди беруть дані звідси.
    """

    def __init__(self, reading_provider: Optional[JapaneseReadingProvider] = None):
        self._current: Optional[LessonSession] = None
        self.reading_provider = reading_provider or JapaneseReadingProvider()

    @property
    def current(self) -> Optional[LessonSession]:
        return self._current

    def has_session(self) -> bool:
        return self._current is not None

    def create_from_text(self, raw_text: str, title: str, level: str, target_language: str) -> LessonSession:
        """
        Розбирає НОВИЙ текст і робить результат поточним уроком.

        Це єдина точка входу для створення CURRENT SESSION з тексту.
        Результат ЗАВЖДИ повністю замінює попередній self._current.
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("EMPTY_TEXT")

        parsed = DialogueParser.parse(raw_text)
        if not parsed.dialogue:
            raise ValueError("NO_DIALOGUE_FOUND")

        lang_cfg = get_language(target_language)
        if lang_cfg.needs_romaji:
            self._attach_readings(parsed)

        session = LessonSession(
            title=title.strip() or "Untitled Lesson",
            target_language=target_language,
            level=level,
            created=datetime.now().isoformat(timespec="seconds"),
            dialogue=parsed.dialogue,
            phrases=parsed.phrases,
            speaker_voices={},  # порожньо навмисно — голос обирається вручну в GUI
            raw_text=raw_text,
        )
        self._current = session
        return session

    def _attach_readings(self, parsed) -> None:
        """Заповнює поле reading (romaji) для японського тексту. Якщо
        pykakasi не встановлено — поля лишаються порожніми, GUI сам
        покаже попередження, romaji ніколи не вигадується."""
        if not self.reading_provider.available:
            return
        for line in parsed.dialogue:
            line.reading = self.reading_provider.romaji(line.text)
        for phrase in parsed.phrases:
            phrase.reading = self.reading_provider.romaji(phrase.phrase)

    def set_current(self, session: LessonSession) -> None:
        """Явно підміняє поточний урок (History / Import JSON). Стара
        сесія повністю відкидається."""
        self._current = session

    def clear(self) -> None:
        self._current = None
