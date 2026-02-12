@echo off
title Whisper Live
cd /d "%~dp0"
call whisper_live_app\venv\Scripts\activate.bat
python -m whisper_live_app %*
