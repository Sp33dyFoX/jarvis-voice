"""
Jarvis voice dictation for the Claude Code prompt.

  Say "Hey Jarvis"   -> starts/resumes dictation (types into the focused window)
  Speak normally     -> transcribed (Whisper base.en, offline) and typed
  Pause ~3s          -> auto-pauses; say "Hey Jarvis" to resume and keep adding
  Say "Jarvis send"  -> types any leftover words, presses Enter, then pauses
  Say "Jarvis stop"  -> pauses immediately
  Ctrl+C in this window -> quit

Whatever window has keyboard focus receives the text, so keep the Claude Code
prompt focused while dictating. 100% offline (openWakeWord + faster-whisper).

Usage:  python jarvis.py [model] [mic]
  model : base.en (default) | small.en | tiny.en
  mic   : index or name fragment (default: realtek)
"""
import sys
import os
import re
import time
import queue

# Make console output UTF-8 safe so a stray character in a transcript (em-dash,
# smart quote, music note) can never crash the app on the Windows cp1252 console.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from faster_whisper import WhisperModel
from pynput.keyboard import Controller, Key

# ---- tunables ----
RATE = 16000
CHUNK = 1280              # 80 ms
WAKE_THRESHOLD = 0.5
SPEECH_RMS = 120          # above this counts as speech
END_SILENCE = 0.7        # silence that ends one spoken phrase -> transcribe
SESSION_TIMEOUT = 3.0    # silence that auto-pauses the session
# Mic to use: a name fragment (e.g. "realtek") or a numeric index. Env var
# JARVIS_MIC overrides; if no match is found the system default mic is used.
DEFAULT_MIC = os.environ.get("JARVIS_MIC", "realtek")

# Hallucinations Whisper tends to emit on near-silence or background music;
# ignore if a whole utterance is just one of these.
JUNK = {"", "you", "thank you", "thanks for watching", "bye", "okay", ".", "you.",
        "thank you.", "thanks for watching!", "please subscribe", "subscribe",
        "i'm sorry", "so", "uh", "um", "yeah", ".."}
# Bracketed/sound annotations Whisper emits for non-speech audio, e.g. [Music], (applause), ♪...
ANNOTATION = re.compile(r"^[\[\(].*[\]\)]$|[♪♫]")
MIN_AVG_LOGPROB = -1.0   # segments below this confidence are treated as hallucinations

CMD_SEND = re.compile(r"\bjarvis[\s,]+(send|submit|enter)(?:\s+it)?\b", re.I)
CMD_STOP = re.compile(r"\bjarvis[\s,]+(stop|pause|sleep)\b", re.I)
CMD_NEWLINE = re.compile(r"\bjarvis[\s,]+new\s*line\b", re.I)
# Edit commands (checked most-specific first).
CMD_REPLACE = re.compile(r"\bjarvis[\s,]+(?:replace|change)\s+(.+?)\s+(?:with|to)\s+(.+?)[.!?]?$", re.I)
CMD_CLEAR = re.compile(r"\bjarvis[\s,]+(?:clear all|clear everything|scratch everything|scratch all|start over|clear)\b", re.I)
CMD_DELWORDS = re.compile(r"\bjarvis[\s,]+delete (?:the )?last (\w+) words\b", re.I)
CMD_DELWORD = re.compile(r"\bjarvis[\s,]+delete (?:the )?last word\b", re.I)
CMD_SCRATCH = re.compile(r"\bjarvis[\s,]+(?:scratch that|delete that|undo that|undo|delete (?:the )?last (?:sentence|line|phrase)|scratch)\b", re.I)
LEADING_WAKE = re.compile(r"^\s*hey\s+jarvis[\s,.!]*", re.I)

_NUMS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
         "seven": 7, "eight": 8, "nine": 9, "ten": 10, "a": 1, "an": 1}


def word_to_int(w):
    w = w.lower().strip()
    if w.isdigit():
        return max(1, int(w))
    return _NUMS.get(w, 1)

MODEL_NAME = os.environ.get("JARVIS_MODEL", "base.en")
MIC_ARG = None
for a in sys.argv[1:]:
    if a in ("--list-mics", "-l", "--list"):
        print("Input (microphone) devices:")
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                print(f"  [{i}] {d['name']}")
        print("\nRun with a device:  python jarvis.py <index|name>   "
              "or set env JARVIS_MIC")
        sys.exit(0)
    if a.endswith(".en") or a in ("tiny", "base", "small", "medium"):
        MODEL_NAME = a
    else:
        MIC_ARG = a


def pick_device(arg):
    if arg is not None and str(arg).isdigit():
        return int(arg)
    needle = (arg or DEFAULT_MIC).lower()
    cands = [(i, d) for i, d in enumerate(sd.query_devices())
             if d["max_input_channels"] > 0 and needle in d["name"].lower()]
    for i, d in cands:
        try:
            sd.check_input_settings(device=i, samplerate=RATE, channels=1, dtype="int16")
            return i
        except Exception:
            continue
    return cands[0][0] if cands else sd.default.device[0]


DEVICE = pick_device(MIC_ARG)
kb = Controller()
q = queue.Queue()

print(f"Mic: [{DEVICE}] {sd.query_devices(DEVICE)['name']}")
print(f"Loading openWakeWord + Whisper '{MODEL_NAME}'...")
oww = Model(wakeword_models=["hey_jarvis"])
whisper = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
print("\nReady. Say 'Hey Jarvis' and start talking. (Ctrl+C here to quit)")
print("built by the maker of milo3d.ai — AI 3D models, images & video\n")


def callback(indata, frames, time_info, status):
    if status:
        print("audio status:", status, file=sys.stderr)
    q.put(bytes(indata))


