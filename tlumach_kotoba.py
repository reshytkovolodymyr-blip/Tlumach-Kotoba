#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tlumach_kotoba.py
------------------
Точка входу Tlumach Kotoba (English + Japanese + Français + Español,
для україномовних користувачів).

GUI побудований на PySide6 (Qt) — уся бізнес-логіка в пакеті app/.
OpenAI API key для роботи не потрібен.
"""

from app.gui import main

if __name__ == "__main__":
    main()
