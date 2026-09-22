"""
database.py
-----------
DatabaseManager — SQLite-сховище історії уроків і подій.

ВАЖЛИВО: History лише ЗБЕРІГАЄ уроки. Вона НІКОЛИ сама не підмішує
старі дані в поточний урок. Щоб зробити збережений урок активним,
потрібна явна дія користувача (подвійний клік у списку History),
яка викликає SessionManager.set_current(...) — див. gui.py.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from .session import LessonSession


class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        con = self._connect()
        con.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY,
                created_at TEXT,
                title TEXT,
                target_language TEXT,
                level TEXT,
                data TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                created_at TEXT,
                kind TEXT,
                session_id INTEGER
            )
        """)
        con.commit()
        con.close()

    def save_session(self, session: LessonSession) -> int:
        con = self._connect()
        cur = con.execute(
            "INSERT INTO sessions(created_at, title, target_language, level, data) VALUES (?,?,?,?,?)",
            (session.created, session.title, session.target_language, session.level, session.to_json()),
        )
        session_id = cur.lastrowid
        con.execute(
            "INSERT INTO events(created_at, kind, session_id) VALUES (?,?,?)",
            (session.created, "session_created", session_id),
        )
        con.commit()
        con.close()
        return session_id

    def update_session(self, session: LessonSession) -> None:
        """Оновлює вже збережений урок — використовується, коли користувач
        призначає/змінює голоси спікерів після початкового розбору,
        щоб при повторному відкритті з History голоси не губились."""
        if session.id is None:
            return
        con = self._connect()
        con.execute(
            "UPDATE sessions SET title=?, target_language=?, level=?, data=? WHERE id=?",
            (session.title, session.target_language, session.level, session.to_json(), session.id),
        )
        con.commit()
        con.close()

    def delete_session(self, session_id: int) -> None:
        """Видаляє урок з History за запитом користувача (права кнопка
        миші → Видалити). Записи в events НЕ чіпаються навмисно — вони
        основа для лічильників "Всього уроків"/"MP3 створено", і мають
        лишатись правдивою історією того, що реально відбувалось, навіть
        якщо сам урок видалено."""
        con = self._connect()
        con.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        con.commit()
        con.close()

    def clear_history(self) -> None:
        """Видаляє ВСІ уроки одразу (кнопка "Очистити всю історію").
        events так само лишаються незмінними — та сама логіка, що й
        у delete_session."""
        con = self._connect()
        con.execute("DELETE FROM sessions")
        con.commit()
        con.close()

    def log_event(self, kind: str, session_id: Optional[int] = None) -> None:
        con = self._connect()
        con.execute(
            "INSERT INTO events(created_at, kind, session_id) VALUES (?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), kind, session_id),
        )
        con.commit()
        con.close()

    def list_history(self, limit: int = 50) -> List[Tuple]:
        con = self._connect()
        rows = con.execute(
            "SELECT id, created_at, title, target_language, level FROM sessions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        con.close()
        return rows

    def load_session(self, session_id: int) -> Optional[LessonSession]:
        con = self._connect()
        row = con.execute("SELECT data FROM sessions WHERE id = ?", (session_id,)).fetchone()
        con.close()
        if not row:
            return None
        session = LessonSession.from_json(row[0])
        session.id = session_id
        return session

    def stats(self) -> dict:
        con = self._connect()
        today = con.execute(
            "SELECT COUNT(*) FROM events "
            "WHERE kind='session_created' AND date(created_at)=date('now','localtime')"
        ).fetchone()[0]
        total_sessions = con.execute(
            "SELECT COUNT(*) FROM events WHERE kind='session_created'"
        ).fetchone()[0]
        audio_created = con.execute(
            "SELECT COUNT(*) FROM events WHERE kind='audio_created'"
        ).fetchone()[0]
        con.close()
        return {"today": today, "total_sessions": total_sessions, "audio_created": audio_created}
