# Supplies an image. Knows nothing about Gemini, speech or the button.
#
# Uses the Pi camera when picamera2 is available, and falls back to reading a
# local test image otherwise, so the pipeline can be exercised without a Pi.

import os
import time

from PIL import Image

from config import CAMERA_RESOLUTION, CAMERA_WARMUP_SECONDS, TEST_IMAGE_PATH

# picamera2 only exists on Raspberry Pi OS.
try:
    from picamera2 import Picamera2
    PI_CAMERA_AVAILABLE = True
except ImportError:
    PI_CAMERA_AVAILABLE = False

CAPTURE_FILE = "capture.jpg"


def is_test_mode() -> bool:
    """True when no real camera is available."""
    return not PI_CAMERA_AVAILABLE


def capture_image() -> Image.Image:
    """Return an image, from the camera or from the test file.

    Raises:
        RuntimeError: if the camera cannot be opened or the capture fails.
        ValueError: if the resulting file is not a valid image.
    """
    if PI_CAMERA_AVAILABLE:
        _capture_from_pi_camera()
        return _open_image(CAPTURE_FILE)

    return _load_test_image()


def _capture_from_pi_camera() -> None:
    """Capture a still from the Pi camera and save it as CAPTURE_FILE.

    The camera is opened in a 'with' block so it is released even if the
    capture fails; otherwise it stays busy and the next press cannot open it.
    """
    try:
        with Picamera2() as picam2:
            picam2.configure(
                picam2.create_still_configuration(main={"size": CAMERA_RESOLUTION})
            )
            picam2.start()

            # Let exposure and focus settle before capturing.
            time.sleep(CAMERA_WARMUP_SECONDS)

            picam2.capture_file(CAPTURE_FILE)
            picam2.stop()

    except Exception as e:
        raise RuntimeError(
            "Hata: Kameradan fotoğraf çekilemedi.\n"
            "Kamera kablosunun düzgün takılı olduğunu kontrol et.\n"
            f"Detay: {e}"
        ) from e

    if not os.path.exists(CAPTURE_FILE):
        raise RuntimeError("Hata: Fotoğraf dosyası oluşturulamadı.")


def _load_test_image() -> Image.Image:
    """Load the stand-in image used when no camera is present."""
    if not os.path.exists(TEST_IMAGE_PATH):
        raise RuntimeError(
            f"Hata: Test modundasın ama '{TEST_IMAGE_PATH}' bulunamadı.\n"
            "Proje klasörüne bu isimde bir fotoğraf koy, ya da projeyi "
            "Raspberry Pi üzerinde çalıştır."
        )

    return _open_image(TEST_IMAGE_PATH)


def _open_image(path: str) -> Image.Image:
    """Open an image file and verify it is not corrupt.

    verify() consumes the file handle, so the image is opened again after
    the check.
    """
    try:
        Image.open(path).verify()
        return Image.open(path)
    except Exception as e:
        raise ValueError(
            f"Hata: Fotoğraf açılamadı. Dosya bozuk olabilir.\nDetay: {e}"
        ) from e
