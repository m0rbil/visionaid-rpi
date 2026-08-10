# VisionAid

**An assistive device that describes the surroundings out loud, at the press of a button.**

VisionAid runs on a Raspberry Pi 4. The user presses a physical button, the camera takes a photo, Gemini describes the scene with an emphasis on obstacles and direction, and the description is spoken through Bluetooth headphones. End to end: **about 3 seconds.**

Turkish and English are both supported, switched with a single setting.

Built as a university capstone project.

---

## The Problem

People with visual impairments navigate through touch and sound. What they lack is ambient context: what is directly ahead, whether the path is clear, what a sign says.

Existing options are either expensive dedicated hardware or phone apps that require holding and aiming a phone — awkward when one hand already holds a cane.

VisionAid targets a narrow slice of this:

- **One physical button.** No screen, no menus, no aiming a phone.
- **Turkish first.** Most assistive vision tools describe scenes in English only. English is supported too, but Turkish was the design target.
- **Obstacle-first descriptions.** The prompt instructs the model to lead with position and safety — *"directly ahead of you"*, *"to your right"*, *"Careful,"* — rather than producing a scenic description.

It is not a navigation system and does not replace a cane or guide dog. It answers one question: *"What is in front of me right now?"*

---

## Architecture

```mermaid
flowchart LR
    A[Button<br/>GPIO 17] --> B[Camera<br/>picamera2]
    B --> C[Vision AI<br/>Gemini 2.5 Flash]
    C --> D[Text Processing<br/>Turkish description]
    D --> E[Text-to-Speech<br/>Google Cloud TTS]
    E --> F[Bluetooth Audio Out<br/>pygame]

    style A fill:#e8eaf6,stroke:#3f51b5,color:#1a237e
    style C fill:#e8f5e9,stroke:#43a047,color:#1b5e20
    style E fill:#fff3e0,stroke:#fb8c00,color:#e65100
    style F fill:#fce4ec,stroke:#e91e63,color:#880e4f
```

Each stage is a separate module that knows nothing about the others. `vision.py` receives an image object and does not know whether it came from the camera or from disk — which is what makes the pipeline testable without a Raspberry Pi attached.

```
main.py       Orchestration — calls each step in order
trigger.py    Button press (or keyboard, when no GPIO is present)
camera.py     Provides an image
vision.py     Image → Turkish description
tts.py        Text → audio file
player.py     Plays the audio, then deletes it
timing.py     Per-step latency measurement
config.py     Settings, secret loading, secret masking
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Board | Raspberry Pi 4 Model B (2 GB) |
| Camera | Pi 3/4-compatible camera module over CSI, via `picamera2` |
| Input | Momentary push button on GPIO 17, internal pull-up |
| Vision AI | Google **Gemini 2.5 Flash** (`google-genai`), thinking disabled |
| Speech | Google **Cloud Text-to-Speech**, Chirp3-HD voices (`tr-TR` / `en-US`) |
| Audio out | `pygame.mixer` → OS default sink → Bluetooth headphones |
| Language | Python 3.11 |

Audio is uncompressed WAV (LINEAR16). MP3 from the same voice was noticeably worse in quality, and the measurements below show the larger download costs little.

---

## Hardware

A single momentary push button, no external resistor:

| Button leg | Pi pin |
|---|---|
| Signal | **Pin 11** — GPIO 17 (BCM) |
| Ground | **Pin 6** — GND |

The Pi's internal pull-up is enabled in software, so the pin idles HIGH and the press is detected when the button pulls it to ground.

Bluetooth headphones need no code — pair them at the OS level and they become the default audio sink.

---

## Setup

```bash
git clone https://github.com/m0rbil/visionaid-rpi.git
cd visionaid-rpi
pip install -r requirements.txt
sudo apt install -y python3-picamera2    # Raspberry Pi OS only
```

Add your API keys:

```bash
cp .env.example .env
```

```env
GEMINI_API_KEY=your_key_here
GOOGLE_TTS_API_KEY=your_key_here
VISIONAID_LANG=tr        # tr or en, defaults to tr
```

Get them from [Google AI Studio](https://aistudio.google.com/apikey) and the [Google Cloud Console](https://console.cloud.google.com/apis/credentials) — the Cloud Text-to-Speech API must be enabled. One Google Cloud key with both APIs enabled can serve both.

`.env` is gitignored, and any key appearing in an API error message is masked before it is printed.

Run it:

```bash
python main.py
```

Press the button. `Ctrl+C` to quit.

Without a Pi, the program falls back to reading a local `test.jpg` and waiting for the Enter key, so the full pipeline can be exercised from a laptop.

---

## Performance

The original build had a noticeable wait between the button press and the first sound. Every stage was instrumented and measured rather than guessed at, which showed **Gemini accounted for roughly 89% of the delay** — image handling and speech synthesis were never the problem.

The cause was not the network. Gemini 2.5 models reason internally before answering, which helps on multi-step problems and is wasted on a single-step task like describing a photo. Disabling it, same image, 4 runs each:

| Configuration | Average |
|---|---:|
| Thinking enabled (default) | 11.80 s |
| Thinking disabled (`thinking_budget=0`) | **1.87 s** |

Description quality was unchanged — same length, same positional cues, same safety warnings. Applying this required migrating from the deprecated `google-generativeai` package to the current `google-genai` SDK, which is the only one that exposes the setting.

Result, measured over 5 runs against the live APIs:

| Stage | Before | After |
|---|---:|---:|
| Gemini vision analysis | 10.96 s | **1.51 s** |
| Google Cloud TTS | 1.47 s | 1.43 s |
| **Time to first audio** | **12.38 s** | **2.94 s** |

Latency here means time until speech *starts* — playback duration is the length of the sentence, not a delay.

Two notes on scope: these were measured on a laptop reading a stored image, so the camera stage reads 0 s. On the Pi it adds the deliberate 1.5 s exposure warm-up set in `config.py` (a blurry frame produces a useless description) plus capture time; those figures were not measured. Gemini and TTS go over the network and are representative either way.

After the fix, Gemini and TTS contribute almost equally, so further gains have to come from elsewhere.

---

## Possible Improvements

**Streaming TTS.** The whole WAV file is currently synthesised and downloaded before playback starts. Streaming would let speech begin on the first chunk, hiding most of the remaining ~1.4 s.

**Overlapping the two API calls.** Gemini can stream its response. The first sentence could be sent to TTS while the model is still producing the second, instead of running the calls back to back.

**On-device pre-filtering.** A lightweight local check could reject unusable frames — too dark, too blurry, lens covered — before spending a network round trip, and skip the call entirely when the scene has not changed.

---

## Limitations

- **Requires an internet connection.** Both stages are cloud APIs. With no connectivity the device does nothing — the biggest weakness for a tool most needed outdoors.
- **Two languages only.** Turkish and English. Each language needs its own hand-written prompt rather than a translated one, because the positional wording carries the safety information — so adding a language is deliberate work, not a config line.
- **Still a multi-second wait.** Fine for *"what is in front of me?"*, too slow to react to anything moving.
- **Costs money per press.** One Gemini call plus one Cloud TTS call each time. Gemini's free tier allows 15 requests per minute.
- **The output is not verified.** The prompt asks the model to lead with obstacles and to refuse to guess on unclear images, but a confidently wrong description is possible and would be dangerous to trust blindly.

---

## License

MIT — see [LICENSE](LICENSE).
