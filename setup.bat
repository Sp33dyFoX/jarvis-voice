@echo off
REM ============================================================
REM  Jarvis voice dictation - one-time setup (Windows)
REM  Creates a venv, installs deps, pre-downloads the models.
REM ============================================================
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found on PATH. Install Python 3.9+ from python.org and re-run.
  pause
  exit /b 1
)

echo [1/4] Creating virtual environment (.venv)...
python -m venv .venv || (echo venv failed & pause & exit /b 1)

echo [2/4] Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet

echo [3/4] Installing dependencies (this can take a few minutes)...
".venv\Scripts\python.exe" -m pip install -r requirements.txt || (echo pip install failed & pause & exit /b 1)

echo [4/4] Pre-downloading models (openWakeWord + Whisper base.en)...
".venv\Scripts\python.exe" -c "import openwakeword,openwakeword.utils as u; u.download_models(); from faster_whisper import WhisperModel; WhisperModel('base.en',device='cpu',compute_type='int8'); print('models ready')"

echo.
echo === Setup complete. ===
echo Pick your microphone:   run-jarvis.bat --list-mics
echo Then start dictation:   run-jarvis.bat
echo (If your mic is not auto-detected, set it: set JARVIS_MIC=your-mic-name  or pass an index)
pause
