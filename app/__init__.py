"""
Tlumach Kotoba — пакет бізнес-логіки.

    parser.py            — розбір тексту (Speaker: text) на репліки й фрази
    languages.py          — конфігурація мов: голоси TTS, рівні, чи потрібен romaji
    japanese_reading.py   — офлайн романізація японського тексту (pykakasi)
    session.py            — LessonSession + SessionManager (CURRENT SESSION)
    tts.py                 — абстракція TTS-рушія (edge-tts)
    audio.py               — складання фінального MP3 через FFmpeg
    exercises.py           — генератори 5 режимів вправ
    database.py            — історія уроків (SQLite)
    gui.py                  — Tkinter-інтерфейс
"""

__version__ = "1.0.0"
