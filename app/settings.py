"""
settings.py
------------
Персистентні налаштування застосунку, що НЕ стосуються конкретного
уроку (на відміну від studio.db) — наразі лише мова інтерфейсу.
Зберігається окремим JSON-файлом поруч із базою уроків.

Мова інтерфейсу застосовується ПІСЛЯ ПЕРЕЗАПУСКУ застосунку, а не
миттєво — свідоме рішення: миттєва заміна тексту в кожному вже
збудованому віджеті Tkinter означала б перебудову практично всього
дерева віджетів наживо, що суттєво підвищує ризик щось пропустити й
зламати вже робочу функціональність. Перезапуск — надійніший шлях.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

DEFAULT_SETTINGS: Dict[str, str] = {"ui_language": "uk"}


def load_settings(path: Path) -> Dict[str, str]:
    if not path.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return dict(DEFAULT_SETTINGS)
        merged = dict(DEFAULT_SETTINGS)
        merged.update(data)
        return merged
    except Exception:  # noqa: BLE001 — пошкоджений файл налаштувань не критичний
        return dict(DEFAULT_SETTINGS)


def save_settings(path: Path, settings: Dict[str, str]) -> None:
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
