# player.py - Ses Çalma
# -----------------------------------------------
# Bu modülün tek işi: hazır bir ses dosyasını çalmak ve sonra silmek.
# Sesin nasıl üretildiğini bilmez (o iş tts.py'ye ait).
#
# Bluetooth kulaklık hakkında not: burada Bluetooth'a özel kod yoktur.
# pygame sesi işletim sisteminin varsayılan çıkışına gönderir; kulaklık
# Raspberry Pi'ye eşleştirildiğinde varsayılan çıkış otomatik olarak
# kulaklık olur ve ses oradan duyulur.

import os
import time

import pygame


def play_audio(filepath: str) -> None:
    """
    Ses dosyasını çalar ve bitmesini bekler.

    Ses aygıtı 'finally' bloğunda kapatılır: çalma sırasında hata çıksa bile
    aygıt serbest bırakılır. Aksi halde ses kartı meşgul kalır ve bir sonraki
    denemede ses hiç çıkmazdı. (Kameradaki 'with' bloğuyla aynı mantık.)

    Args:
        filepath: Çalınacak ses dosyasının yolu

    Raises:
        RuntimeError: Ses aygıtı açılamazsa veya çalma başarısız olursa
    """
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.play()

        # Ses bitene kadar bekle; beklemezsek program sesi kesip devam eder.
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
        # Kapatma sırasında çıkan hata yutulur: asıl hatayı gizlememesi gerekir,
        # ayrıca kapatma başarısız olsa da yapılabilecek bir şey yoktur.
        try:
            pygame.mixer.music.unload()
            pygame.mixer.quit()
        except pygame.error:
            pass


def cleanup(filepath: str) -> None:
    """
    Geçici ses dosyasını siler.

    Silinemezse program durmaz: dosyanın kalması işleyişi bozmaz,
    bir sonraki çalıştırmada zaten üzerine yazılır.

    Dosya zaten yoksa os.remove hata verir, ama o hata da OSError olduğu
    için aşağıdaki except tarafından yakalanır; ayrıca varlık kontrolü
    yapmaya gerek yoktur.
    """
    try:
        os.remove(filepath)
    except OSError:
        pass
