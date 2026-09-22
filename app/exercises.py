"""
exercises.py
------------
ExerciseGenerator будує списки аудіо-сегментів (мова/пауза) для кожного
з 5 навчальних режимів (розділ 8 ТЗ, дописаний — в оригінальному docx
було описано лише Full Dialogue, а Shadowing/Phrase Trainer/Recall/
Reverse Recall були відсутні чи порожні).

КРИТИЧНО: кожен метод приймає LessonSession ЯВНИМ аргументом і не
зберігає жодного власного стану. Дані завжди беруться з того об'єкта,
який передав викликач (GUI бере його з SessionManager.current).

Голос спікера більше НЕ визначається позицією (перший=A, другий=B),
як було в English Practice Studio — тепер він береться з
session.speaker_voices, який користувач заповнює вручну в GUI.
Якщо голос не призначено — метод одразу зупиняється з MissingVoiceError,
щоб ніколи не створити аудіо з "вгаданим" голосом.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .audio import PauseSegment, Segment, SpeakSegment
from .languages import pick_native_voice, pick_voice
from .session import LessonSession

MODES: Dict[str, str] = {
    "full_dialogue": "Full Dialogue",
    "shadowing": "Shadowing",
    "phrase_trainer": "Phrase Trainer",
    "recall": "Recall",
    "reverse_recall": "Reverse Recall",
}


class MissingVoiceError(Exception):
    """Хоча б одному спікеру не призначено стать вручну."""

    def __init__(self, speakers: List[str]):
        self.speakers = speakers
        names = ", ".join(speakers)
        super().__init__(f"Не обрано голос для спікера(ів): {names}")


@dataclass
class AudioSettings:
    speech_rate: str = "-10%"          # загальний темп мовлення, напр. "-10%"
    pause_between_lines: float = 1.0    # пауза між репліками у Full Dialogue;
                                         # також база для "природного" проходу Shadowing
    recall_pause: float = 5.0           # пауза перед відповіддю в Recall /
                                         # у зворотному блоці Phrase Trainer
    # Конкретний voice_id (і мови вивчення, і голосу перекладу) сюди
    # НЕ передається — це свідомо: користувач обирає лише стать, а
    # яку саме модель голосу залучити, вирішує сама програма (див.
    # ExerciseGenerator._speaker_voice_map / _native_voice нижче).


class ExerciseGenerator:
    """Генерує сегменти для FULL DIALOGUE, SHADOWING, PHRASE TRAINER,
    RECALL та REVERSE RECALL — виключно на основі переданого LessonSession."""

    def __init__(self, settings: AudioSettings):
        self.settings = settings

    def _speaker_voice_map(self, session: LessonSession) -> Dict[str, str]:
        """{ім'я спікера: voice_id}. session.speaker_voices зберігає лише
        стать ("male"/"female"), обрану вручну в GUI. Конкретна модель
        голосу підбирається тут автоматично (languages.pick_voice) і
        кешується в session.resolved_voices — щоб той самий спікер
        звучав однаково у всіх файлах, згенерованих для цього уроку."""
        missing = session.missing_speaker_voices()
        if missing:
            raise MissingVoiceError(missing)

        mapping: Dict[str, str] = {}
        for speaker in session.unique_speakers():
            if speaker not in session.resolved_voices:
                gender = session.speaker_voices[speaker]
                session.resolved_voices[speaker] = pick_voice(session.target_language, gender)
            mapping[speaker] = session.resolved_voices[speaker]
        return mapping

    def _native_voice(self, session: LessonSession) -> str:
        """Голос перекладу (рідна мова) — так само автоматичний, і так
        само кешується на весь урок (не змінюється між фразами чи
        режимами одного й того самого уроку)."""
        if not session.resolved_native_voice:
            session.resolved_native_voice = pick_native_voice()
        return session.resolved_native_voice

    def _narrator_voice(self, session: LessonSession) -> str:
        """Голос для озвучення фраз у Phrase Trainer, які не прив'язані
        до конкретного спікера діалогу. Використовуємо голос першого
        спікера, якому вже призначено стать — а якщо спікерів немає
        взагалі, це також MissingVoiceError."""
        voice_map = self._speaker_voice_map(session)
        first_speaker = next(iter(voice_map), None)
        if first_speaker is None:
            raise MissingVoiceError(["(немає спікерів у діалозі)"])
        return voice_map[first_speaker]

    # ------------------------------------------------------------------
    # 1. FULL DIALOGUE — Speaker A -> pause -> Speaker B -> pause -> ...
    # ------------------------------------------------------------------
    def full_dialogue(self, session: LessonSession) -> List[Segment]:
        voice_map = self._speaker_voice_map(session)
        segments: List[Segment] = []
        for i, line in enumerate(session.dialogue):
            segments.append(SpeakSegment(text=line.text, voice=voice_map[line.speaker]))
            if i < len(session.dialogue) - 1:
                segments.append(PauseSegment(seconds=self.settings.pause_between_lines))
        return segments

    # ------------------------------------------------------------------
    # 2. SHADOWING — три проходи зі зростаючою складністю:
    #    повільно (довга пауза) -> природний темп (коротша пауза) ->
    #    без паузи ("наздоганяючий" — говорити одночасно з диктором).
    #    Короткий словесний маркер на початку кожного проходу орієнтує
    #    слухача всередині одного MP3-файлу.
    # ------------------------------------------------------------------
    def shadowing(self, session: LessonSession) -> List[Segment]:
        voice_map = self._speaker_voice_map(session)
        natural_pause = self.settings.pause_between_lines
        segments: List[Segment] = []

        passes = [
            ("Повільно. Повторюйте кожну репліку вголос.",
             self._slower(self.settings.speech_rate), natural_pause * 2),
            ("У природному темпі.",
             self.settings.speech_rate, natural_pause),
            ("Без пауз. Говоріть одночасно з диктором.",
             self.settings.speech_rate, 0.3),
        ]

        for label, rate, pause in passes:
            segments.append(SpeakSegment(text=label, voice=self._native_voice(session)))
            segments.append(PauseSegment(seconds=1.0))
            for line in session.dialogue:
                segments.append(SpeakSegment(text=line.text, voice=voice_map[line.speaker], rate=rate))
                segments.append(PauseSegment(seconds=pause))

        return segments

    # ------------------------------------------------------------------
    # 3. PHRASE TRAINER — два блоки:
    #    (1) форма і значення: фраза -> повільніше -> переклад -> приклад
    #    (2) активне пригадування: переклад -> пауза -> фраза
    #        (лише для фраз, що мають переклад — без нього нічим підказати)
    # ------------------------------------------------------------------
    def phrase_trainer(self, session: LessonSession) -> List[Segment]:
        if not session.phrases:
            raise ValueError("NO_PHRASES")

        narrator = self._narrator_voice(session)
        slower_rate = self._slower(self.settings.speech_rate)
        segments: List[Segment] = []

        for phrase in session.phrases:
            segments.append(SpeakSegment(text=phrase.phrase, voice=narrator))
            segments.append(PauseSegment(seconds=0.6))
            segments.append(SpeakSegment(text=phrase.phrase, voice=narrator, rate=slower_rate))
            segments.append(PauseSegment(seconds=0.6))

            if phrase.meaning_uk:
                segments.append(SpeakSegment(text=phrase.meaning_uk, voice=self._native_voice(session)))
            else:
                # КРИТИЧНО: якщо перекладу немає у вхідному тексті —
                # програма НЕ вигадує переклад сама.
                segments.append(SpeakSegment(text="Translation unavailable.", voice=narrator))

            if phrase.example:
                segments.append(PauseSegment(seconds=0.4))
                segments.append(SpeakSegment(text=phrase.example, voice=narrator))

            segments.append(PauseSegment(seconds=self.settings.pause_between_lines))

        recallable = [p for p in session.phrases if p.meaning_uk]
        if recallable:
            segments.append(SpeakSegment(
                text="Тепер спробуйте пригадати фразу самі.", voice=self._native_voice(session),
            ))
            segments.append(PauseSegment(seconds=1.0))
            for phrase in recallable:
                segments.append(SpeakSegment(text=phrase.meaning_uk, voice=self._native_voice(session)))
                segments.append(PauseSegment(seconds=self.settings.recall_pause))
                segments.append(SpeakSegment(text=phrase.phrase, voice=narrator))
                segments.append(PauseSegment(seconds=self.settings.pause_between_lines))

        return segments

    # ------------------------------------------------------------------
    # 4. RECALL — питання -> пауза (спроба відповісти самому) -> відповідь
    # ------------------------------------------------------------------
    def recall(self, session: LessonSession) -> List[Segment]:
        voice_map = self._speaker_voice_map(session)
        segments: List[Segment] = []
        for pair in session.practice_pairs:
            segments.append(SpeakSegment(text=pair.prompt_text, voice=voice_map[pair.prompt_speaker]))
            segments.append(PauseSegment(seconds=self.settings.recall_pause))
            segments.append(SpeakSegment(text=pair.answer_text, voice=voice_map[pair.answer_speaker]))
            segments.append(PauseSegment(seconds=self.settings.pause_between_lines))
        return segments

    # ------------------------------------------------------------------
    # 5. REVERSE RECALL — відповідь -> пауза (згадати питання) -> питання
    # ------------------------------------------------------------------
    def reverse_recall(self, session: LessonSession) -> List[Segment]:
        voice_map = self._speaker_voice_map(session)
        segments: List[Segment] = []
        for pair in session.practice_pairs:
            segments.append(SpeakSegment(text=pair.answer_text, voice=voice_map[pair.answer_speaker]))
            segments.append(PauseSegment(seconds=self.settings.recall_pause))
            segments.append(SpeakSegment(text=pair.prompt_text, voice=voice_map[pair.prompt_speaker]))
            segments.append(PauseSegment(seconds=self.settings.pause_between_lines))
        return segments

    @staticmethod
    def _slower(rate: str) -> str:
        """Зменшує темп ще на 15 в.п. відносно базового rate
        (наприклад "-10%" -> "-25%") для повільного повторення фрази."""
        try:
            value = int(rate.replace("%", "").replace("+", ""))
        except ValueError:
            value = 0
        value -= 15
        value = max(value, -70)
        sign = "+" if value > 0 else ""
        return f"{sign}{value}%"
