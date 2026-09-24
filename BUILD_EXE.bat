@echo off
echo =====================================================
echo   Tlumach Kotoba - Building EXE (PyInstaller)
echo =====================================================
echo.

echo [1/2] Installing PyInstaller...
py -m pip install pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller.
    pause
    exit /b 1
)

echo.
echo [2/2] Building TlumachKotoba.exe...
py -m PyInstaller --noconsole --onefile ^
    --name TlumachKotoba ^
    --icon assets\icon.ico ^
    --add-data "examples;examples" ^
    --add-data "assets;assets" ^
    --collect-data pykakasi ^
    --collect-all PySide6 ^
    --collect-all pygame ^
    --collect-all imageio_ffmpeg ^
    tlumach_kotoba.py

if errorlevel 1 (
    echo [ERROR] Build failed. See the messages above.
    pause
    exit /b 1
)

echo.
echo =====================================================
echo   Done! dist\TlumachKotoba.exe
echo.
echo   FFmpeg is bundled into the EXE via imageio-ffmpeg
echo   (--collect-all imageio_ffmpeg), nothing to install.
echo   --collect-data pykakasi is required, otherwise
echo   Japanese romanization will not work in the built EXE.
echo   --collect-all PySide6 is required, otherwise the
echo   GUI will not load in the built EXE.
echo   --collect-all pygame is required, otherwise the
echo   built-in audio player will not work in the built EXE.
echo =====================================================
pause
