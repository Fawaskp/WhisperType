@echo off
title Building Whisper Live .exe
cd /d "%~dp0"
call whisper_live_app\venv\Scripts\activate.bat

echo Installing PyInstaller if needed...
pip install pyinstaller >nul 2>&1

echo Building executable...
pyinstaller whisper_live.spec --noconfirm

echo.
if exist "dist\WhisperLive\WhisperLive.exe" (
    echo Build successful: dist\WhisperLive\WhisperLive.exe
) else (
    echo Build failed. Check output above for errors.
)
pause
