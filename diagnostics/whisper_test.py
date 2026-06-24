"""
Stage 2 retest with Whisper (faster-whisper, offline). Utterance-based:
transcribes after each short pause, so text appears ~1s after you finish a
phrase but is far more accurate than Vosk-small. Still PRINTS only.

Flow:
  - Say "Hey Jarvis"  -> "● LISTENING".
  - Speak a phrase, pause briefly -> it prints  you said: ...
  - ~3s of silence    -> pauses; say "Hey Jarvis" again to resume.
  - Ctrl+C to quit.

Usage:  python whisper_test.py [model] [device]
  model  : base.en (default) | small.en | tiny.en
  device : mic index or name fragment (default: realtek)
"""
import sys
import os
import time
import queue
import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from faster_whisper import WhisperModel

HERE = os.path.dirname(os.path.abspath(__file__))
RATE = 16000
CHUNK = 1280              # 80 ms
WAKE_THRESHOLD = 0.5
SPEECH_RMS = 120          # above this = speech
END_SILENCE = 0.7        # silence that ends one utterance -> transcribe
SESSION_TIMEOUT = 3.0    # silence that pauses the whole session
DEFAULT_MIC = "realtek"

MODEL_NAME = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].isdigit() else "base.en"
MIC_ARG = None
for a in sys.argv[1:]:
    if a.isdigit() or a.lower() in ("realtek", "oculus"):
        MIC_ARG = a


def pick_device(arg):
    if arg is not None and arg.isdigit():
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
print(f"Using mic: [{DEVICE}] {sd.query_devices(DEVICE)['name']}")
print(f"Loading openWakeWord + Whisper '{MODEL_NAME}' (int8)...")
oww = Model(wakeword_models=["hey_jarvis"])
whisper = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
print("Ready. Say 'Hey Jarvis' to start. (Ctrl+C to quit)\n")

q = queue.Queue()


def callback(indata, frames, time_info, status):
    if status:
        print("audio status:", status, file=sys.stderr)
    q.put(bytes(indata))


def transcribe(pcm_bytes_list):
    audio = np.frombuffer(b"".join(pcm_bytes_list), dtype=np.int16).astype(np.float32) / 32768.0
    if len(audio) < RATE * 0.2:        # too short to be real speech
        return ""
    t0 = time.time()
    segments, _ = whisper.transcribe(audio, language="en", beam_size=1)
    text = " ".join(s.text.strip() for s in segments).strip()
    dt = time.time() - t0
    if text:
        print(f"  you said: {text}    [{dt:.1f}s]")
    return text


session = False
in_speech = False
utt = []
preroll = []
last_speech = 0.0
last_wake = 0.0

try:
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
                    session = True
                    in_speech = False
                    utt, preroll = [], []
                    last_speech = now
                    print("● LISTENING — speak now")
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
                        transcribe(utt)
                        in_speech = False
                        utt = []
                if now - last_speech > SESSION_TIMEOUT:
                    session = False
                    print("⏸  paused (silence). Say 'Hey Jarvis' to resume.\n")
except KeyboardInterrupt:
    print("\nStopped.")
