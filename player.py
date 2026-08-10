# Plays an audio file, then deletes it. Knows nothing about how it was made.
#
# Bluetooth needs no code here: pygame writes to the OS default audio sink,
# and a paired headset becomes that sink automatically.

import os
import time

import pygame


def play_audio(filepath: str) -> None:
    """Play the file and block until it finishes.

    The mixer is closed in a 'finally' block so the audio device is released
    even if playback fails; otherwise it stays busy and the next attempt is
    silent.

    Raises:
        RuntimeError: if the device cannot be opened or playback fails.
    """
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.play()

        # Without this wait the program would cut the audio short.
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

    except pygame.error as e:
        raise RuntimeError(
            "Hata: Ses çalınamadı.\n"
            "Ses kartını ve kulaklık bağlantısını kontrol et.\n"
            f"Detay: {e}"
        ) from e
    except Exception as e:
        raise RuntimeError(
            f"Hata: Ses oynatıcıda beklenmedik sorun.\nDetay: {e}"
        ) from e

    finally:
        # Swallowed on purpose: a shutdown error must not mask the real one,
        # and there is nothing useful to do about it.
        try:
            pygame.mixer.music.unload()
            pygame.mixer.quit()
        except pygame.error:
            pass


def cleanup(filepath: str) -> None:
    """Delete the temporary audio file.

    Failure is ignored: a leftover file is harmless and gets overwritten on
    the next run. A missing file raises OSError, which the same handler
    catches, so no existence check is needed.
    """
    try:
        os.remove(filepath)
    except OSError:
        pass
