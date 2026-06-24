#!/usr/bin/env bash
# ============================================================
#  Jarvis voice dictation - one-time setup (macOS / Linux)
#  Creates a venv, installs deps, pre-downloads the models.
# ============================================================
set -e
cd "$(dirname "$0")"

# sounddevice needs the PortAudio system library:
#   macOS:  brew install portaudio
#   Debian/Ubuntu:  sudo apt-get install -y libportaudio2 portaudio19-dev
if ! python3 -c "import ctypes.util,sys; sys.exit(0 if ctypes.util.find_library('portaudio') else 1)" 2>/dev/null; then
  echo "[warn] PortAudio not detected. Install it first:"
  echo "       macOS:        brew install portaudio"
  echo "       Debian/Ubuntu: sudo apt-get install -y libportaudio2 portaudio19-dev"
fi

echo "[1/4] Creating virtual environment (.venv)..."
python3 -m venv .venv

echo "[2/4] Upgrading pip..."
.venv/bin/python -m pip install --upgrade pip --quiet

echo "[3/4] Installing dependencies (this can take a few minutes)..."
.venv/bin/python -m pip install -r requirements.txt

echo "[4/4] Pre-downloading models (openWakeWord + Whisper base.en)..."
.venv/bin/python -c "import openwakeword,openwakeword.utils as u; u.download_models(); from faster_whisper import WhisperModel; WhisperModel('base.en',device='cpu',compute_type='int8'); print('models ready')"

echo
echo "=== Setup complete. ==="
echo "Pick your microphone:   ./run-jarvis.sh --list-mics"
echo "Then start dictation:   ./run-jarvis.sh"
