# camera.py - Fotoğraf Çekme
# -----------------------------------------------
# Bu modülün tek işi fotoğraf sağlamak. Gemini'yi, sesi veya butonu bilmez.
#
# İki çalışma modu vardır ve hangisinin kullanılacağına otomatik karar verir:
#   1. Raspberry Pi modu : picamera2 ile gerçek kameradan çeker
#   2. Test modu         : picamera2 kurulu değilse (örn. Windows'ta)
#                          hazır bir fotoğrafı okur
#
# Bu sayede Pi olmadan da projenin tamamı çalıştırılıp test edilebilir.

import os
import time

from PIL import Image

from config import CAMERA_RESOLUTION, CAMERA_WARMUP_SECONDS, TEST_IMAGE_PATH

# picamera2 sadece Raspberry Pi OS üzerinde bulunur.
# Kurulu değilse hata vermek yerine test moduna geçilir.
try:
    from picamera2 import Picamera2
    PI_CAMERA_AVAILABLE = True
except ImportError:
    PI_CAMERA_AVAILABLE = False

CAPTURE_FILE = "capture.jpg"  # Geçici fotoğraf dosyası


def is_test_mode() -> bool:
    """Gerçek kamera yoksa True döner (test modunda çalışılıyor demektir)."""
    return not PI_CAMERA_AVAILABLE


def capture_image() -> Image.Image:
    """
    Ortama uygun yöntemle bir fotoğraf sağlar.

    Returns:
        Fotoğrafın PIL Image nesnesi

    Raises:
        RuntimeError: Kamera açılamazsa veya çekim başarısız olursa
        ValueError: Elde edilen dosya geçerli bir görüntü değilse
    """
    if PI_CAMERA_AVAILABLE:
        _capture_from_pi_camera()
        return _open_image(CAPTURE_FILE)

    return _load_test_image()


def _capture_from_pi_camera() -> None:
    """
    Raspberry Pi kamerasından fotoğraf çeker ve CAPTURE_FILE olarak kaydeder.

    Çekimden önce kısa bir bekleme yapılır: kameranın otomatik pozlama ve
    beyaz dengesi ayarları oturmadan çekilen fotoğraf bulanık/karanlık çıkar.

    Kamera 'with' bloğu içinde açılır: çekim sırasında hata çıksa bile blok
    bitince kamera otomatik olarak serbest bırakılır. Aksi halde kamera
    meşgul kalır ve bir sonraki butona basışta açılamazdı.
    """
    try:
        with Picamera2() as picam2:
            picam2.configure(
                picam2.create_still_configuration(main={"size": CAMERA_RESOLUTION})
            )
            picam2.start()

            # Pozlama/odak ayarlarının oturması için bekleme (netlik için gerekli)
            time.sleep(CAMERA_WARMUP_SECONDS)

            picam2.capture_file(CAPTURE_FILE)
            picam2.stop()

    except Exception as e:
        # 'from e': asıl kamera hatası bu mesajın altına iliştirilir, iz kaybolmaz.
        raise RuntimeError(
            "Hata: Kameradan fotoğraf çekilemedi.\n"
            "Kamera kablosunun düzgün takılı olduğunu kontrol et.\n"
            f"Detay: {e}"
        ) from e

    if not os.path.exists(CAPTURE_FILE):
        raise RuntimeError("Hata: Fotoğraf dosyası oluşturulamadı.")


def _load_test_image() -> Image.Image:
    """
    Test modunda kullanılacak hazır fotoğrafı yükler.

    Raises:
        RuntimeError: Test fotoğrafı bulunamazsa
    """
    if not os.path.exists(TEST_IMAGE_PATH):
        raise RuntimeError(
            f"Hata: Test modundasın ama '{TEST_IMAGE_PATH}' bulunamadı.\n"
            "Proje klasörüne bu isimde bir fotoğraf koy, ya da projeyi "
            "Raspberry Pi üzerinde çalıştır."
        )

    return _open_image(TEST_IMAGE_PATH)


def _open_image(path: str) -> Image.Image:
    """
    Görüntü dosyasını açar ve gerçekten geçerli bir görüntü olduğunu doğrular.

    verify() dosyanın bozuk olup olmadığını kontrol eder, ancak kontrolden
    sonra dosyayı kullanılamaz hale getirir. Bu yüzden dosya tekrar açılır.
    """
    try:
        Image.open(path).verify()
        return Image.open(path)
    except Exception as e:
        raise ValueError(
            f"Hata: Fotoğraf açılamadı. Dosya bozuk olabilir.\nDetay: {e}"
        ) from e