def transcribe(pcm_bytes_list):
    audio = np.frombuffer(b"".join(pcm_bytes_list), dtype=np.int16).astype(np.float32) / 32768.0
    if len(audio) < RATE * 0.2:
        return ""
    segments, _ = whisper.transcribe(
        audio, language="en", beam_size=1,
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=300),
    )
    parts = []
    for s in segments:
        if getattr(s, "no_speech_prob", 0.0) >= 0.6:
            continue
        if getattr(s, "avg_logprob", 0.0) < MIN_AVG_LOGPROB:
            continue
        t = s.text.strip()
        if ANNOTATION.search(t):
            continue
        parts.append(t)
    text = " ".join(parts).strip()
    if text.lower().strip(" .") in JUNK:
        return ""
    return text


class Field:
    """Tracks exactly what we've typed (cursor assumed at end) so we can edit it
    by diffing the desired text against the current text and emitting the minimal
    backspaces + retype. Desyncs only if the field is hand-edited mid-session."""

    def __init__(self, kb):
        self.kb = kb
        self.typed = ""        # everything we've put in the field
        self.bounds = []       # start offset of each appended phrase (for "scratch that")

    def _emit(self, new):
        old = self.typed
        cp = 0
        while cp < len(old) and cp < len(new) and old[cp] == new[cp]:
            cp += 1
        for _ in range(len(old) - cp):
            self.kb.press(Key.backspace)
            self.kb.release(Key.backspace)
        if new[cp:]:
            self.kb.type(new[cp:])
        self.typed = new
        self.bounds = [b for b in self.bounds if b <= len(new)]

    def append(self, text):
        self.bounds.append(len(self.typed))
        self._emit(self.typed + text + " ")

    def scratch(self):
        if self.bounds:
            self._emit(self.typed[:self.bounds.pop()])
        elif self.typed:
            self._emit("")

    def delete_words(self, n=1):
        t = self.typed.rstrip()
        for _ in range(n):
            i = t.rfind(" ")
            t = t[:i] if i >= 0 else ""
        self._emit((t + " ") if t else "")

    def clear(self):
        self.bounds = []
        self._emit("")

    def replace(self, x, y):
        x, y = x.strip(), y.strip()
        idx = self.typed.lower().rfind(x.lower())
        if idx < 0:
            return False
        self._emit(self.typed[:idx] + y + self.typed[idx + len(x):])
        return True

    def reset(self):
        self.typed = ""
        self.bounds = []


field = Field(kb)


def press_enter():
    kb.press(Key.enter)
    kb.release(Key.enter)


def handle_utterance(text):
    """Returns new state: 'listen' to keep going, 'pause' to auto-pause."""
    text = LEADING_WAKE.sub("", text).strip()
    if not text:
        return "listen"

    m = CMD_SEND.search(text)
    if m:
        before = text[:m.start()].strip()
        if before:
            field.append(before)
        press_enter()
        field.reset()
        print("  ⏎ sent")
        return "pause"

    if CMD_STOP.search(text):
        print("  ⏸ stop")
        return "pause"

    mr = CMD_REPLACE.search(text)
    if mr:
        ok = field.replace(mr.group(1), mr.group(2))
        print(f"  ✎ replace {mr.group(1)!r} -> {mr.group(2)!r}" + ("" if ok else "  (not found)"))
        return "listen"

    if CMD_CLEAR.search(text):
        field.clear()
        print("  ✗ cleared all")
        return "listen"

    mw = CMD_DELWORDS.search(text)
    if mw:
        n = word_to_int(mw.group(1))
        field.delete_words(n)
        print(f"  ⌫ deleted last {n} words")
        return "listen"

    if CMD_DELWORD.search(text):
        field.delete_words(1)
        print("  ⌫ deleted last word")
        return "listen"

    if CMD_SCRATCH.search(text):
        field.scratch()
        print("  ⌫ scratched last phrase")
        return "listen"

    if CMD_NEWLINE.search(text):
        before = CMD_NEWLINE.sub("", text).strip()
        if before:
            field.append(before)
        kb.press(Key.shift); kb.press(Key.enter); kb.release(Key.enter); kb.release(Key.shift)
        return "listen"

    field.append(text)
    print(f"  + {text}")
    return "listen"


def main():
    session = False
    in_speech = False
    utt, preroll = [], []
    last_speech = 0.0
    last_wake = 0.0

    with sd.RawInputStream(samplerate=RATE, blocksize=CHUNK, device=DEVICE,
                           dtype="int16", channels=1, callback=callback):
        while True:
            chunk = q.get()
            pcm = np.frombuffer(chunk, dtype=np.int16)
            rms = float(np.sqrt(np.mean(pcm.astype(np.float32) ** 2))) if len(pcm) else 0.0
            now = time.time()

            if not session:
                if oww.predict(pcm).get("hey_jarvis", 0.0) >= WAKE_THRESHOLD and now - last_wake > 1.5:
                    last_wake = now
                    session, in_speech = True, False
                    utt, preroll = [], []
                    last_speech = now
                    print("● listening")
                continue

            preroll.append(chunk)
            preroll = preroll[-5:]

            if rms > SPEECH_RMS:
                if not in_speech:
                    in_speech = True
                    utt = list(preroll)
                else:
                    utt.append(chunk)
                last_speech = now
            else:
                if in_speech:
                    utt.append(chunk)
                    if now - last_speech > END_SILENCE:
                        text = transcribe(utt)
                        in_speech, utt = False, []
                        if text:
                            if handle_utterance(text) == "pause":
                                session = False
                                print("⏸ paused — say 'Hey Jarvis' to resume\n")
                                continue
                if session and now - last_speech > SESSION_TIMEOUT:
                    session = False
                    print("⏸ paused (silence) — say 'Hey Jarvis' to resume\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
