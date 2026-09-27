"""
winutils.py
-----------
Дрібні системні хелпери, специфічні для Windows. Окремий модуль (а не
метод у gui.py) навмисно — щоб і gui.py, і wizard.py могли його
імпортувати без циклічного імпорту (gui.py й так імпортує PromptWizard
з wizard.py).
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QWidget


def force_light_titlebar(widget: QWidget) -> None:
    """Заголовок вікна (смужка з назвою й хрестиком) малює сама Windows,
    не Qt, і від нашого QSS ніяк не залежить. Windows 11 інколи вгадує
    світлу/темну тему для різних вікон ПО-РІЗНОМУ — реальний баг, коли
    головне вікно лишалось світлим, а майстер промпту ставав темним,
    хоча в коді між ними жодної різниці немає. Явно фіксуємо світлий
    заголовок для КОЖНОГО вікна програми (MainWindow, майстер, «Про
    програму»), щоб вигляд завжди був однаковим, незалежно від примх
    системи. На інших ОС виклик — тихий no-op."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = int(widget.winId())
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(0)  # 0 = світлий заголовок, 1 = темний
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value),
        )
    except Exception:  # noqa: BLE001 — суто косметика, ніколи не критично
        pass
