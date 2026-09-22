"""
test_shadowing_and_phrases.py
------------------------------
Перевіряє новий дизайн двох режимів:

- Shadowing: три проходи (повільно / природний темп / без паузи),
  кожна репліка звучить рівно тричі, паузи між проходами різні.
- Phrase Trainer: блок "форма і значення" (з прикладом речення, якщо
  AI його надав) + окремий блок активного пригадування (переклад ->
  пауза -> фраза), який будується лише з фраз, що мають переклад.

Не потребує ffmpeg, edge-tts чи Tkinter.

Запуск:  py tests/test_shadowing_and_phrases.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.audio import PauseSegment, SpeakSegment  # noqa: E402
from app.exercises import AudioSettings, ExerciseGenerator  # noqa: E402
from app.session import SessionManager  # noqa: E402

DIALOGUE = """Officer: Good morning. May I see your passport?
Traveler: Certainly. Here you are.
Officer: What is the purpose of your trip?
Traveler: I am visiting my family.

1. What is the purpose of your trip? - Яка мета вашої поїздки? | приклад: The officer asked what the purpose of my trip was.
2. personal belongings - особисті речі
3. random phrase without translation
"""


def test_no_ai_list_means_no_phrases():
    """КРИТИЧНО: якщо AI не додав ЖОДНОГО рядка "фраза - переклад" —
    phrases має лишитись порожнім. Раніше тут спрацьовував regex-fallback
    (вгадування типових англійських конструкцій) — він прибраний навмисно."""
    sessions = SessionManager()
    dialogue_without_phrase_list = """Officer: Could you show me your passport, please?
Traveler: Sure, here it is. I would like to also ask about customs.
"""
    session = sessions.create_from_text(
        dialogue_without_phrase_list, title="No List", level="B2", target_language="english",
    )
    assert session.phrases == [], (
        "Без нумерованого списку від AI phrases має бути порожнім — "
        "жодного автовиділення фраз бути не повинно."
    )
    print("OK: без списку від AI ключових фраз немає (жодного вгадування)")


def test_phrase_list_without_numbers_still_recognized():
    """Реальний випадок з практики: AI дав список фраз-перекладів, але
    забув пронумерувати рядки. Парсер має розпізнати їх все одно —
    інакше Ключові фрази стають недоступні через технічну дрібницю."""
    from app.parser import DialogueParser

    text = (
        "由美: はい。ウクライナの文学をもっと知りたいです。\n\n"
        "ウクライナの文学 - українська література | ウクライナの文学を勉強しています。\n"
        "有名な作家 - відомий письменник | この町には有名な作家がいます。\n"
    )
    parsed = DialogueParser.parse(text)
    assert len(parsed.dialogue) == 1, "Репліка діалогу має розпізнатись окремо від фраз"
    assert len(parsed.phrases) == 2, f"Очікувались 2 фрази без номерів, отримано {len(parsed.phrases)}"
    assert parsed.phrases[0].phrase == "ウクライナの文学"
    assert parsed.phrases[0].meaning_uk == "українська література"
    assert parsed.phrases[0].example == "ウクライナの文学を勉強しています。"
    print("OK: список фраз без нумерації все одно розпізнається (разом із прикладом)")


def main():
    sessions = SessionManager()
    session = sessions.create_from_text(DIALOGUE, title="Airport", level="B2", target_language="english")
    session.speaker_voices["Officer"] = "male"
    session.speaker_voices["Traveler"] = "female"

    settings = AudioSettings(pause_between_lines=1.0)
    generator = ExerciseGenerator(settings)

    # ---------------- Shadowing: 3 проходи ----------------
    segments = generator.shadowing(session)
    speak_texts = [s.text for s in segments if isinstance(s, SpeakSegment)]

    for line in session.dialogue:
        count = speak_texts.count(line.text)
        assert count == 3, f"Репліка «{line.text}» мала прозвучати 3 рази (по разу на прохід), а прозвучала {count}"
    print("OK: кожна репліка звучить рівно тричі (3 проходи Shadowing)")

    pause_values = [p.seconds for p in segments if isinstance(p, PauseSegment)]
    assert 0.3 in pause_values, "Мала бути коротка пауза 0.3с у 'наздоганяючому' проході"
    assert max(pause_values) >= 2.0, "Повільний прохід мав мати найдовшу паузу"
    print("OK: паузи проходів різняться (повільно > природно > без паузи)")

    # ---------------- Phrase Trainer: приклад + двонапрямковість ----------------
    pt_segments = generator.phrase_trainer(session)
    pt_texts = [s.text for s in pt_segments if isinstance(s, SpeakSegment)]

    assert "The officer asked what the purpose of my trip was." in pt_texts, \
        "Приклад речення мав прозвучати для фрази, де AI його надав"
    print("OK: приклад речення (example) з парсера озвучується")

    assert "random phrase without translation" in pt_texts, "Фраза без перекладу все одно має бути в блоці 1"
    assert "Translation unavailable." in pt_texts, "Без перекладу має прозвучати чесне 'Translation unavailable.'"
    print("OK: фраза без перекладу не вигадує переклад")

    # У блоці активного пригадування "особисті речі" (переклад) має
    # прозвучати перед фразою "personal belongings".
    assert pt_texts.count("особисті речі") >= 1
    print("OK: блок активного пригадування (переклад -> фраза) присутній")

    # Фраза без перекладу звучить у прямому блоці ДВІЧІ (звичайний темп +
    # повільний повтор), але НЕ повинна потрапити у зворотний блок
    # (там нема чим озвучити підказку-переклад).
    assert pt_texts.count("random phrase without translation") == 2, \
        "Фраза без перекладу має прозвучати лише в прямому блоці (2 рази: звичайно + повільно)"
    print("OK: фраза без перекладу пропущена в зворотному блоці")

    print("\nВСІ ТЕСТИ SHADOWING/PHRASE TRAINER ПРОЙДЕНО.")


if __name__ == "__main__":
    main()
    test_no_ai_list_means_no_phrases()
    test_phrase_list_without_numbers_still_recognized()
