#!/usr/bin/env bash
# Start Jarvis voice dictation (macOS / Linux).
# Examples:
#   ./run-jarvis.sh                 (default mic + base.en)
#   ./run-jarvis.sh --list-mics     (show microphones and exit)
#   ./run-jarvis.sh small.en        (more accurate model)
#   ./run-jarvis.sh 2               (use mic index 2)
cd "$(dirname "$0")"
exec .venv/bin/python jarvis.py "$@"
