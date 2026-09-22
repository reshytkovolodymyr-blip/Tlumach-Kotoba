"""
test_current_session.py
------------------------
Автоматизована версія "КРИТИЧНОГО ТЕСТУ": перевіряє, що жодна вправа
ніколи не використовує старий чи demo-діалог замість поточного уроку,
і що без ручного призначення голосу спікеру аудіо НЕ створюється.

Не потребує ffmpeg, edge-tts чи Tkinter.

Запуск:  py tests/test_current_session.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.audio import SpeakSegment  # noqa: E402
from app.exercises import AudioSettings, ExerciseGenerator, MissingVoiceError  # noqa: E402
from app.session import SessionManager  # noqa: E402

AIRPORT = """Officer: Good morning. May I see your passport?
Traveler: Certainly. Here you are.
Officer: What is the purpose of your trip?
Traveler: I am visiting my family.
"""

HOTEL = """Receptionist: Welcome to our hotel. Do you have a reservation?
Guest: Yes, under the name Smith.
Receptionist: How many nights will you be staying?
Guest: Three nights, please.
"""

JOB_INTERVIEW = """Interviewer: Why do you want to work here?
Candidate: I admire the company's mission.
Interviewer: What is your biggest strength?
Candidate: I adapt quickly to new challenges.
"""


def spoken_text(segments) -> str:
    return " ".join(s.text for s in segments if isinstance(s, SpeakSegment))


def assert_contains_only(label, text, must_have, must_not_have):
    for phrase in must_have:
        assert phrase in text, f"[{label}] ОЧІКУВАВСЯ фрагмент «{phrase}», але його немає: {text}"
    for phrase in must_not_have:
        assert phrase not in text, f"[{label}] ЗАБОРОНЕНИЙ фрагмент «{phrase}» знайдено: {text}"
    print(f"OK: {label}")


def assign_all_voices(session):
    """Імітує ручний вибір СТАТІ користувачем у GUI. Конкретна модель
    голосу (напр. яка саме з en-US-Guy/Davis/Jason...) підбирається
    автоматично в exercises.py — цей тест лише про стать."""
    for i, speaker in enumerate(session.unique_speakers()):
        session.speaker_voices[speaker] = "male" if i % 2 == 0 else "female"


def main():
    sessions = SessionManager()
    generator = ExerciseGenerator(AudioSettings())

    # --- Голос НЕ призначено -> MissingVoiceError -----------------------
    airport = sessions.create_from_text(AIRPORT, title="Airport", level="B2", target_language="english")
    try:
        generator.shadowing(airport)
        raise AssertionError("Мало бути MissingVoiceError — голоси ще не призначені!")
    except MissingVoiceError:
        print("OK: без ручного призначення голосу генерація аудіо заблокована")

    assign_all_voices(airport)

    # --- Крок 2: Hotel B1 (Airport більше не активний) -------------------
    hotel = sessions.create_from_text(HOTEL, title="Hotel", level="B1", target_language="english")
    assign_all_voices(hotel)
    assert sessions.current is hotel
    assert sessions.current is not airport

    # --- Крок 3: Shadowing повинен містити ТІЛЬКИ Hotel -------------------
    shadow_text = spoken_text(generator.shadowing(sessions.current))
    assert_contains_only(
        "Крок 3: Shadowing = Hotel B1", shadow_text,
        must_have=["reservation", "Three nights"],
        must_not_have=["passport", "purpose of your trip"],
    )

    # --- Крок 4: повернення до Airport через History -----------------------
    sessions.set_current(airport)
    assert sessions.current is airport

    # --- Крок 5: Recall повинен містити ТІЛЬКИ Airport -----------------------
    recall_text = spoken_text(generator.recall(sessions.current))
    assert_contains_only(
        "Крок 5: Recall = Airport B2", recall_text,
        must_have=["passport", "purpose of your trip"],
        must_not_have=["reservation", "Three nights"],
    )

    # --- Крок 6: Job Interview B2 ---------------------------------------------
    job = sessions.create_from_text(JOB_INTERVIEW, title="Job Interview", level="B2", target_language="english")
    assign_all_voices(job)
    assert sessions.current is job

    # --- Крок 7: усі режими повинні містити ТІЛЬКИ Job Interview ---------------
    for mode_name, builder in [
        ("Shadowing", generator.shadowing),
        ("Recall", generator.recall),
        ("Reverse Recall", generator.reverse_recall),
    ]:
        text = spoken_text(builder(sessions.current))
        forbidden = ["passport", "purpose of your trip", "reservation", "Three nights"]
        for phrase in forbidden:
            assert phrase not in text, f"[Крок 7: {mode_name}] Знайдено СТОРОННІЙ текст «{phrase}»!"
        print(f"OK: Крок 7: {mode_name} = тільки Job Interview")

    print("\nВСІ КРИТИЧНІ ТЕСТИ ПРОЙДЕНО.")


if __name__ == "__main__":
    main()
