@echo off
REM Start Jarvis voice dictation (Windows).
REM Examples:
REM   run-jarvis.bat                 (default mic + base.en)
REM   run-jarvis.bat --list-mics     (show microphones and exit)
REM   run-jarvis.bat small.en        (more accurate model)
REM   run-jarvis.bat 2               (use mic index 2)
cd /d "%~dp0"
title Jarvis Voice Dictation
".venv\Scripts\python.exe" jarvis.py %*
pause
