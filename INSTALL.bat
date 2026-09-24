@echo off
echo =====================================================
echo   Tlumach Kotoba - Installing dependencies
echo =====================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo Install Python 3.10+ from https://python.org
    echo During installation, check "Add python.exe to PATH".
    pause
    exit /b 1
)

echo [1/3] Python found:
py --version
echo.

echo [2/3] Installing Python dependencies (edge-tts, pykakasi)...
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    echo Check your Internet connection, or see README.txt section 5
    echo if the error mentions "distutils" or "msvccompiler" - that is
    echo a known pygame/Python version issue, not a network problem.
    pause
    exit /b 1
)
echo.

echo [3/3] FFmpeg...
echo FFmpeg is provided by the imageio-ffmpeg package
echo installed in step [2/3]. Nothing else to install.

echo.
echo =====================================================
echo   Setup complete. Run START_APP.bat to launch the app.
echo =====================================================
pause
