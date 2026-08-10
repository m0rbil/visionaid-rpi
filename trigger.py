# trigger.py - Tetikleme (Buton / Klavye)
# -----------------------------------------------
# Bu modülün tek işi: "kullanıcı fotoğraf çekilmesini istedi mi?" sorusuna
# cevap vermek. Fotoğrafın nasıl çekildiğini, ne yapılacağını bilmez.
#
# İki mod otomatik olarak seçilir:
#   1. Buton modu   : gpiozero kuruluysa GPIO butonu beklenir
#   2. Klavye modu  : değilse (örn. Windows'ta) Enter tuşu beklenir
#
# Donanım bağlantısı:
#   Pin 11 (GPIO17, BCM) → butonun bir ayağı
#   Pin 6  (GND)         → butonun diğer ayağı
#
# Buton basılınca GPIO17 toprağa (GND) bağlanır. Bu yüzden Pi'nin dahili
# pull-up direnci kullanılır: pin normalde yüksek (1), basılınca düşük (0)
# olur. Harici direnç gerekmez.

from config import GPIO_BUTTON_PIN

# gpiozero sadece Raspberry Pi üzerinde anlamlıdır.
try:
    from gpiozero import Button
    GPIO_AVAILABLE = True
except Exception:
    # Sadece ImportError değil: gpiozero kurulu olsa bile Pi dışında
    # pin fabrikası bulunamadığı için başka hatalar da verebilir.
    GPIO_AVAILABLE = False

_button = None


def is_button_mode() -> bool:
    """GPIO butonu kullanılabiliyorsa True döner."""
    return GPIO_AVAILABLE


def _get_button() -> "Button":
    """Buton nesnesini hazırlar. İlk çağrıda kurar, sonra aynısını verir."""
    global _button

    if _button is None:
        _button = Button(GPIO_BUTTON_PIN, pull_up=True)

    return _button


def wait_for_trigger() -> bool:
    """
    Kullanıcının tetiklemesini bekler.

    Returns:
        True: Fotoğraf çekilsin
        False: Programdan çıkılsın
    """
    if GPIO_AVAILABLE:
        return _wait_for_button()

    return _wait_for_enter()


def _wait_for_button() -> bool:
    """
    GPIO butonuna basılmasını bekler.

    Buton modunda çıkış için klavyeden Ctrl+C kullanılır; bu durum
    KeyboardInterrupt olarak gelir ve çıkış isteği sayılır.
    """
    print("  📸 Fotoğraf çekmek için butona bas (çıkış için Ctrl+C)")
    try:
        _get_button().wait_for_press()
        return True
    except KeyboardInterrupt:
        return False


def _wait_for_enter() -> bool:
    """
    Klavyeden Enter tuşunu bekler (buton yokken kullanılır).

    Returns:
        True: Enter'a basıldı
        False: 'q' yazıldı veya Ctrl+C ile çıkıldı
    """
    try:
        raw = input("  📸 Fotoğraf çekmek için Enter'a bas (veya q=çıkış): ").strip()
    except (KeyboardInterrupt, EOFError):
        return False

    return raw.lower() not in ("q", "quit", "exit", "çıkış")
