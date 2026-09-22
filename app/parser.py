"""
parser.py
---------
DialogueParser перетворює довільний текст (зазвичай згенерований AI)
на структуровані дані: репліки діалогу та ключові фрази.

Парсер НЕ прив'язаний ні до конкретних імен персонажів (Officer/
Traveler тощо), ні до конкретної мови — регулярний вираз "Speaker: text"
працює однаково для латиниці й для японських символів (田中: text).

Парсер НІЧОГО не знає про TTS, романізацію чи мову вивчення — це
свідоме архітектурне рішення: поле `reading` тут завжди порожнє,
його заповнює session.py окремим кроком лише для мов, яким це
потрібно (japanese_reading.py). Так parser.py лишається придатним
для будь-якої майбутньої мови без змін.
"""

from __future__ import annotations

import re
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class DialogueLine:
    speaker: str
    text: str
    reading: str = ""  # romaji тощо; заповнюється поза парсером


@dataclass
class Phrase:
    phrase: str
    meaning_uk: str = ""
    example: str = ""
    reading: str = ""  # romaji тощо; заповнюється поза парсером


@dataclass
class ParsedLesson:
    dialogue: List[DialogueLine] = field(default_factory=list)
    phrases: List[Phrase] = field(default_factory=list)


# "Speaker: repl.ka" — ім'я мовця до 40 символів, без символу ":"
_SPEAKER_RE = re.compile(r"^([^:\n]{1,40}):\s*(.+)$")

# Евристика для "злиплих" реплік: AI іноді забуває розрив рядка між
# двома репліками, і вони опиняються в ОДНОМУ рядку. Шукаємо ознаку —
# ще один патерн "Ім'я: " ПОСЕРЕД УЖЕ розпізнаної репліки (не на
# початку — початок і так вже "з'їдений" _SPEAKER_RE). Це евристика,
# не гарантія: ловить конкретний поширений випадок, а не будь-яку
# помилку вводу.
_EMBEDDED_SPEAKER_RE = re.compile(
    r"(?<=\s)([A-Za-zА-Яа-яІіЇїЄєҐґ]{2,30}):\s+(?=[A-ZА-ЯІЇЄ])"
)


def find_glued_speaker_marker(text: str) -> Optional[str]:
    """Повертає ім'я, знайдене ВСЕРЕДИНІ репліки (ознака, що дві репліки
    злиплись в один рядок без переносу), або None, якщо підозрілого
    патерну не знайдено. Використовується GUI для дружнього
    попередження користувачу — саме розбір діалогу це не блокує."""
    match = _EMBEDDED_SPEAKER_RE.search(text)
    return match.group(1) if match else None

# Нумерований рядок ключової фрази: "1. phrase" / "1) phrase"
_NUMBERED_RE = re.compile(r"^\d+[.)]\s*(.+)$")

# Кирилиця — використовується, щоб НЕ вигадувати переклад,
# а брати його лише якщо користувач сам додав його в тексті.
_CYRILLIC_RE = re.compile(r"[а-яА-ЯіІїЇєЄґҐ]")

# Приклад речення після фрази, якщо AI його додав:
# "1. phrase - переклад | приклад: повне речення"
_EXAMPLE_RE = re.compile(r"(?:приклад|example)\s*:\s*(.+)$", re.IGNORECASE)

# Рядок ключової фрази БЕЗ номера — на випадок, якщо AI забув
# пронумерувати список (частий випадок на практиці): "phrase - переклад".
_LOOSE_PHRASE_RE = re.compile(r"^[^:]+\s+[-—–]\s+.+$")


class DialogueParser:
    """Розбирає сирий текст у структуру ParsedLesson. Чиста функція без
    побічних ефектів — однаковий вхід завжди дає однаковий вихід.

    КРИТИЧНО: ключові фрази беруться ВИКЛЮЧНО з тексту, який надав AI
    ("фраза - переклад", з номером чи без). Парсер НЕ намагається сам
    вгадувати "корисні фрази" з реплік діалогу — раніше тут був
    regex-fallback для англійської (пошук патернів на кшталт
    "Could you", "I'd like to"), він свідомо прибраний: це було
    вгадування, а не аналіз, і працювало лише для однієї мови. Якщо AI
    не додав жодного рядка "фраза - переклад" — phrases лишається
    порожнім, і GUI чесно повідомляє про це, а не підсовує вигадані
    фрази. Нумерація ("1.") НЕ обов'язкова — AI часто її забуває,
    тому розпізнається і рядок без номера, якщо він має форму
    "фраза - переклад" і не є реплікою діалогу (без символу ":")."""

    @staticmethod
    def parse(raw_text: str) -> ParsedLesson:
        lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]

        dialogue: List[DialogueLine] = []
        phrases: List[Phrase] = []

        for line in lines:
            numbered_match = _NUMBERED_RE.match(line)
            speaker_match = _SPEAKER_RE.match(line)

            if numbered_match:
                phrases.append(DialogueParser._parse_phrase_line(numbered_match.group(1)))
            elif speaker_match:
                speaker = speaker_match.group(1).strip()
                text = speaker_match.group(2).strip()
                if speaker and text:
                    dialogue.append(DialogueLine(speaker=speaker, text=text))
            elif DialogueParser._looks_like_phrase_line(line):
                phrases.append(DialogueParser._parse_phrase_line(line))

        return ParsedLesson(dialogue=dialogue, phrases=phrases)

    @staticmethod
    def _looks_like_phrase_line(line: str) -> bool:
        """Рядок без номера трактуємо як фразу, лише якщо: (1) це НЕ
        репліка діалогу (немає ":" — інакше це вже перехопив би
        _SPEAKER_RE вище), (2) є роздільник " - ", і (3) десь у рядку
        є кирилиця (інакше немає підстав вважати це парою
        фраза-переклад, а не просто випадковим реченням)."""
        if ":" in line:
            return False
        if not _LOOSE_PHRASE_RE.match(line):
            return False
        return bool(_CYRILLIC_RE.search(line))

    @staticmethod
    def _parse_phrase_line(body: str) -> Phrase:
        """КРИТИЧНО: переклад додається ТІЛЬКИ якщо він реально присутній
        у вхідному тексті (виявлений кирилицею). Програма ніколи не
        вигадує переклад сама. Приклад речення (example) береться з
        усього, що йде після "|" — з міткою "приклад:"/"example:" або
        й без неї (AI не завжди її додає, але текст після "|" усе одно
        реальний, написаний AI, а не вигаданий програмою)."""
        body = body.strip()

        example = ""
        if "|" in body:
            main_part, _, tail = body.partition("|")
            body = main_part.strip()
            tail = tail.strip()
            m = _EXAMPLE_RE.search(tail)
            example = m.group(1).strip() if m else tail

        parts = re.split(r"\s+[-—–]\s+", body, maxsplit=1)
        if len(parts) == 2 and _CYRILLIC_RE.search(parts[1]):
            return Phrase(phrase=parts[0].strip(), meaning_uk=parts[1].strip(), example=example)

        paren = re.match(r"^(.*?)\(([^)]+)\)\s*$", body)
        if paren and _CYRILLIC_RE.search(paren.group(2)):
            return Phrase(phrase=paren.group(1).strip(), meaning_uk=paren.group(2).strip(), example=example)

        return Phrase(phrase=body, example=example)
