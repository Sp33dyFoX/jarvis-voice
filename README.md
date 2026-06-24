# Jarvis — offline voice dictation for Claude Code

Hands-free dictation with a **"Hey Jarvis"** wake word. It transcribes your
speech and types it into whatever window has keyboard focus (e.g. the Claude
Code prompt), and understands spoken **edit** and **send** commands. Runs
**100% offline** — no accounts, no API keys, no audio leaves the machine.

Pipeline: `openWakeWord` (wake word) → `faster-whisper` (speech-to-text) →
keystroke injection (`pynput`).

---

## Requirements
- **Python 3.9+**
- A **microphone**
- ~1 GB disk (Whisper `base.en` + wake models + deps)
- macOS/Linux only: the **PortAudio** system library
  - macOS: `brew install portaudio`
  - Debian/Ubuntu: `sudo apt-get install -y libportaudio2 portaudio19-dev`

It does **not** require Claude Code to install — but the whole point is to
dictate into Claude Code, so keep that prompt focused while talking.

---

## Setup (one time)
**Windows:** double-click **`setup.bat`**
**macOS/Linux:**
```bash
chmod +x setup.sh run-jarvis.sh
./setup.sh
```
This creates a `.venv`, installs dependencies, and pre-downloads the models.
(First run needs internet to fetch models; afterwards it's fully offline.)

---

## Run
**Windows:** double-click **`run-jarvis.bat`**
**macOS/Linux:** `./run-jarvis.sh`

1. Click into the window you want to dictate into (the Claude Code prompt).
2. Say **"Hey Jarvis"** → console shows `● listening`.
3. Talk. Your words are typed in.
4. Say **"Jarvis send"** to submit (presses Enter), or just keep talking.

### Picking your microphone
The default tries to find a mic named "realtek", then falls back to the system
default. To choose explicitly:
```
run-jarvis.bat --list-mics          # list devices with indexes
run-jarvis.bat 2                    # use device index 2
set JARVIS_MIC=headset              # (Windows) match by name fragment
export JARVIS_MIC=headset           # (macOS/Linux)
```

### Choosing a model (accuracy vs speed)
`base.en` (default) is a good balance. More accurate / slower: `small.en`.
Faster / less accurate: `tiny.en`.
```
run-jarvis.bat small.en
export JARVIS_MODEL=small.en
```

---

## Voice commands
All commands require the **"Jarvis"** prefix so they never fire from normal speech.

| Say | Effect |
|---|---|
| **"Hey Jarvis"** | Start / resume dictation |
| *(normal speech)* | Transcribed and typed |
| **"Jarvis send"** | Type leftover words, press **Enter**, then pause |
| **"Jarvis stop"** | Pause immediately |
| **"Jarvis scratch that"** | Delete the last phrase |
| **"Jarvis delete last word"** / **"…last three words"** | Delete word(s) |
| **"Jarvis replace X with Y"** / **"Jarvis change X to Y"** | Fix a word (say as one phrase) |
| **"Jarvis clear all"** | Erase everything typed this session |
| **"Jarvis new line"** | Insert a newline (Shift+Enter) |
| *(stop talking ~3s)* | Auto-pauses; say "Hey Jarvis" to resume |

**Notes**
- Edits operate on **what Jarvis typed this session**; after "Jarvis send" the
  buffer resets. It can't edit an already-sent message.
- It types **blind** (tracks its own keystrokes, cursor assumed at the end). If
  you hand-edit the field with the mouse/keyboard mid-dictation it can desync —
  say **"Jarvis clear all"** to resync, or just send and start fresh.

---

## Tuning
Edit the constants near the top of `jarvis.py`:

| Constant | Meaning | If… |
|---|---|---|
| `SPEECH_RMS` | energy above which audio counts as speech | raise if background noise leaks in; lower if quiet speech is missed |
| `END_SILENCE` | pause that ends one phrase (s) | raise if it cuts you off mid-sentence |
| `SESSION_TIMEOUT` | silence that auto-pauses (s) | raise to stay listening longer |
| `WAKE_THRESHOLD` | wake-word sensitivity (0–1) | raise if it false-triggers; lower if it misses |

Background music/noise is filtered by Silero VAD + Whisper confidence, but a
close-talking mic (headset) gives the best results.

---

## Diagnostics
`diagnostics/wake_test.py` — verify mic level + "Hey Jarvis" detection.
`diagnostics/whisper_test.py` — verify transcription quality (prints only).
Run with the venv, e.g. `.venv\Scripts\python diagnostics\wake_test.py`.

---

## Auto-start on login (optional)
- **Windows:** press `Win+R`, type `shell:startup`, and put a shortcut to
  `run-jarvis.bat` there. (Or use Task Scheduler → "At log on".)
- **macOS:** create a `launchd` user agent that runs `run-jarvis.sh`.
- **Linux:** a `systemd --user` service running `run-jarvis.sh`.

---

## Files
```
jarvis.py            the app
requirements.txt     pinned dependencies
setup.bat/.sh        one-time setup (venv + deps + models)
run-jarvis.bat/.sh   launcher
diagnostics/         mic + transcription test scripts
```
Offline after first setup. Wake models cache under the openWakeWord package;
the Whisper model caches under `~/.cache/huggingface`.

---

## About

Jarvis is built and maintained by the creator of **[Milo3D](https://milo3d.ai)** —
an AI platform for generating **3D models, images, and video** from text and images.
If this tool is useful to you, check it out.

*(Milo3D is not required to use Jarvis — this is just a note from the author.)*
