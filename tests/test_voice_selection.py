"""
test_voice_selection.py
-------------------------
Перевіряє нову (поточну) архітектуру вибору голосу:

1. У кожній мові декілька голосів на стать (є з чого автоматично
   обирати — інакше "автоматичний вибір" був би фікцією).
2. Стать обирається ВИКЛЮЧНО вручну ("male"/"female"); будь-яке інше
   значення (порожньо, залишок формату з конкретним voice_id тощо)
   трактується як "не призначено".
3. Конкретна МОДЕЛЬ голосу в межах обраної статі підбирається
   автоматично (pick_voice), без участі й без відома користувача.
4. У межах ОДНОГО екземпляра сесії конкретна модель лишається сталою
   між кількома генераціями різних режимів того самого уроку.
5. Голос перекладу (рідна мова) так само автоматичний — один із
   наявних українських голосів (Остап/Поліна), сталий на весь урок.

Не потребує ffmpeg, edge-tts чи Tkinter.

Запуск:  py tests/test_voice_selection.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.audio import SpeakSegment  # noqa: E402
from app.exercises import AudioSettings, ExerciseGenerator, MissingVoiceError  # noqa: E402
from app.languages import NATIVE_LANGUAGE_VOICES, get_language, pick_voice  # noqa: E402
from app.session import SessionManager  # noqa: E402

DIALOGUE = """Officer: Good morning.
Traveler: Good morning to you too.
"""

DIALOGUE_WITH_PHRASE = (
    "Officer: What is your name?\n"
    "Traveler: John Smith.\n\n"
    "What is your name? - Як вас звати?\n"
)


def test_each_gender_has_at_least_one_voice():
    """Пул наразі звужений до РІВНО ОДНОГО підтверджено робочого голосу
    на стать (Guy/Jenny, Keita/Nanami) — це свідоме рішення на користь
    надійності після інциденту з невалідними voice_id (частина голосів,
    перевірених лише через офіційну Azure-документацію, насправді не
    підтримувалась вужчим неофіційним edge-tts, і TTS постійно
    відмовляв з'єднання). Тест лише гарантує, що пул не порожній —
    коли пул розшириться (після реальної перевірки через
    `edge-tts --list-voices`), test_voice_pool_variety нижче сам
    почне змістовно перевіряти різноманітність."""
    for code in ("english", "japanese"):
        cfg = get_language(code)
        assert len(cfg.voices["male"]) >= 1, f"{code}: немає жодного чоловічого голосу"
        assert len(cfg.voices["female"]) >= 1, f"{code}: немає жодного жіночого голосу"
    print("OK: у кожній мові є хоча б один підтверджено робочий голос на стать")


def test_invalid_gender_value_treated_as_missing():
    """Якщо в speaker_voices опиниться щось, окрім 'male'/'female'
    (напр. залишок формату з конкретним voice_id) — це має трактуватись
    як 'не призначено', а не як готовий голос."""
    sessions = SessionManager()
    session = sessions.create_from_text(DIALOGUE, title="Invalid", level="B2", target_language="english")
    session.speaker_voices["Officer"] = "en-US-DavisNeural"  # НЕ стать — некоректне значення
    session.speaker_voices["Traveler"] = "female"

    missing = session.missing_speaker_voices()
    assert missing == ["Officer"], f"Очікувався лише Officer як 'не призначено', отримано {missing}"

    generator = ExerciseGenerator(AudioSettings())
    try:
        generator.full_dialogue(session)
        raise AssertionError("Мало бути MissingVoiceError через некоректне значення в Officer!")
    except MissingVoiceError:
        pass
    print("OK: значення, що не є 'male'/'female', трактується як 'не призначено'")


def test_voice_model_is_picked_automatically_and_stays_consistent():
    """Користувач обирає лише стать. Конкретна модель — автоматично,
    і лишається СТАЛОЮ для цього спікера в межах одного екземпляра
    сесії (щоб Officer не міняв голос між Full Dialogue і Shadowing
    того самого уроку)."""
    sessions = SessionManager()
    session = sessions.create_from_text(DIALOGUE, title="Auto", level="B2", target_language="english")
    session.speaker_voices["Officer"] = "male"
    session.speaker_voices["Traveler"] = "female"

    generator = ExerciseGenerator(AudioSettings())
    lang = get_language("english")

    segments_full = generator.full_dialogue(session)
    voices_full = {s.voice for s in segments_full if isinstance(s, SpeakSegment)}
    assert voices_full & set(lang.voices["male"]), "Мав використовуватись один із чоловічих голосів пулу"
    assert voices_full & set(lang.voices["female"]), "Мав використовуватись один із жіночих голосів пулу"

    officer_voice = session.resolved_voices["Officer"]
    assert officer_voice in lang.voices["male"], "Обраний голос має бути з чоловічого пулу"

    # Друга генерація (інший режим) ТОГО САМОГО екземпляра сесії —
    # голос Officer має лишитись тим самим.
    segments_shadow = generator.shadowing(session)
    officer_voices_in_shadow = {
        s.voice for s in segments_shadow
        if isinstance(s, SpeakSegment) and s.voice in lang.voices["male"]
    }
    assert officer_voices_in_shadow == {officer_voice}, (
        "Голос спікера не повинен змінюватись між генераціями одного уроку"
    )
    print("OK: конкретна модель голосу підбирається автоматично й лишається сталою в межах уроку")


def test_voice_pool_variety_or_stability():
    """Новий екземпляр сесії (новий розбір діалогу) МОЖЕ отримати новий
    випадковий вибір — але лише якщо пул для цієї статі/мови реально
    містить більше одного підтвердженого голосу. З поточним звуженим
    пулом (по одному голосу на стать, див. languages.py) очікувано
    ЗАВЖДИ той самий голос — це не баг, це прямий наслідок пулу
    розміром 1. Тест написаний так, щоб автоматично почати перевіряти
    справжню варіативність, щойно пул розшириться підтвердженими
    голосами, а не ламатись при цьому."""
    lang = get_language("english")
    pool_size = len(lang.voices["male"])
    seen = set()
    for _ in range(30):
        sessions = SessionManager()
        session = sessions.create_from_text(DIALOGUE, title="X", level="B2", target_language="english")
        session.speaker_voices["Officer"] = "male"
        session.speaker_voices["Traveler"] = "female"
        generator = ExerciseGenerator(AudioSettings())
        generator.full_dialogue(session)
        seen.add(session.resolved_voices["Officer"])

    assert seen.issubset(set(lang.voices["male"])), f"Усі обрані голоси мають бути з пулу, отримано {seen}"

    if pool_size > 1:
        assert len(seen) > 1, (
            f"За 30 незалежних сесій мав трапитись хоча б два різні голоси "
            f"(пул налічує {pool_size} варіантів), отримано лише {seen}"
        )
        print(f"OK: різні екземпляри сесії дійсно отримують різні голоси (побачено {len(seen)} варіантів)")
    else:
        assert len(seen) == 1, "З пулом розміром 1 голос має бути завжди той самий"
        print(f"OK: пул розміром 1 — очікувано завжди той самий голос ({seen}); "
              f"тест почне перевіряти різноманітність, щойно пул розшириться")


def test_native_voice_picked_automatically_and_consistent():
    """Голос перекладу (рідна мова) — автоматичний, один із наявних
    українських голосів, сталий на весь урок."""
    sessions = SessionManager()
    session = sessions.create_from_text(
        DIALOGUE_WITH_PHRASE, title="Native", level="B2", target_language="english",
    )
    session.speaker_voices["Officer"] = "male"
    session.speaker_voices["Traveler"] = "female"

    generator = ExerciseGenerator(AudioSettings())
    segments = generator.phrase_trainer(session)
    native_used = {
        s.voice for s in segments
        if isinstance(s, SpeakSegment) and s.voice in NATIVE_LANGUAGE_VOICES.values()
    }
    assert len(native_used) == 1, f"Мав використовуватись рівно один голос перекладу, отримано {native_used}"
    print("OK: голос перекладу автоматично обирається з наявних українських голосів (Остап/Поліна)")


def test_pick_voice_uses_pool():
    """pick_voice() завжди повертає voice_id саме з пулу відповідної статі."""
    lang = get_language("english")
    for _ in range(20):
        assert pick_voice("english", "male") in lang.voices["male"]
        assert pick_voice("english", "female") in lang.voices["female"]
    print("OK: pick_voice() завжди в межах пулу голосів обраної статі")


def test_changing_gender_invalidates_voice_cache():
    """РЕАЛЬНИЙ БАГ, знайдений на практиці: якщо стать спікера ЗМІНИТИ
    після того, як для нього вже закешовано конкретний голос
    (resolved_voices), наступна генерація має видати голос із НОВОГО
    пулу статі, а не залишок старого кешу. Виправлення —
    LessonSession.set_speaker_gender(), єдиний правильний спосіб
    змінювати стать (замість прямого запису в speaker_voices)."""
    lang = get_language("english")
    sessions = SessionManager()
    session = sessions.create_from_text(DIALOGUE, title="CacheBug", level="B2", target_language="english")

    session.set_speaker_gender("Officer", "male")
    session.set_speaker_gender("Traveler", "female")

    generator = ExerciseGenerator(AudioSettings())
    generator.full_dialogue(session)
    male_voice = session.resolved_voices["Officer"]
    assert male_voice in lang.voices["male"]

    # Стать МІНЯЄТЬСЯ на протилежну — саме той сценарій з бага.
    session.set_speaker_gender("Officer", "female")
    assert "Officer" not in session.resolved_voices, (
        "Кеш голосу мав бути скинутий одразу при зміні статі, "
        "а не лишитись зі старим чоловічим голосом"
    )

    generator.full_dialogue(session)
    new_voice = session.resolved_voices["Officer"]
    assert new_voice in lang.voices["female"], (
        f"Після зміни статі на 'female' голос мав бути з жіночого пулу, отримано {new_voice}"
    )
    print("OK: зміна статі спікера коректно скидає кеш голосу (баг виправлено)")


def main():
    test_each_gender_has_at_least_one_voice()
    test_invalid_gender_value_treated_as_missing()
    test_voice_model_is_picked_automatically_and_stays_consistent()
    test_voice_pool_variety_or_stability()
    test_native_voice_picked_automatically_and_consistent()
    test_pick_voice_uses_pool()
    test_changing_gender_invalidates_voice_cache()
    print("\nВСІ ТЕСТИ ВИБОРУ ГОЛОСУ ПРОЙДЕНО.")


if __name__ == "__main__":
    main()
