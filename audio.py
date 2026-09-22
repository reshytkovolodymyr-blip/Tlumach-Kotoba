"""
audio.py
--------
AudioAssembler перетворює список сегментів (мова/пауза), згенерованих
exercises.py для CURRENT SESSION, у ОДИН фінальний MP3-файл за допомогою
FFmpeg.

Тимчасові фрагменти зберігаються в temporary/ і ГАРАНТОВАНО видаляються
одразу після складання фінального файлу — незалежно від того, вдалось
складання чи ні (через finally/shutil.rmtree).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Union

from .tts import TTSError, TTSManager

# Програма зібрана без консолі (--noconsole), а FFmpeg — консольна
# програма. Без цього прапорця Windows на мить відкриває порожнє вікно
# CMD для КОЖНОГО запуску FFmpeg (пауза, склеювання) — «вікна-привиди»
# під час генерації. На інших системах прапорця немає й він не потрібен.
_NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}

# Програма, запущена з Finder на macOS, не бачить PATH із терміналу,
# тому FFmpeg, встановлений через Homebrew, треба шукати й за відомими
# шляхами.
_FFMPEG_FALLBACKS = ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg")


class AudioError(Exception):
    """Помилка складання аудіо (немає FFmpeg, немає TTS, немає тексту)."""


@dataclass
class SpeakSegment:
    text: str
    voice: str
    rate: Optional[str] = None


@dataclass
class PauseSegment:
    seconds: float


Segment = Union[SpeakSegment, PauseSegment]
StatusCallback = Callable[[str], None]


def _noop_status(_msg: str) -> None:
    pass


class AudioAssembler:
    def __init__(self, tts: TTSManager, out_dir: Path, temp_dir: Path):
        self.tts = tts
        self.out_dir = out_dir
        self.temp_dir = temp_dir
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def check_ffmpeg() -> str:
        ff = shutil.which("ffmpeg") or next((c for c in _FFMPEG_FALLBACKS if Path(c).exists()), None)
        if not ff:
            raise AudioError("FFmpeg не знайдено. Встановіть FFmpeg і повторіть.")
        return ff

    def target_path(self, title: str, mode_label: str) -> Path:
        """Обчислює, яким буде ім'я фінального файлу для цього уроку й
        режиму — БЕЗ створення чи перевірки нічого. Використовується
        GUI, щоб заздалегідь спитати користувача "перезаписати чи
        зберегти як новий", перш ніж узагалі починати синтез."""
        safe_title = re.sub(r"[^A-Za-z0-9_-]+", "_", title).strip("_") or "lesson"
        safe_mode = re.sub(r"[^A-Za-z0-9_-]+", "_", mode_label).strip("_") or "audio"
        return self.out_dir / f"{safe_title}_{safe_mode}.mp3"

    def next_available_path(self, title: str, mode_label: str) -> Path:
        """Те саме, що target_path(), але якщо файл із таким іменем уже
        існує — додає суфікс _2, _3... поки не знайде вільне ім'я.
        Використовується, коли користувач обирає "Зберегти як новий
        файл" замість перезапису вже існуючого."""
        base = self.target_path(title, mode_label)
        if not base.exists():
            return base
        n = 2
        while True:
            candidate = base.with_name(f"{base.stem}_{n}{base.suffix}")
            if not candidate.exists():
                return candidate
            n += 1

    def build(
        self,
        segments: List[Segment],
        default_rate: str,
        title: str,
        mode_label: str,
        status: StatusCallback = _noop_status,
        final_path: Optional[Path] = None,
    ) -> str:
        """Синтезує всі сегменти й склеює їх у ОДИН MP3. Повертає шлях до файлу.

        final_path — якщо задано, використовується як точне ім'я
        фінального файлу (так GUI реалізує вибір "перезаписати" чи
        "зберегти як новий" ще ДО виклику build). Якщо не задано —
        обчислюється так само, як і завжди (target_path)."""
        if not segments:
            raise AudioError("Немає тексту для озвучення.")

        ff = self.check_ffmpeg()

        work = self.temp_dir / ("work_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
        work.mkdir(parents=True, exist_ok=True)

        parts: List[Path] = []
        n = 0
        try:
            for seg in segments:
                if isinstance(seg, SpeakSegment):
                    if not seg.text.strip():
                        continue
                    n += 1
                    p = work / f"{n:04}.mp3"
                    status(f"Озвучення {n}: {seg.text[:55]}")
                    try:
                        self.tts.synth(seg.text, seg.voice, seg.rate or default_rate, p)
                    except TTSError as exc:
                        raise AudioError(str(exc)) from exc
                    if p.exists() and p.stat().st_size > 0:
                        parts.append(p)
                elif isinstance(seg, PauseSegment):
                    n += 1
                    p = work / f"{n:04}_silence.mp3"
                    self._make_silence(ff, seg.seconds, p)
                    parts.append(p)

            if not parts:
                raise AudioError("Немає тексту для озвучення.")

            concat_file = work / "concat.txt"
            rows = ["file '" + p.as_posix().replace("'", "'\\''") + "'" for p in parts]
            concat_file.write_text("\n".join(rows), encoding="utf-8")

            final = final_path if final_path is not None else self.target_path(title, mode_label)

            status("Об'єднання фрагментів в один MP3…")
            result = subprocess.run(
                [ff, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
                 "-c:a", "libmp3lame", "-b:a", "96k", str(final)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **_NO_WINDOW,
            )
            if result.returncode != 0 or not final.exists() or final.stat().st_size < 1000:
                raise AudioError(
                    "FFmpeg не зміг створити цільний MP3.\n\n"
                    "Якщо повідомлення нижче містить \"Permission denied\" саме на "
                    "цьому файлі — найімовірніша причина: цей самий файл зараз "
                    "відкритий у вбудованому плеєрі застосунку. Натисніть ⏹ Stop "
                    "у блоці \"Плеєр\" і спробуйте ще раз.\n\n"
                    + result.stderr[-2000:]
                )

            status(f"Готово: {final.name}")
            return str(final)
        finally:
            # Тимчасові фрагменти видаляються ЗАВЖДИ, навіть при помилці,
            # щоб не накопичувати сміття в temporary/.
            shutil.rmtree(work, ignore_errors=True)

    @staticmethod
    def _make_silence(ffmpeg_bin: str, seconds: float, out_path: Path) -> None:
        subprocess.run(
            [ffmpeg_bin, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
             "-t", str(max(0.1, float(seconds))), "-q:a", "5", str(out_path)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **_NO_WINDOW,
        )
