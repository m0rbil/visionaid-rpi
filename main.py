# Entry point. Does no work itself — it calls each step in order:
#
#     trigger → capture → describe → synthesise → play
#
# Adapts to its environment: GPIO button and Pi camera on a Raspberry Pi,
# Enter key and a test image elsewhere.

import sys
import textwrap

# Force UTF-8 output. On Turkish Windows the default encoding is cp1254,
# which lacks the box-drawing characters and emoji used below, and the
# program would crash on startup when output is redirected.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import camera
import player
import trigger
import tts
import vision
from config import ACTIVE_LANGUAGE
from timing import StepTimer

SEPARATOR = "─" * 50
VERSION = "1.2.0"


def print_banner() -> None:
    """Print the splash screen and the detected operating mode."""
    giris = "GPIO butonuna bas" if trigger.is_button_mode() else "Enter'a bas"
    kaynak = "test fotoğrafı" if camera.is_test_mode() else "kamera"

    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║          VisionAid - Görme Engelli Asistanı      ║")
    print(f"║          Versiyon: {VERSION:<29}║")
    print("╚══════════════════════════════════════════════════╝")
    print()
    print(f"  Görüntü kaynağı : {kaynak}")
    print(f"  Tetikleme       : {giris}")
    print(f"  Çıktı dili      : {ACTIVE_LANGUAGE}")
    print()
    print("  Nasıl kullanılır:")
    print(f"  1. {giris} → fotoğraf alınır")
    print("  2. Gemini fotoğrafı betimler")
    print("  3. Betimleme seslendirilir")
    print()


def print_description(description: str) -> None:
    """Print the description wrapped inside a frame."""
    print()
    print("  ┌─ Gemini Betimleme " + "─" * 31)
    for line in textwrap.wrap(description, width=60):
        print(f"  │ {line}")
    print("  └" + "─" * 49)
    print()


def run_pipeline() -> bool:
    """Run one full cycle, timing each step.

    Returns:
        True on success, False if an error was already reported.
    """
    timer = StepTimer()
    audio_file = None

    try:
        print("  [1/3] Fotoğraf alınıyor...")
        with timer.measure("Fotoğraf çekimi"):
            image = camera.capture_image()

        print("  [2/3] Gemini analiz ediyor...")
        with timer.measure("Gemini analizi"):
            description = vision.describe_image(image)

        print_description(description)

        print("  [3/3] Seslendiriliyor...")
        with timer.measure("Ses üretimi (TTS)"):
            audio_file = tts.synthesize_speech(description)

        # Playback time is the length of the sentence, not a delay.
        with timer.measure("Ses çalma", is_latency=False):
            player.play_audio(audio_file)

    except (ConnectionError, ValueError, RuntimeError) as e:
        print(f"\n  ❌ {e}\n")
        return False
    except Exception as e:
        print(f"\n  ❌ Beklenmedik hata: {e}\n")
        return False

    finally:
        # Runs even if playback failed, so no stale file is left behind.
        if audio_file:
            player.cleanup(audio_file)

    print("  ✅ Tamamlandı!")
    timer.print_report()
    return True


def main() -> None:
    """Wait for a trigger and run the pipeline until the user quits."""
    print_banner()

    session_count = 0

    while True:
        print(SEPARATOR)

        if not trigger.wait_for_trigger():
            print()
            print(f"  👋 Çıkılıyor... Bu oturumda {session_count} fotoğraf işlendi.")
            print()
            break

        print()
        if run_pipeline():
            session_count += 1
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Program durduruldu (Ctrl+C).")
        sys.exit(0)
