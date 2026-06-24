# Third-Party Notices & Credits

Jarvis Voice Dictation is built on excellent open-source software and models.
This project's own code is licensed under the PolyForm Noncommercial License 1.0.0
(see `LICENSE`). **The third-party components below are licensed under their own
terms, which govern those components — not this project's license.** Anyone using
this software (including under a commercial license from the author) is
responsible for complying with these third-party licenses as well.

## Python dependencies

| Component | Version | License | Author / Project | Role here |
|---|---|---|---|---|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 1.2.1 | MIT | SYSTRAN | Speech-to-text engine |
| [openWakeWord](https://github.com/dscripka/openWakeWord) | 0.6.0 | Apache-2.0 | David Scripka | "Hey Jarvis" wake-word detection |
| [sounddevice](https://github.com/spatialaudio/python-sounddevice) | 0.5.5 | MIT | Matthias Geier | Microphone audio capture |
| [pynput](https://github.com/moses-palmer/pynput) | 1.8.2 | **LGPL-3.0** | Moses Palmér | Keystroke injection (typing into the prompt) |
| [NumPy](https://numpy.org) | 2.5.0 | BSD-3-Clause | NumPy Developers | Audio array math |

### Transitive dependencies (pulled in by the above)
| Component | License | Author / Project |
|---|---|---|
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | MIT | SYSTRAN / OpenNMT |
| [tokenizers](https://github.com/huggingface/tokenizers) | Apache-2.0 | Hugging Face |
| [PyAV (av)](https://github.com/PyAV-Org/PyAV) | BSD-3-Clause | The PyAV Authors |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) | MIT | Microsoft |
| [PortAudio](http://www.portaudio.com) (via sounddevice) | MIT | PortAudio community |

A complete, exact list of every installed package and version is pinned in
`requirements.lock.txt`.

## Models

| Model | License | Source | Role here |
|---|---|---|---|
| Whisper (`base.en`, run via faster-whisper) | MIT | [OpenAI](https://github.com/openai/whisper) | Speech-to-text |
| openWakeWord `hey_jarvis` pretrained model | Apache-2.0 | [openWakeWord](https://github.com/dscripka/openWakeWord) | Wake-word model |
| Silero VAD (used for voice-activity filtering) | MIT | [Silero Team](https://github.com/snakers4/silero-vad) | Filters non-speech / background music |

## Note on pynput (LGPL-3.0)

pynput is licensed under the GNU Lesser General Public License v3.0. It is used
here as an **unmodified library** installed from PyPI. Under the LGPL you may use
it in a project under different terms (including this project's noncommercial
license, or a commercial license obtained from the author) provided pynput
itself remains LGPL, is credited, and its source remains available to users
(it is, at the link above). If you redistribute, keep this notice and pynput's
license intact, and allow users to replace the pynput library.

---

*The names "Whisper", "OpenAI", "Hugging Face", "Microsoft", "SYSTRAN", and
"Silero" are the property of their respective owners and are used here only to
credit the components this project depends on.*
