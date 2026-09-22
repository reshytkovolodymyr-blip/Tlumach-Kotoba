@echo off
title Tlumach Kotoba
py tlumach_kotoba.py
if errorlevel 1 (
    echo.
    echo The application exited with an error. See the message above.
    echo If dependencies are not installed, run INSTALL.bat first.
    pause
)
