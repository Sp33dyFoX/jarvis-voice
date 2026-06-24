"""
Stage 1 test: confirm mic input + "Hey Jarvis" wake-word detection.
Usage:  python wake_test.py [device_index | name-substring]
With no argument it auto-selects your Realtek mic by name (survives index
reshuffles on reboot). You can also pass an index (e.g. 2) or a name
fragment (e.g. realtek).
Say "Hey Jarvis" a few times. You should see DETECTED lines.
Watch the RMS number to confirm your mic is actually being heard.
Press Ctrl+C to stop.
"""
import sys
import time
import numpy as np
import sounddevice as sd
from openwakeword.model import Model

RATE = 16000
CHUNK = 1280          # 80 ms at 16 kHz (openWakeWord's expected frame size)
THRESHOLD = 0.5       # wake score above this = detection
DEFAULT_MIC = "realtek"  # preferred mic selected by name when no arg given


def pick_device(arg):
    """Return an input device index. arg may be None, an int index, or a name fragment."""
    if arg is not None and arg.isdigit():
        return int(arg)
    needle = (arg or DEFAULT_MIC).lower()
    # Prefer a device whose name contains the needle AND opens at 16 kHz mono.
    candidates = [(i, d) for i, d in enumerate(sd.query_devices())
                  if d["max_input_channels"] > 0 and needle in d["name"].lower()]
    for i, d in candidates:
        try:
            sd.check_input_settings(device=i, samplerate=RATE, channels=1, dtype="int16")
            return i
        except Exception:
            continue
    if candidates:          # name matched but none cleanly accept 16k; use first anyway
        return candidates[0][0]
    return sd.default.device[0]


DEVICE = pick_device(sys.argv[1] if len(sys.argv) > 1 else None)

print(f"Loading hey_jarvis model...")
oww = Model(wakeword_models=["hey_jarvis"])
print("Loaded.\n")

dev_name = sd.query_devices(DEVICE)["name"]
print(f"Using mic: [{DEVICE}] {dev_name}")
print("Speak 'Hey Jarvis' now. (Ctrl+C to stop)\n")

last_rms_print = 0.0
last_detect = 0.0

def callback(indata, frames, time_info, status):
    global last_rms_print, last_detect
    if status:
        print("audio status:", status, file=sys.stderr)
    pcm = np.frombuffer(indata, dtype=np.int16)
    # RMS level (0-100ish) so the user can confirm the mic hears them
    rms = int(np.sqrt(np.mean(pcm.astype(np.float32) ** 2)))
    now = time.time()
    if now - last_rms_print > 1.0:
        bar = "#" * min(40, rms // 50)
        print(f"  mic level: {rms:5d}  {bar}")
        last_rms_print = now
    scores = oww.predict(pcm)
    s = scores.get("hey_jarvis", 0.0)
    if s >= THRESHOLD and (now - last_detect) > 1.5:
        print(f">>> DETECTED 'Hey Jarvis'  (score={s:.2f})  <<<")
        last_detect = now

try:
    with sd.RawInputStream(samplerate=RATE, blocksize=CHUNK, device=DEVICE,
                           dtype="int16", channels=1, callback=callback):
        while True:
            time.sleep(0.1)
except KeyboardInterrupt:
    print("\nStopped.")
except Exception as e:
    print(f"\nERROR opening mic at 16kHz on this device: {e}")
    print("Try a different device index from the list, e.g.  python wake_test.py 2")
