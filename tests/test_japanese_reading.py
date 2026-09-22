"""
test_japanese_reading.py
--------------------------
Перевіряє: (1) романізацію через pykakasi, якщо він встановлений;
(2) що сесія японською мовою коректно отримує поле reading для кожної
репліки і фрази; (3) що голоси спікерів для Japanese автоматично
беруться з японського пулу голосів languages.py, а не з англійського.

Якщо pykakasi не встановлено — тест пропускається (не падає), бо
відсутність необов'язкової залежності — не помилка архітектури.

Запуск:  py tests/test_japanese_reading.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.exercises import AudioSettings, ExerciseGenerator  # noqa: E402
from app.japanese_reading import PYKAKASI_AVAILABLE  # noqa: E402
from app.languages import get_language  # noqa: E402
from app.session import SessionManager  # noqa: E402

JAPANESE_DIALOGUE = """田中: おはようございます。
鈴木: おはようございます。元気です。
"""


def main():
    if not PYKAKASI_AVAILABLE:
        print("ПРОПУЩЕНО: pykakasi не встановлено (pip install pykakasi).")
        return

    sessions = SessionManager()
    session = sessions.create_from_text(
        JAPANESE_DIALOGUE, title="Japanese Greetings", level="N5", target_language="japanese",
    )

    for line in session.dialogue:
        assert line.reading, f"Очікувався romaji для рядка: {line.text}"
        print(f"OK: {line.speaker}: {line.text} -> [{line.reading}]")

    session.speaker_voices["田中"] = "male"
    session.speaker_voices["鈴木"] = "female"

    generator = ExerciseGenerator(AudioSettings())
    segments = generator.full_dialogue(session)
    voices_used = {s.voice for s in segments if hasattr(s, "voice")}
    lang = get_language("japanese")
    assert voices_used & set(lang.voices["male"]), "Мав використовуватись один із японських чоловічих голосів"
    assert voices_used & set(lang.voices["female"]), "Мав використовуватись один із японських жіночих голосів"
    assert not any(v.startswith("en-US") for v in voices_used), "Не повинно бути англійських голосів"

    print("OK: для japanese-сесії використано японські голоси (не англійські).")
    print("\nВСІ ТЕСТИ РОМАНІЗАЦІЇ ПРОЙДЕНО.")


if __name__ == "__main__":
    main()
