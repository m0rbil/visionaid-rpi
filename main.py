# main.py - VisionAid Ana Döngü
# -----------------------------------------------
# Bu dosya hiçbir işi kendisi yapmaz; sadece adımları doğru sırayla çağırır:
#
#   tetikleme → fotoğraf çek → Gemini'ye betimlet → sese çevir → çal
#
# Her adım kendi dosyasında olduğu için buradaki akış tek bakışta okunur.
#
# Çalışma ortamına göre kendini ayarlar:
#   - Raspberry Pi'de : GPIO butonu + Pi kamerası
#   - Windows'ta      : Enter tuşu + hazır test fotoğrafı

import sys
import textwrap

# Ekran çıktısını UTF-8'e sabitler.
#
# Neden gerekli: Windows'ta varsayılan kodlama Türkçe sistemlerde cp1254'tür
# ve aşağıdaki çerçeve karakterleri (╔═╗) ile emoji (📸 ✅) o kodlamada
# bulunmaz. Çıktı bir dosyaya yönlendirildiğinde program daha açılış
# ekranında çökerdi. Linux/Raspberry Pi zaten UTF-8 kullandığı için orada
# sorun çıkmıyordu.
#
# errors="replace": beklenmedik bir karakter yine de gelirse program
# çökmek yerine o karakteri '?' ile gösterir.
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
    """Açılış ekranını ve içinde bulunulan çalışma modunu yazdırır."""
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
    print("  2. Gemini fotoğrafı Türkçe betimler")
    print("  3. Betimleme seslendirilir")
    print()


def print_description(description: str) -> None:
    """Betimlemeyi çerçeve içinde, satırlara bölerek ekrana yazdırır."""
    print()
    print("  ┌─ Gemini Betimleme " + "─" * 31)
    for line in textwrap.wrap(description, width=60):
        print(f"  │ {line}")
    print("  └" + "─" * 49)
    print()


def run_pipeline() -> bool:
    """
    Tek bir tur için tüm adımları sırayla çalıştırır ve sürelerini ölçer.

    Returns:
        True: Başarılı
        False: Hata oluştu (kullanıcıya mesaj zaten gösterildi)
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

        # is_latency=False: bu süre kullanıcının beklediği gecikme değil,
        # konuşmanın kendi uzunluğudur.
        with timer.measure("Ses çalma", is_latency=False):
            player.play_audio(audio_file)

    except (ConnectionError, ValueError, RuntimeError) as e:
        print(f"\n  ❌ {e}\n")
        return False
    except Exception as e:
        print(f"\n  ❌ Beklenmedik hata: {e}\n")
        return False

    finally:
        # Geçici ses dosyası her durumda silinir; çalma sırasında hata çıksa
        # bile diskte kalmaz. Ses hiç üretilemediyse audio_file None'dır ve
        # silinecek bir şey yoktur.
        if audio_file:
            player.cleanup(audio_file)

    print("  ✅ Tamamlandı!")
    timer.print_report()
    return True


def main() -> None:
    """Kullanıcı çıkmak isteyene kadar tetikleme bekleyip pipeline'ı çalıştırır."""
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
